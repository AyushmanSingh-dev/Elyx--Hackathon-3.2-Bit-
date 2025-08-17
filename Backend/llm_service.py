# Backend/llm_service.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta
import random
import math # Added for poisson_int

app = Flask(__name__)
CORS(app)

# -------------------------
# Config / Global Settings
# -------------------------
START_DATE = datetime(2025, 8, 1)  # Journey start date
WEEKS_TO_GENERATE = 34  # ~8 months of simulation
DIAGNOSTIC_EVERY_WEEKS = 12  # Every 3 months (~12 weeks)
EXERCISE_UPDATE_EVERY_WEEKS = 2
TRAVEL_EVERY_N_WEEKS = 4  # Travel 1 week out of every 4
AVERAGE_MEMBER_CONVS_PER_WEEK = 5  # Average member-initiated conversations
PLAN_ADHERENCE_PROB = 0.5  # ~50% adherence
MEMORY_RETENTION_WEEKS = 4 # Rohan won't ask about the same topic for this many weeks

# Seed for reproducible runs during dev; remove or randomize in production
RANDOM_SEED = os.environ.get("SYNTH_SEED")
if RANDOM_SEED:
    random.seed(int(RANDOM_SEED))
else:
    random.seed(42) # Using a fixed seed for consistent demo output


# -------------------------
# Profiles and Knowledge
# -------------------------
ROHAN_PROFILE = {
    "name": "Rohan Patel",
    "age": 46,
    "gender": "Male",
    "occupation": "Regional Head of Sales (FinTech), frequent international travel",
    "residence": "Singapore",
    "personal_assistant": "Sarah Tan",
    "health_goals": [
        "Reduce risk of heart disease (family history, ApoB focus)",
        "Enhance cognitive function and focus",
        "Annual full-body health screenings"
    ],
    "chronic_condition": "Elevated ApoB (lipoprotein particle risk)",
    "values": "Analytical, efficiency-oriented, time-constrained",
    "commitment_hours_per_week": 5 # Explicitly stated
}

ELYX_TEAM_PERSONAS = {
    "Ruby": {"role": "Concierge / Orchestrator", "voice": "Empathetic, organized, proactive"},
    "Dr. Warren": {"role": "Medical Strategist", "voice": "Authoritative, clinical, careful"},
    "Advik": {"role": "Performance Scientist", "voice": "Analytical, experimental, data-driven"},
    "Carla": {"role": "Nutritionist", "voice": "Practical, behavior-focused"},
    "Rachel": {"role": "Physiotherapist", "voice": "Direct, pragmatic, safety-first"},
    "Neel": {"role": "Concierge Lead / Relationship Manager", "voice": "Strategic, reassuring"}
}

# Expanded knowledge base (more topics, richer summarises/advice)
ELYX_KNOWLEDGE_BASE = {
    "hypertension": {
        "specialist": "Dr. Warren",
        "summary": "High blood pressure increases long-term cardiovascular risk. Management includes lifestyle changes and targeted diagnostics.",
        "advice": "Home BP logs, dietary sodium reduction (DASH principles), and staged diagnostic workup before starting medications where possible."
    },
    "sleep_apnea": {
        "specialist": "Advik",
        "summary": "Sleep apnea reduces restorative sleep and impairs recovery — impacts HRV and cognitive function.",
        "advice": "If suspected, refer for sleep study. Meanwhile, maintain weight control, positional therapy, and avoid alcohol near bedtime."
    },
    "migraines": {
        "specialist": "Carla",
        "summary": "Migraines are multifactorial — diet, sleep, stress, hormones can trigger them.",
        "advice": "Keep a food, sleep and stress diary. Try eliminating common triggers (aged cheese, processed meats) and trial magnesium if appropriate."
    },
    "pediatric_cold": {
        "specialist": "Ruby",
        "summary": "Family illnesses are common; focus on hygiene, immunizations, and early symptom management.",
        "advice": "Sick-day protocol, rest, hydration, and when needed arrange testing or teleconsults."
    },
    "gerd": {
        "specialist": "Carla",
        "summary": "Reflux can disrupt sleep and general wellbeing.",
        "advice": "Avoid late heavy meals, elevate head of bed, and trial diet changes before medication unless severe."
    },
    "apo_b": {
        "specialist": "Dr. Warren",
        "summary": "ApoB estimates number of atherogenic particles and is tightly linked to cardiovascular risk.",
        "advice": "Focus on soluble fiber, reduce saturated fats, increase aerobic exercise and re-check panel in ~3 months. Consider statin evaluation if lifestyle changes inadequate."
    },
    "jet_lag": {
        "specialist": "Advik",
        "summary": "Circadian misalignment from travel decreases performance and can linger.",
        "advice": "Timed light exposure, meal timing, and sleep timing shifts; we send compressed protocols when travel occurs."
    },
    "strength_program": {
        "specialist": "Rachel",
        "summary": "Progressive strength training improves metabolic health, bone density and longevity.",
        "advice": "Start with movement quality, progressive overload, and periodic supervised sessions for form."
    },
    "full_body_mri": {
        "specialist": "Dr. Warren",
        "summary": "Full-body MRI can be a radiation-free screening tool for structural findings.",
        "advice": "Use selectively as part of a proactive screening strategy; evaluate cost/benefit and follow-up plans."
    },
    "cognitive_function": {
        "specialist": "Advik",
        "summary": "Cognitive function is impacted by sleep, stress, nutrition, and physical activity.",
        "advice": "Implement structured focus blocks, consider adaptogens, and optimize sleep hygiene for enhanced clarity."
    },
    "hydration": {
        "specialist": "Carla",
        "summary": "Optimal hydration is foundational for energy, cognitive function, and metabolic health.",
        "advice": "Aim for 2-3 liters of water daily, consider electrolytes during intense exercise or travel. Monitor urine color."
    }
}

# --- Simulated Health Metrics (dynamic & global for generation) ---
CURRENT_HEALTH_METRICS = {} # Will be initialized in generate_full_journey

# --- Global variable to track Rohan's recently asked topics for memory ---
# Stores tuples of (topic_key, timestamp) to allow topics to "cool down"
ROHAN_ASKED_TOPICS_MEMORY = [] # Stores (topic_key, datetime_object)

# --- Message Pools (expanded) ---
# For each persona we create a large pool of unique messages. We'll pop messages to avoid reuse.
def make_pool(prefix, items):
    return [f"{prefix}{text}" for text in items]

# Rohan: member-initiated questions / updates (expanded ~4x)
ROHAN_POOL = make_pool("",
    [
        "Just a quick check-in. The new meal plan from Carla has been helpful, energy is slightly better. What's the next step for nutrition?",
        "My back pain flared up again after that long flight. What's the immediate plan to address this effectively?",
        "Heads up — I have a last-minute trip to London next week. Can we get a jet-lag strategy that's easy to follow?",
        "I've been feeling more headaches lately. Could they be migraines?",
        "What's the overall strategy for my ApoB? I want something actionable and realistic, considering my time.",
        "I have only a 36-hour window next week — can we front-load labs & scans efficiently?",
        "The travel workout was manageable; I did 3/4 of it. Any adjustments or ways to make it more impactful?",
        "My son has a cold. What's the best way to avoid catching it during a heavy work week, without disrupting my routine?",
        "I only have short windows each day — what's a minimal, high-impact routine for fitness?",
        "Can we push my strength session earlier, mornings work better now.",
        "I felt dizzy on standing this morning. Not severe but noticeable.",
        "I'm low on fiber while traveling. What's the minimum effective approach for nutrition on the go?",
        "Can Sarah coordinate the water quality test and VO2 slot?",
        "I've been getting worse jet lag than before. Any tweak to the protocol?",
        "Can we make my exercise plan more aggressive for the next two weeks?",
        "My deep sleep was low last night—any quick tips?",
        "I want to try time-restricted eating; what's a safe protocol?",
        "I tried oatmeal and it spiked my glucose — what's the right way?",
        "I noticed a rash under the Whoop strap. Any suggestions?",
        "Can we do a DEXA and VO2 max next month?",
        "Is a full-body MRI worth it for longevity screening?",
        "How do I adjust nutrition when eating out in the US?",
        "Would short meditation blocks really help focus and recovery?",
        "My HR zones look wrong on Garmin, can Advik review?",
        "I feel like the plan is ad-hoc — I want a coordinated approach.",
        "If I add NMN or NR supplements, is it likely to help?"
    ]
)

# Ruby: concierge messages
RUBY_POOL = make_pool("Ruby: ",
    [
        "Thanks for the update — I'm coordinating with the team and will confirm times by EOD. Your convenience is our priority.",
        "I can arrange a phlebotomist at your office next week; which morning works best for your schedule?",
        "Got it. I've flagged this as Priority 1 for Dr. Warren to review immediately. We'll ensure a swift response.",
        "I've scheduled the VO2 slot and emailed Javier to coordinate meals, aiming for seamless integration.",
        "Reservation confirmed and added to your calendar. Want me to arrange transport? We optimize for your time.",
        "I'll loop Sarah in and handle the logistics so you don't have to worry about the details.",
        "Understood. I'll put a travel-ready meal plan together with Carla, focusing on high-impact, easy options.",
        "I'll overnight a breathable strap for your Whoop. Please switch wrists in the meantime for comfort.",
        "We received the records from Dr. Tan's clinic — thank you for your patience. This completes a crucial step.",
        "I've scheduled Advik for a morning consult — options at 07:30 or 08:30, which do you prefer for efficiency?",
        "I will coordinate the Prenuvo MRI and send you options for late September, minimizing your administrative burden.",
        "We can have a phlebotomist come to your office at 08:30; fasting instructions sent. This saves you valuable time.",
        "I'm arranging meal delivery and electrolyte beverages under the Sick Day Protocol to support your recovery.",
        "I'll handle the environmental lab for water testing next Thursday, ensuring all data points are covered.",
        "Noted. I'll confirm with Rachel the hotel-friendly workout plan and share it tonight, designed for your travel needs.",
        "I'll coordinate with your cook Javier by email to align evening meals to the plan, ensuring dietary consistency.",
        "I'll set a reminder for your 3-month diagnostic panel and coordinate the lab, keeping your plan on track."
    ]
)

# Dr. Warren: medical strategist
DRWARREN_POOL = make_pool("Dr. Warren: ",
    [
        "I've reviewed your records. Elevated ApoB at 110 mg/dL is an important target for risk reduction, aligning with your primary longevity goal. We'll interpret results in context and avoid knee-jerk medication choices unless clinically required.",
        "ApoB is a key marker—we'll prioritize dietary and exercise changes and re-test in 3 months. This integrated approach is often more sustainable and cost-effective long-term.",
        "For dizziness on standing, let's consolidate past autonomic tests and consider orthostatic vitals. This will help us pinpoint the exact cause for targeted intervention.",
        "Before starting any complex supplement like NMN/NR, let's look at your metabolic panel first to ensure efficacy and safety. We prioritize evidence-based decisions.",
        "Add a home BP log and re-run the lipid panel; we will make medication choices if lifestyle fails. Our goal is to maximize health through sustainable habits first.",
        "Cognitive dips often mirror sleep deficits and glucose variability — try 90-min focus blocks + 10-min reset. This optimizes your existing work patterns.",
        "Given your symptoms, upgrading to higher-resolution telemetry (Whoop) is sensible for more precise data. This is an investment in granular insights for better adaptations.",
        "If recovery stays poor after 12 weeks, we may escalate diagnostics (tilt table / autonomic clinic) to uncover underlying issues. This ensures we don't miss critical insights.",
        "We will document plan rationale and set a re-check in 8–12 weeks to review progress. Transparency and data-driven adjustments are core to Elyx.",
        "Your recent diagnostic panel shows significant improvement in key markers. This confirms the effectiveness of your personalized plan and commitment. Let's discuss maintaining this momentum.",
        "While your metrics are stable, let's proactively explore areas for further optimization to push your health span even further. We aim for continuous improvement."
    ]
)

# Advik: performance scientist
ADVIK_POOL = make_pool("Advik: ",
    [
        "Small changes to sleep timing and light exposure can shift circadian rhythm quickly when traveling. We'll provide a concise protocol for your upcoming trip.",
        "Let's try a compressed light-exposure protocol for your upcoming flight — I'll send times. This is designed for maximum impact with minimal effort.",
        "HRV dips could be due to fragmented sleep; let's test a 10-day experiment on sleep timing. This data will inform precise adjustments.",
        "For last-minute travel: morning light, avoid naps >20min on day 1, and time caffeine after first light. Simple, high-impact strategies.",
        "Your Whoop shows good responsiveness — let's increase Zone 2 minutes by 10% over 2 weeks. This progression is key to building aerobic capacity.",
        "We can replace one cardio day with a short Zone 5 interval once per week to boost VO2 max. This is a time-efficient way to enhance performance.",
        "I see a pattern — deep sleep dips after late-afternoon Zoom calls; try blue-light blocking glasses after 4 PM. A small change for a significant sleep gain.",
        "We'll monitor objective signals after each experiment to check signal validity. Data-driven decisions ensure optimal results.",
        "If your HR zones are miscalibrated, we'll do a metabolic step test to individualize training zones. This ensures your efforts are precisely targeted.",
        "Your recovery scores are consistently high. Let's explore advanced recovery techniques or consider increasing training volume slightly."
    ]
)

# Carla: nutritionist
CARLA_POOL = make_pool("Carla: ",
    [
        "For ApoB focus, prioritize soluble fiber, reduce saturated fats, and increase oily fish or plant sterols. Simple swaps can make a big difference.",
        "Try adding psyllium to a morning smoothie for soluble fiber — let me know how it goes. It's an easy way to boost intake.",
        "When traveling, pick a vegetable or fruit at every meal — simple, high-impact rule. This keeps nutrition consistent on the go.",
        "Sushi can spike glucose; pair rice with protein and fat to blunt the curve. A small tweak for better metabolic control.",
        "If legumes cause bloating, soak them overnight and introduce slowly to allow adaptation. We aim for sustainable dietary changes.",
        "We will design travel-friendly substitutions for your cook Javier to follow, ensuring your plan is seamless even when busy.",
        "Time-restricted eating (10h window) is a good experiment — we'll monitor glucose and deep sleep. It's a flexible approach for busy schedules.",
        "If ApoB remains high after lifestyle changes, we may need a conversation about pharmacologic options. We explore all avenues for your health.",
        "For consistent energy, focus on balanced meals with protein, healthy fats, and complex carbs. Avoid refined sugars and excessive caffeine."
    ]
)

# Rachel: physiotherapist
RACHEL_POOL = make_pool("Rachel: ",
    [
        "Try this 12-minute hotel room routine focusing on glute activation and thoracic mobility. It's designed for maximum benefit in minimal time.",
        "I'll create a travel-ready bodyweight routine that keeps stimulus without heavy equipment. No gym needed, high impact.",
        "Introduce a 15-minute pre-workout activation routine to improve form and reduce injury risk. A small investment for big returns.",
        "We'll progress your strength program gradually — focus on movement quality for the first 2 weeks. Building a strong foundation is key.",
        "If low-back flare-ups recur after flights, we'll add daily mobility and modify lifting cues. We adapt the plan to your body's needs.",
        "Log your weights in the app so we can track progressive overload and reduce injury risk. Data helps us optimize your progress.",
        "Great work on consistency! Let's introduce a new compound lift this week to further challenge your strength."
    ]
)

# Neel: concierge lead / relationship
NEEL_POOL = make_pool("Neel: ",
    [
        "Zooming out: trends are heading the right way despite travel volatility. Let's lock the next quarter's plan. How do you feel about the overall progress?", # Added question
        "We can shift strategy if preferences or logistics demand it — your priorities guide the plan. What's your biggest challenge right now?", # Added question
        "Thanks for the transparency. This is design constraints, not failure. We'll adapt and keep the big picture in mind. How can we support you best?", # Added question
        "I'll handle escalations and ensure the team reduces your cognitive load so you can focus on outcomes. Your peace of mind is paramount.",
        "Your commitment to integrating health into your busy life is truly paying off. We're seeing great progress across the board. What's next for you?", # More engaging
        "We're continuously fine-tuning your plan to ensure it's as effective and seamless as possible. Any feedback on how it's fitting into your routine?" # More engaging
    ]
)

# System / automated nudge templates (non-personal)
SYSTEM_POOL = make_pool("System: ",
    [
        "Weekly adherence report: member committed ~5 hours this week; adherence ~50%. Keep up the great effort!",
        "Diagnostic panel scheduled: 12-week follow-up recommended. Prepare for optimal results.",
        "Exercise plan auto-update executed (bi-weekly cadence). Check your portal for new routine details.",
        "Travel protocol deployed for upcoming trip; team has been notified. Safe travels and optimized health!",
        "Automated check: HRV trending up, indicating improved recovery. Excellent progress!",
        "Automated alert: Deep sleep duration slightly below target. Reviewing recent activity for potential causes."
    ]
)

PERSONA_POOLS = {}
# Used messages tracks messages that have been popped from pools to prevent immediate reuse
USED_MESSAGES = {} 

def reset_pools():
    """ Resets the message pools and used messages trackers. Crucial for reproducible runs. """
    global PERSONA_POOLS, USED_MESSAGES
    PERSONA_POOLS = {
        "Rohan": ROHAN_POOL.copy(),
        "Ruby": RUBY_POOL.copy(),
        "Dr. Warren": DRWARREN_POOL.copy(),
        "Advik": ADVIK_POOL.copy(),
        "Carla": CARLA_POOL.copy(),
        "Rachel": RACHEL_POOL.copy(),
        "Neel": NEEL_POOL.copy(),
        "System": SYSTEM_POOL.copy()
    }
    # Randomize the order of messages in each pool if a seed is not set
    if not RANDOM_SEED:
        for pool in PERSONA_POOLS.values():
            random.shuffle(pool)
    USED_MESSAGES = {k: set() for k in PERSONA_POOLS.keys()}

# -------------------------
# Helper Utilities
# -------------------------
def pop_unique(persona):
    """
    Pop a unique message from persona pool. If exhausted, generate a fallback variant (timestamp-based)
    to preserve uniqueness. Always returns a string.
    """
    pool = PERSONA_POOLS.get(persona, [])
    
    # Try to find a message not yet used by this persona
    available_msgs = [msg for msg in pool if msg not in USED_MESSAGES[persona]]
    
    if available_msgs:
        msg = random.choice(available_msgs) # Pick randomly from available
        USED_MESSAGES[persona].add(msg)
        # Remove from pool to prevent future selection in this run
        if msg in pool: # Ensure it's still in the pool before removing
            pool.remove(msg)
        return msg
    
    # Fallback: synthesize a unique message if pool exhausted
    fallback = f"{persona}: (auto-generated unique message at {datetime.utcnow().isoformat()})"
    USED_MESSAGES[persona].add(fallback)
    return fallback

def detect_sentiment(text):
    """
    Simple keyword-based sentiment detector for messages.
    Returns one of: 'angry', 'frustrated', 'curious', 'sad', 'nonchalant', 'positive', 'neutral',
    or Elyx-specific tones: 'authoritative', 'analytical', 'practical', 'direct'.
    """
    if not text:
        return "neutral"
    t = text.lower()
    if any(k in t for k in ["overwhelm", "stress", "off", "concerning", "flared up", "major setback", "unwell", "illness", "struggle", "dizzy", "rash"]):
        return "sad" if random.random() < 0.5 else "angry" # Vary between sad/angry for negative
    if any(k in t for k in ["why", "how", "what's next", "updates", "curious", "question", "advise", "suggest", "recommend", "worth it", "implication", "basis", "insights", "optimize", "challenge"]):
        return "curious"
    if any(k in t for k in ["good", "great", "excellent", "fantastic", "helpful", "progress", "win", "better", "improving", "paying off"]):
        return "positive"
    if any(k in t for k in ["fine", "okay", "alright", "nonchalant", "meh"]):
        return "nonchalant"
    
    # Elyx team specific tones based on their persona
    if "dr. warren" in text.lower():
        return "authoritative"
    if "advik" in text.lower():
        return "analytical"
    if "carla" in text.lower():
        return "practical"
    if "rachel" in text.lower():
        return "direct"
    if "ruby" in text.lower() or "neel" in text.lower():
        return "positive" # Concierge roles are generally positive

    return "neutral"

def format_ts(dt):
    return dt.strftime("%Y-%m-%d %H:%M")

def poisson_int(lam):
    # Simple poisson sample using Knuth's algorithm
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1

# -------------------------
# Core Generator Logic (generate_llm_response is defined here)
# -------------------------
def generate_llm_response(role, prompt_context, current_metrics, chat_history, journey_data_so_far, current_sim_date=None):
    prompt_lower = prompt_context.lower()
    response_text = ""
    decision_rationale = None
    pillar_impact = None
    health_metrics_snapshot = current_metrics.copy() # Snapshot current metrics
    intervention_effect = None # New field for effectiveness
    monetary_factor = None
    time_efficiency = None
    service_interaction_type = "general"
    specialist_involved = role if role != "Rohan" else None
    next_steps = None # New field for following steps
    sentiment = "neutral" # Default sentiment

    # Clean up old topics from memory
    if current_sim_date:
        global ROHAN_ASKED_TOPICS_MEMORY
        ROHAN_ASKED_TOPICS_MEMORY = [
            (topic, ts) for topic, ts in ROHAN_ASKED_TOPICS_MEMORY
            if (current_sim_date - ts).days / 7 < MEMORY_RETENTION_WEEKS
        ]
    
    recently_asked_topic_keys = {topic for topic, _ in ROHAN_ASKED_TOPICS_MEMORY}

    # --- Rohan's Responses (Patient Concerns & Priorities) ---
    if role == "Rohan":
        service_interaction_type = "member-initiated query"
        
        # Define a pool of Rohan's questions, categorized by topic
        # Added more variations and follow-up style questions
        rohan_query_pool = {
            "initial_plan": [
                "Ruby, I'm feeling overwhelmed with my ad-hoc health routine. High work stress, and my Garmin HR seems off even on rest days. I need a proper, coordinated plan. My current supplement list is attached.",
                "My current health efforts feel disjointed. Can we establish a more cohesive plan? My wearable data feels inconsistent.",
                "I'm ready for a structured health approach. My current stress levels are high, and my Garmin data isn't reflecting recovery. Attached is my supplement list.",
                "The current health approach isn't sustainable for my schedule. I need a streamlined, effective plan. My metrics are concerning."
            ],
            "medical_records": [
                "Acknowledged. How long will that take? And what about my fitness goals?",
                "Understood. What's the typical turnaround for record consolidation? Also, let's discuss optimizing my workouts.",
                "Okay, I'll ensure Sarah assists with records. Separately, I'm keen to refine my fitness strategy.",
                "Records are in progress. Meanwhile, I'm eager to discuss my exercise regimen and how to maximize its impact."
            ],
            "movement_assessment": [
                "Understood. I'm also thinking about my stress levels. Any immediate tips?",
                "A movement assessment makes sense. On another note, I've been feeling more stressed. Any quick stress relief techniques?",
                "Good. While we schedule that, what are some immediate strategies for managing cognitive load?",
                "I'm on board for the assessment. What are some rapid techniques for mental clarity and stress reduction?"
            ],
            "couch_stretch": [
                "The couch stretch helped a bit! Also, for stress, any immediate dietary tips? I struggle with consistent energy.",
                "That stretch provided some relief. What about nutritional strategies for managing stress and energy dips?",
                "Good call on the stretch. What are some quick dietary hacks for energy and stress during busy days?",
                "The stretch was beneficial. Now, can we address nutritional support for my energy levels and stress resilience?"
            ],
            "diagnostic_panel": [
                "Yes, next Tuesday works. Confirmed. I'm keen to see the numbers, though I'm always a bit skeptical until I see tangible results.",
                "Tuesday works for diagnostics. I'm interested in the data, but I need to see actionable insights, not just numbers.",
                "Confirmed for diagnostics next week. I value data, but ultimately, it's about practical improvements. What should I expect?",
                "I've scheduled the diagnostic panel for Tuesday. What are the key metrics we're tracking, and how will they inform my plan?"
            ],
            "apo_b": [
                "What's the plan for the ApoB? I want clear, actionable steps. Is this a significant investment?",
                "Elevated ApoB is a concern. What are the most effective, efficient interventions? What's the cost implication?",
                "Understood on ApoB. Let's prioritize interventions. Are there any budget-friendly alternatives for dietary changes or supplements?",
                "Given the ApoB results, what's the immediate, high-impact strategy? I need to know the financial implications and time commitment."
            ],
            "travel": [
                "This sounds critical. I need a clear, minute-by-minute guide for my upcoming trip. How can we make it time-efficient?",
                "My travel schedule is intense. What's the most time-efficient jet lag protocol? I need practical advice for on-the-go.",
                "Preparing for travel. What are the key strategies to minimize disruption to my health, especially given my limited time?",
                "Upcoming international travel. What specific protocols can I implement to mitigate jet lag and maintain my routine effectively?"
            ],
            "illness": [
                "This is a major setback. The board meeting is critical. What's the immediate plan? I need to maximize my recovery output.",
                "Feeling unwell. This is impacting my ability to perform. What's the fastest way to recover without compromising long-term health?",
                "I'm experiencing symptoms. What's the Elyx protocol for this? I need to get back on track efficiently.",
                "I'm feeling a dip in health. What's the recommended course of action to minimize downtime and prevent further impact on my schedule?"
            ],
            "recovery": [
                "Good. I feel it. Let's get back to the plan.",
                "Excellent. I'm seeing the positive effects. What's the next optimization?",
                "Great news on recovery. I'm ready for the next challenge.",
                "My recovery metrics are strong. What advanced strategies can we implement now to push further?"
            ],
            "piano": [
                "I've always wanted to learn piano. From a health and performance perspective, is this a worthwhile use of my time?",
                "Considering learning piano. What are the cognitive benefits, and how does it fit into my overall health investment strategy?",
                "Is piano a good investment for cognitive longevity and stress? What's the commitment like?",
                "I'm exploring new hobbies. Is learning piano a recommended activity for long-term brain health and stress reduction?"
            ],
            "poor_digestion": [
                "I'm experiencing poor digestion. Any suggestions that are easy to integrate into my busy schedule?",
                "What are some practical dietary adjustments for improving digestion, considering my travel and time constraints?",
                "My digestion feels off. Are there any simple, effective strategies I can implement immediately?",
                "Can you provide quick, actionable tips for better digestion that won't disrupt my routine?"
            ],
            "monetary_concern": [ # Rohan explicitly asks about cost
                "I'm concerned about the cost of some recommendations. Can you suggest more budget-friendly alternatives?",
                "How can we optimize for value without compromising results? Are there more economical options?",
                "What's the return on investment for this, and are there less expensive but still effective options?",
                "I need to balance health investments with financial prudence. What are some high-impact, low-cost recommendations?"
            ],
            "time_constraint": [ # Rohan explicitly asks about time
                "I have very limited time. What's the most time-efficient way to achieve Y?",
                "My schedule is packed. Can we focus on high-impact, low-time-commitment interventions?",
                "What are some quick wins for health that fit into a demanding schedule?",
                "I need strategies that deliver maximum health output for minimal time investment. Any suggestions?"
            ],
            "general_query": [
                "Just checking in. Any new recommendations based on my overall progress?",
                "What's the overarching strategy for the next phase of my health journey?",
                "I'm curious about optimizing my current routine. Any thoughts on that?",
                "What's the latest insight from my data? Any new areas of focus?"
            ]
        }

        # Determine Rohan's question based on prompt_context and avoid recent repetition
        chosen_key = None
        # Prioritize specific query types if context matches
        if "initial onboarding" in prompt_lower:
            chosen_key = "initial_plan"
        elif "medical records" in prompt_lower:
            chosen_key = "medical_records"
        elif "movement assessment" in prompt_lower:
            chosen_key = "movement_assessment"
        elif "couch stretch" in prompt_lower and "helped" in prompt_lower:
            chosen_key = "couch_stretch"
        elif "diagnostic panel" in prompt_lower:
            chosen_key = "diagnostic_panel"
        elif "apo b" in prompt_lower or "apob" in prompt_lower:
            chosen_key = "apo_b"
        elif "jet lag" in prompt_lower or "travel" in prompt_lower:
            chosen_key = "travel"
        elif "not feeling great" in prompt_lower or "illness" in prompt_lower:
            chosen_key = "illness"
        elif "recovery" in prompt_lower and "green" in prompt_lower:
            chosen_key = "recovery"
        elif "piano" in prompt_lower:
            chosen_key = "piano"
        elif "poor digestion" in prompt_lower:
            chosen_key = "poor_digestion"
        elif "monetary" in prompt_lower or "cost" in prompt_lower or "expensive" in prompt_lower:
            chosen_key = "monetary_concern"
        elif "time" in prompt_lower or "busy" in prompt_lower or "quick" in prompt_lower:
            chosen_key = "time_constraint"
        else:
            # If no specific match, try to pick a general query not recently asked
            possible_general_keys = [k for k in rohan_query_pool.keys() if k not in recently_asked_topic_keys and k != "initial_plan"]
            if possible_general_keys:
                chosen_key = random.choice(possible_general_keys)
            else: # Fallback if all specific topics are in cool-down, or if it's truly generic
                chosen_key = "general_query"

        # Select a response from the pool, ensuring it's not a recent duplicate text
        # This checks the last 5 actual message contents from Rohan in the chat_history
        recent_rohan_messages_content = [
            msg['parts'][0]['text'] for msg in chat_history[-5:] # Check last 5 messages
            if msg['role'] == 'user' and 'parts' in msg and len(msg['parts']) > 0 and 'text' in msg['parts'][0]
        ]
        available_questions_for_key = [q for q in rohan_query_pool[chosen_key] if q not in recent_rohan_messages_content]
        
        if not available_questions_for_key:
            # If all specific questions for this topic have been used recently, cycle through them
            response_text = random.choice(rohan_query_pool[chosen_key])
        else:
            response_text = random.choice(available_questions_for_key)
        
        # Add the chosen query's *topic* and current timestamp to memory
        if current_sim_date:
            ROHAN_ASKED_TOPICS_MEMORY.append((chosen_key, current_sim_date)) # Store datetime object

        # Determine Rohan's sentiment based on current metrics or context
        if current_metrics["RecoveryScore"] < 50 or current_metrics["POTS_symptoms"] == "severe" or current_metrics["BackPain"] == "severe":
            sentiment = random.choice(["angry", "sad"])
        elif current_metrics["HRV"] > 60 and current_metrics["RecoveryScore"] > 80:
            sentiment = "positive"
        elif "curious" in prompt_lower or "what about" in prompt_lower or "tell me about" in prompt_lower:
            sentiment = "curious"
        elif "thanks" in prompt_lower or "good" in prompt_lower or "excellent" in prompt_lower:
            sentiment = "positive"
        else:
            sentiment = "neutral"

    # --- Elyx Team Member Responses (Prioritizing, Value-Driven, Adaptable) ---
    else:
        service_interaction_type = "proactive check-in" if "check-in" in prompt_lower else "intervention update"
        
        # Default sentiment for Elyx team is neutral/positive
        sentiment = "neutral" 
        if role == "Dr. Warren":
            sentiment = "authoritative" # Dr. Warren's voice
        elif role == "Ruby" or role == "Neel":
            sentiment = "positive" # Concierge roles are generally positive
        elif role == "Advik":
            sentiment = "analytical" # Advik's voice
        elif role == "Carla":
            sentiment = "practical" # Carla's voice
        elif role == "Rachel":
            sentiment = "direct" # Rachel's voice

        # --- Context-aware responses based on Rohan's last query ---
        # Look at the last message from Rohan in the chat history for specific context
        last_rohan_message_lower = ""
        for msg in reversed(chat_history):
            if msg['role'] == 'user' and 'parts' in msg and len(msg['parts']) > 0 and 'text' in msg['parts'][0]:
                last_rohan_message_lower = msg['parts'][0]['text'].lower()
                break

        if "initial submission" in prompt_lower and role == "Ruby":
            response_text = random.choice([
                "Hi Rohan, thank you for sharing this. We understand. Our goal is to bring coordination to your health. I'm flagging your concerns for Dr. Warren to review immediately. We're here to make this seamless for you.",
                "Welcome, Rohan! We've received your initial details. Your concerns about stress and Garmin data are noted. We're initiating a comprehensive review with Dr. Warren to build your coordinated plan.",
                "Rohan, great to have you onboard! We're already working to consolidate your health data and address your initial concerns about routine and stress. Expect a prompt follow-up from Dr. Warren.",
                "Elyx is here to streamline your health journey, Rohan. Your initial input is valuable; we're now mobilizing the team to craft your personalized, efficient plan."
            ])
            decision_rationale = "Prioritizing Rohan's core concern of 'ad-hoc health' by initiating a coordinated clinical review, maximizing early engagement output."
            time_efficiency = "Immediate flagging for quick initial response."
            next_steps = "Ruby will contact Sarah to begin medical record consolidation."
        elif "medical records" in last_rohan_message_lower and role == "Dr. Warren":
            response_text = random.choice([
                "Dr. Warren here. I've reviewed your initial submission. The symptoms and data strongly suggest autonomic dysfunction (Pillar 1). To proceed, we must consolidate your complete medical records. This is non-negotiable for safety. Ruby will manage the process.",
                "Dr. Warren. Your initial data points towards autonomic imbalance. Full medical records are vital for a safe, effective strategy. Ruby will handle the logistics.",
                "This is Dr. Warren. To build a robust plan for your autonomic health, complete medical records are essential. Ruby will streamline this process for you.",
                "For precise clinical strategy, Rohan, comprehensive medical records are a foundational requirement. This ensures we maximize safety and avoid redundant efforts. Ruby will manage the collection."
            ])
            decision_rationale = "To establish a clinical-grade strategy, ensure safety, and avoid redundant testing by consolidating complete medical history. This is a foundational step for maximizing long-term health output and preventing future costly errors."
            pillar_impact = "Pillar 1 (Autonomic Health)"
            next_steps = "Complete medical record consolidation via Ruby."
            sentiment = "authoritative"
        elif "medical records" in last_rohan_message_lower and role == "Ruby":
            response_text = random.choice([
                "The timeline can vary depending on clinics' response speed, but we will manage the entire process. We typically aim for records within 2-3 weeks. We'll provide daily updates to keep you in the loop, ensuring minimal disruption to your schedule.", # Adjusted phrasing
                "We're on it! Consolidating your records is our priority. We'll handle all communication with clinics and keep you updated every step of the way, minimizing your effort.",
                "Don't worry about the record collection. We'll streamline the process, aiming for completion within 2-3 weeks, and notify you as soon as they're ready. Your time is valuable.",
                "Sarah has been briefed on the medical record collection. We anticipate completion within 2-3 weeks, and you'll receive real-time updates, ensuring minimal disruption to your schedule."
            ])
            time_efficiency = "Elyx team handles logistics to save Rohan's time."
            next_steps = "Ruby will send daily updates on record collection progress."
            sentiment = "positive"
        elif "fitness goals" in last_rohan_message_lower and role == "Advik":
            response_text = random.choice([
                "Rohan, Advik here. A good first step is a comprehensive movement assessment to understand your baseline and identify any imbalances. Ruby can help schedule this with Rachel. This will inform your personalized exercise plan, maximizing your workout output.",
                "Advik. To optimize your workouts and prevent injury, a baseline movement assessment is key. Ruby can coordinate with Rachel for this. It's a data-driven approach to maximize your fitness investment.",
                "For your fitness goals, Advik recommends a detailed movement assessment. This will ensure your personalized plan is efficient and effective, fitting your demanding schedule. Ruby will assist with scheduling.",
                "To truly elevate your fitness, Rohan, Advik advises a foundational movement assessment. This data will allow Rachel to craft a highly efficient, personalized exercise program. Ruby will manage the scheduling."
            ])
            decision_rationale = "To establish a data-driven baseline for personalized exercise programming, optimizing for Rohan's time constraints and avoiding injury. This maximizes efficiency and adherence for long-term gains."
            pillar_impact = "Pillar 4 (Structural Health)"
            next_steps = "Schedule movement assessment with Rachel via Ruby."
            sentiment = "analytical"
        elif "stress" in last_rohan_message_lower and role == "Carla":
            response_text = random.choice([
                "Rohan, Carla here. For immediate stress support, focus on consistent hydration and mindful eating. Avoiding processed snacks can also help. These are simple, low-cost dietary adjustments that integrate easily.",
                "Carla. To combat stress and energy dips, prioritize hydration and mindful eating. Small, consistent efforts here yield significant benefits without major lifestyle overhauls or cost.",
                "For quick stress relief, Carla advises focusing on hydration and making conscious food choices. These are fundamental, zero-cost practices that can make an immediate difference.",
                "Carla suggests immediate, low-effort nutritional tweaks for stress: consistent hydration and mindful eating. These foundational habits are highly impactful and seamlessly integrate into your day."
            ])
            pillar_impact = "Pillar 3 (Fuel), Pillar 5 (Stress Resilience)"
            monetary_factor = "Low-cost/no-cost dietary adjustments."
            time_efficiency = "Easy to integrate, minimal time commitment."
            next_steps = "Focus on consistent hydration and mindful eating practices daily."
            sentiment = "practical"
        elif "couch stretch" in last_rohan_message_lower and role == "Rachel":
            response_text = random.choice([
                "Hi Rohan, Rachel here. Glad to hear the couch stretch provided some relief! That's a great start. Now, let's discuss integrating a few more targeted mobility drills to build on that progress. How does adding 5 minutes post-run sound?", # More interactive
                "Excellent! The couch stretch is a foundational win. Rachel here. Building on that, we can explore dynamic stretches or foam rolling for sustained back health. What's your availability for a quick video call to review options?", # More interactive
                "Fantastic! Rachel. That 2-minute stretch is proving its value. To further enhance your spinal health and prevent future discomfort, we recommend incorporating it consistently and exploring complementary core stability exercises. How does this fit your schedule?" # More interactive
            ])
            decision_rationale = "To address Rohan's reported lower back pain, a common issue from prolonged sitting during travel, with a time-efficient, non-invasive intervention that integrates into his daily routine for maximum relief."
            pillar_impact = "Pillar 4 (Structural Health)"
            time_efficiency = "2-minute, quick intervention."
            next_steps = "Perform couch stretch daily and report back on effectiveness; explore additional mobility drills."
            intervention_effect = "Initial relief, focus on long-term mobility." # Default for this intervention
            sentiment = "direct"
        elif "q1 diagnostic panel" in prompt_lower and role == "Ruby": # For initial diagnostic scheduling
            response_text = random.choice([
                "Rohan, it's time to schedule your Q1 diagnostic panel. This comprehensive test will give us a baseline for your metabolic and hormonal health. We can arrange a phlebotomist to come to your office. Does next Tuesday morning work? This maximizes your convenience.",
                "Your quarterly diagnostic is due. This panel is key to tracking your metabolic health. We can send a phlebotomist to your office for ultimate convenience. Let us know your availability next week.",
                "Time for your Q1 diagnostic panel! This essential data helps us fine-tune your plan. We can schedule a phlebotomist at your office to save your valuable time. What day next week works best?",
                "Ruby here. Your Q1 diagnostic panel is ready for scheduling. To maximize your time efficiency, we can arrange a phlebotomist to visit your office. Please confirm your availability next Tuesday."
            ])
            decision_rationale = "Full diagnostic test panel every three months is a core program requirement to track progress on biomarkers and identify new areas for intervention. This maximizes long-term health output by providing critical data for personalized adjustments, minimizing future health costs."
            pillar_impact = "Pillar 1 (Autonomic), Pillar 3 (Fuel), Pillar 5 (Stress Resilience)"
            time_efficiency = "Phlebotomist to office for convenience."
            next_steps = "Confirm availability for phlebotomist visit next Tuesday."
            sentiment = "positive"
        elif "apo b" in last_rohan_message_lower and role == "Dr. Warren":
            # Simulate different effectiveness based on current ApoB
            if current_metrics["ApoB"] < 90:
                effect_text = "Your ApoB has shown significant improvement, indicating positive progress on cardiovascular health. This is a great win for your metabolic health!"
                effectiveness = "effective"
                next_steps = "Continue current dietary and exercise interventions; re-evaluate in Q3 to ensure sustained progress."
            else:
                effect_text = "Your ApoB remains elevated, requiring continued focus and potential adjustments to interventions. This is a key area for maximizing your long-term health output."
                effectiveness = "partially effective"
                next_steps = "Carla will refine your dietary plan, and Rachel will review exercise intensity. We'll re-test in Q2 to track progress."

            response_text = random.choice([
                f"Dr. Warren here. Your Q1 diagnostics show ApoB at {current_metrics['ApoB']} mg/dL. {effect_text} This is a primary focus for long-term heart disease risk reduction, aligning with your top health goal. Carla will lead dietary interventions (reducing saturated fat, increasing fiber), and Rachel's exercise plan will be critical. We will aggressively target this with lifestyle changes and re-test in Q2. How do you feel about these adjustments?", # Added question
                f"Rohan, your ApoB is {current_metrics['ApoB']} mg/dL. {effect_text} This is a primary focus for long-term heart disease risk reduction, aligning with your top health goal. Carla will lead dietary interventions (reducing saturated fat, increasing fiber), and Rachel's exercise plan will be critical. We will aggressively target this with lifestyle changes and re-test in Q2.",
                f"Your Q1 diagnostics show elevated ApoB. This is a serious indicator for heart health, directly impacting your primary goal. Our strategy involves aggressive, integrated lifestyle changes via Carla and Rachel, aiming for significant reduction by Q2. This is a high-ROI health investment. What are your thoughts on this intensified focus?" # Added question
            ])
            decision_rationale = "Elevated ApoB is a serious cardiovascular risk factor based on diagnostics. The intervention prioritizes Rohan's top health goal, using integrated lifestyle changes for maximum impact and long-term investment. This approach is more sustainable than medication alone and is a cost-effective preventative measure."
            pillar_impact = "Pillar 3 (Fuel), Pillar 4 (Structural), Pillar 1 (Autonomic)"
            monetary_factor = "Cost-effective preventative measure."
            intervention_effect = effectiveness
            next_steps = next_steps # From conditional logic above
            sentiment = "authoritative"
        elif "travel protocol" in last_rohan_message_lower and role == "Advik":
            response_text = random.choice([
                "For your Tokyo trip, we'll build a precise light exposure and avoidance schedule to shift your circadian rhythm, and Rachel will find a suitable gym near your hotel. This proactive approach aims to minimize jet lag and maintain your health routine, maximizing your performance during demanding travel. Your detailed guide is in your portal.",
                "Advik. To ensure your demanding travel doesn't derail your progress, we're implementing a bespoke travel protocol. This includes circadian rhythm adjustment via light exposure and pre-vetted exercise options near your hotel, maximizing your efficiency on the road. Any specific concerns about this plan?", # Added question
                "Your upcoming travel is an opportunity to optimize your resilience. Advik will provide a detailed jet lag protocol and Rachel will identify convenient workout spots, ensuring your health remains a priority even with time constraints. How does this sound for integration?", # Added question
                "Advik here. For your upcoming travel, we've designed a comprehensive protocol to combat jet lag and maintain your routine. This includes personalized light exposure plans and vetted local gym options, ensuring peak performance on your trip. Do you have any questions about the specifics?" # Added question
            ])
            decision_rationale = "To proactively mitigate the known impact of international travel on Rohan's POTS and overall performance, ensuring his demanding work schedule doesn't derail health progress. Focus on time-efficient, integrated solutions that fit his travel lifestyle, maximizing his output during business trips."
            pillar_impact = "Pillar 1 (Autonomic), Pillar 2 (Sleep), Pillar 4 (Structural), Pillar 5 (Stress Resilience)"
            time_efficiency = "Precise schedule for jet lag, gym finding for efficiency."
            next_steps = "Follow personalized light exposure schedule and utilize identified local gyms during travel."
            sentiment = "analytical"
        elif "illness" in last_rohan_message_lower and role == "Dr. Warren":
            response_text = random.choice([
                "Rohan, the biotelemetry strongly suggests a viral infection. We are initiating the Elyx Sick Day Protocol immediately. You must postpone your board meeting. Your cognitive function will be severely impaired, and you risk a much longer recovery if you push through. Ruby will manage rescheduling.",
                "Dr. Warren here. Your current biometrics indicate a significant viral load. It's critical you engage the Elyx Sick Day Protocol and postpone your meeting. Pushing through will severely extend recovery and compromise your long-term health investment. Ruby will assist.",
                "This is Dr. Warren. Immediate rest and the Elyx Sick Day Protocol are paramount. Your current state demands full recovery focus; attempting the board meeting will be counterproductive and costly in the long run. Ruby is on standby for logistics.",
                "Dr. Warren: Biotelemetry confirms a viral infection. We're activating the Elyx Sick Day Protocol. Postponing your meeting is non-negotiable; pushing now will severely extend your recovery and incur greater long-term costs. Ruby will handle the rescheduling."
            ])
            decision_rationale = "Prioritizing immediate health stabilization and long-term recovery over short-term business commitments, as pushing through illness risks severe setbacks and prolonged recovery, ultimately impacting long-term performance and health investment. This maximizes long-term output and avoids higher future medical costs."
            pillar_impact = "All Pillars (Acute Health Crisis)"
            monetary_factor = "Avoids higher future medical costs."
            next_steps = "Engage Elyx Sick Day Protocol: rest, hydration, Ruby will reschedule meetings."
            intervention_effect = "Severe fatigue, recovery score dropped significantly." # Default for this intervention
            sentiment = "authoritative"
        elif "piano" in last_rohan_message_lower and role == "Neel":
            response_text = random.choice([
                "We agree. Learning piano is an excellent intervention for cognitive longevity, engaging multiple brain domains. We will add 'Weekly Piano Practice' as a trackable goal within Pillar 5 (Stress Management) of your Plan. This integrates a personal interest with health investment and offers a non-monetary health benefit.",
                "Neel. Incorporating piano practice is a brilliant idea for cognitive health and stress. We'll formalize 'Weekly Piano Practice' as a trackable goal in Pillar 5. It's a high-value, non-monetary investment that integrates seamlessly.",
                "Absolutely, Rohan. Piano practice is a fantastic, personalized approach to cognitive longevity and stress resilience. We'll add it to Pillar 5, allowing you to track its impact on your HRV and focus. A truly holistic health investment.",
                "Neel here. Your interest in piano is a perfect fit for cognitive enhancement and stress management. We'll integrate 'Weekly Piano Practice' as a trackable goal in Pillar 5, a valuable, non-monetary investment in your long-term well-being."
            ])
            decision_rationale = "To align with Rohan's interest in cognitive longevity and stress management, providing a personalized, engaging, and long-term health investment that integrates naturally into his lifestyle and offers a non-monetary benefit, maximizing his personal growth output."
            pillar_impact = "Pillar 5 (Stress Resilience), Cognitive Health"
            monetary_factor = "Non-monetary health benefit."
            time_efficiency = "Integrated into weekly routine."
            next_steps = "Begin weekly piano practice; track subjective focus and HRV."
            sentiment = "positive"
        elif "deviate from exercise" in last_rohan_message_lower and role in ["Rachel", "Advik"]:
            response_text = random.choice([
                "Understood, Rohan. It's common for plans to need adjustments. Let's adapt. We can explore shorter, more flexible routines for your travel weeks, or bodyweight alternatives that require no equipment, maximizing adherence even when time is tight. Your health journey is dynamic.",
                "Rachel/Advik here. We understand adherence can fluctuate. Instead of skipping, let's pivot to a quick 15-minute bodyweight circuit or a targeted mobility flow. The goal is consistency and adaptability, maximizing your output even on challenging days.",
                "It's okay to deviate; the key is quick adaptation. We'll revise your plan to include more flexible, time-efficient options that fit your dynamic schedule, ensuring you maintain momentum without feeling overwhelmed. This maximizes long-term adherence.",
                "We anticipated dynamic adherence, Rohan. Rachel and Advik will provide adaptable, time-efficient exercise alternatives, like hotel room workouts, ensuring your progress continues uninterrupted, even with unforeseen schedule changes."
            ])
            decision_rationale = "Adapting to Rohan's dynamic schedule and adherence patterns to ensure continued progress, focusing on flexible and time-efficient alternatives to maximize health output without feeling forced."
            monetary_factor = "Suggests bodyweight alternatives (cost-effective)."
            time_efficiency = "Shorter, more flexible routines."
            next_steps = "Implement flexible exercise routines; report on adherence."
            intervention_effect = "Plan adapted to improve adherence; metrics may stabilize or improve."
            sentiment = "direct" if role == "Rachel" else "analytical"
        elif "monetary concern" in last_rohan_message_lower and role in ["Ruby", "Neel"]: # Concierge handles monetary
            response_text = random.choice([
                "We hear your concern about monetary factors. We always strive to provide cost-effective alternatives and ensure every recommendation is a justified investment in your long-term health. For example, simple dietary changes can have a huge impact on ApoB without high cost.",
                "Elyx is about maximizing health ROI. We'll always present cost-effective alternatives and clearly articulate the long-term value of any investment, ensuring your plan is sustainable and delivers maximum output within your budget.",
                "Your financial considerations are important. We focus on high-impact, low-cost interventions where possible, and for any investment, we'll outline the long-term health benefits and how it prevents future, higher costs.",
                "We prioritize value, Rohan. For every recommendation, we consider cost-effectiveness and demonstrate its long-term health ROI, ensuring your investments are prudent and maximize your healthy years."
            ])
            decision_rationale = "Prioritizing Rohan's financial considerations by offering cost-effective alternatives and justifying investments as long-term health benefits, ensuring the plan is sustainable and maximizes value."
            monetary_factor = "Emphasizes cost-effectiveness and justified investment."
            next_steps = "Review proposed cost-effective alternatives with relevant specialist."
            sentiment = "positive"
        elif "time" in last_rohan_message_lower or "busy" in last_rohan_message_lower or "quick" in last_rohan_message_lower and role in ["Ruby", "Neel"]: # Concierge handles time
            response_text = random.choice([
                "We understand your time constraints. Our goal is to seamlessly integrate health into your busy life. We can focus on micro-interventions, like 5-minute mobility breaks or strategic meal prepping with Javier, to maximize health output with minimal time investment.",
                "Your time is precious. We design interventions for maximum impact in minimal time. Think strategic 10-minute bursts, or leveraging your cook for efficient meal prep, turning health into an integrated lifestyle, not a chore.",
                "We specialize in optimizing for busy schedules. We'll streamline your health activities, focusing on high-leverage actions that fit into your existing routine, ensuring consistent progress without adding burden.",
                "Elyx excels at time-optimization. We'll identify high-impact, low-time interventions and integrate them seamlessly into your demanding schedule, maximizing your health benefits without friction."
            ])
            decision_rationale = "Adapting the plan to Rohan's severe time constraints by focusing on micro-interventions and efficient strategies, ensuring health activities are integrated seamlessly and maximize output per minute invested."
            time_efficiency = "Focus on micro-interventions and strategic planning."
            next_steps = "Implement time-efficient strategies; track impact on schedule and health."
            sentiment = "positive"
        else:
            # General check-in/response, now more varied and interactive
            response_text = random.choice([
                f"Hi Rohan, {role} here. We're continuously optimizing your plan based on your feedback and data to maximize your health output. How are things going with your current priorities?",
                f"Understood. We'll integrate this into your personalized plan to maximize your health output, considering your time and value. Thanks for the feedback. What's on your mind today?", # Added question
                f"That's a great point, {ELYX_TEAM_PERSONAS[role]['role']} will look into that for you, ensuring it aligns with your priorities and lifestyle. Is there anything else pressing?", # Added question
                f"We're always looking for ways to make your health journey more seamless and impactful, turning medical procedures into lifestyle habits. What's your biggest challenge this week?", # Added question
                f"Just checking in, Rohan. How are you feeling about your current progress and any new challenges you're facing? {role} is here to support. What's your current focus?", # Added question
                f"We've noted your recent activity. {role} is reviewing your latest data for potential optimizations. Anything specific you'd like to discuss or any new concerns?", # Added question
                f"Hello Rohan, this is {role}. Your recent data looks promising/needs attention (depending on metrics). We're here to help you maximize your health output. How can we assist you today?", # More direct check-in
                f"Rohan, {role} here. We're reviewing your progress. Remember, consistency is key to long-term gains. What's one small win you had this week?" # Encouraging feedback
            ])
            decision_rationale = "Routine check-in / general response, emphasizing personalized care, value, and lifestyle integration."
            pillar_impact = "General"
            monetary_factor = "General emphasis on value."
            time_efficiency = "General emphasis on efficiency."
            next_steps = "Continue with current plan; Elyx team will review for further optimizations."
            sentiment = "positive" # Default sentiment for general Elyx responses

    return response_text, decision_rationale, pillar_impact, health_metrics_snapshot, intervention_effect, monetary_factor, time_efficiency, service_interaction_type, specialist_involved, next_steps, sentiment

# -------------------------
# Main generate function and consolidated API endpoint
# -------------------------
@app.route("/api/generate-journey", methods=["POST"])
def api_generate_journey():
    """
    Generates the full 8-month journey data dynamically.
    This endpoint is called by the frontend to get the entire simulated log.
    """
    # CRITICAL: Reset pools and global state at the start of every generation request
    reset_pools()
    global CURRENT_HEALTH_METRICS, ROHAN_ASKED_TOPICS_MEMORY
    CURRENT_HEALTH_METRICS = {
        "HRV": 45, "RestingHR": 65, "GlucoseAvg": 105, "ApoB": 105,
        "RecoveryScore": 70, "DeepSleep": 60, "POTS_symptoms": "moderate", "BackPain": "mild"
    }
    ROHAN_ASKED_TOPICS_MEMORY = []

    all_timeline_events = [] # This will store only the significant events for the timeline
    all_chat_messages = [] # This will store ALL messages for the chat tab

    # Initialize the simulation state
    sim_state = {
        "metrics": CURRENT_HEALTH_METRICS.copy(), # Pass a copy of initial metrics
        "in_travel": False,
        "last_diag_week": 0
    }

    # Initial onboarding messages (these are always included in full chat and also the first timeline event)
    rohan_msg, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist, rohan_next_steps, rohan_sentiment = generate_llm_response("Rohan", "Initial onboarding: I need a proper, coordinated plan. My Garmin HR seems off.", sim_state["metrics"], all_chat_messages, all_timeline_events, current_sim_date=START_DATE)
    all_chat_messages.append({"sender": "Rohan", "content": rohan_msg, "timestamp": format_ts(START_DATE), "sentiment": rohan_sentiment, "serviceInteractionType": rohan_interaction_type, "specialistInvolved": rohan_specialist})
    
    ruby_msg, ruby_rationale, ruby_pillar, ruby_metrics, ruby_effect, ruby_monetary, ruby_time, ruby_interaction_type, ruby_specialist, ruby_next_steps, ruby_sentiment = generate_llm_response("Ruby", "welcome Rohan and acknowledge concerns", sim_state["metrics"], all_chat_messages, all_timeline_events, current_sim_date=START_DATE + timedelta(minutes=5))
    all_chat_messages.append({"sender": "Ruby", "content": ruby_msg, "timestamp": format_ts(START_DATE + timedelta(minutes=5)), "sentiment": ruby_sentiment, "serviceInteractionType": ruby_interaction_type, "specialistInvolved": ruby_specialist})
    
    # Onboarding event is a major timeline event
    all_timeline_events.append({
        "type": "event", "eventId": "onboarding_start", "timestamp": format_ts(START_DATE),
        "description": "Member Onboarding Initiated", "details": f"Rohan's initial concern: '{rohan_msg}' | Ruby's welcome: '{ruby_msg}'", # Combine initial messages here
        "decisionRationale": "Standard Elyx onboarding process to establish baseline and goals for a personalized plan.",
        "healthMetricsSnapshot": sim_state["metrics"].copy(), "interventionEffect": None,
        "monetaryFactor": None, "timeEfficiency": None, "serviceInteractionType": "onboarding_event", 
        "specialistInvolved": "Elyx Team", "nextSteps": "Complete medical record consolidation and initial assessments."
    })


    # Loop through the weeks and generate events
    for week in range(1, WEEKS_TO_GENERATE + 1):
        current_week_start_date = START_DATE + timedelta(weeks=week-1)
        
        # --- Weekly Check-in (Ruby/Neel) ---
        if week % 4 == 0: # Monthly review - these are considered major messages for timeline
            team_member_name = random.choice(["Neel", "Ruby"])
            msg_context = f"weekly/monthly check-in for progress review and alignment with goals. Current metrics: {sim_state['metrics']}. Rohan's adherence is ~{int(PLAN_ADHERENCE_PROB*100)}%."
            msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team, team_sentiment = generate_llm_response(team_member_name, msg_context, sim_state["metrics"], all_chat_messages, all_timeline_events, current_sim_date=current_week_start_date)
            
            # Add to full chat history
            all_chat_messages.append({"sender": team_member_name, "content": msg, "timestamp": format_ts(current_week_start_date), "sentiment": team_sentiment, "serviceInteractionType": interaction_type, "specialistInvolved": specialist})
            # Add to timeline_events as a major message
            all_timeline_events.append({
                "type": "message", "sender": team_member_name, "timestamp": format_ts(current_week_start_date),
                "content": msg, "pillar": pillar, "relatedTo": "Previous interactions",
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": "proactive check-in", 
                "specialistInvolved": specialist, "nextSteps": next_steps_team, "sentiment": team_sentiment
            })
            
            # Rohan's response to check-in
            rohan_response_msg, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist, rohan_next_steps, rohan_sentiment = generate_llm_response("Rohan", f"response to monthly check-in. Current state: {sim_state['metrics']}", sim_state["metrics"], all_chat_messages, all_timeline_events, current_sim_date=current_week_start_date + timedelta(minutes=random.randint(5, 15)))
            all_chat_messages.append({"sender": "Rohan", "content": rohan_response_msg, "timestamp": format_ts(current_week_start_date + timedelta(minutes=random.randint(5, 15))), "sentiment": rohan_sentiment, "serviceInteractionType": rohan_interaction_type, "specialistInvolved": rohan_specialist})
            all_timeline_events.append({
                "type": "message", "sender": "Rohan", "timestamp": format_ts(current_week_start_date + timedelta(minutes=random.randint(5, 15))),
                "content": rohan_response_msg, "pillar": rohan_pillar, "relatedTo": "Monthly check-in",
                "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                "timeEfficiency": rohan_time, "serviceInteractionType": "member-initiated query", 
                "specialistInvolved": rohan_specialist, "nextSteps": rohan_next_steps, "sentiment": rohan_sentiment
            })


        # --- Diagnostic Tests (Every 3 months) ---
        if (week_index - 1) % DIAGNOSTIC_EVERY_WEEKS == 0:
            diag_day = current_week_start_date + timedelta(days=random.randint(1, 3))
            ruby_msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team, team_sentiment = generate_llm_response("Ruby", "schedule Q1/Q2/Q3 diagnostic panel", sim_state["metrics"], all_chat_messages, all_timeline_events, current_sim_date=diag_day)
            
            all_chat_messages.append({"sender": "Ruby", "content": ruby_msg, "timestamp": format_ts(diag_day), "sentiment": team_sentiment, "serviceInteractionType": interaction_type, "specialistInvolved": specialist})
            all_timeline_events.append({
                "type": "message", "sender": "Ruby", "timestamp": format_ts(diag_day),
                "content": ruby_msg, "pillar": pillar, "relatedTo": "Program requirement",
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": "diagnostic_scheduling", 
                "specialistInvolved": specialist, "nextSteps": next_steps_team, "sentiment": team_sentiment
            })
            
            # Rohan's response to diagnostic scheduling
            rohan_response_msg, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist, rohan_next_steps, rohan_sentiment = generate_llm_response("Rohan", f"response to diagnostic scheduling. Current state: {sim_state['metrics']}", sim_state["metrics"], all_chat_messages, all_timeline_events, current_sim_date=diag_day + timedelta(minutes=random.randint(5, 15)))
            all_chat_messages.append({"sender": "Rohan", "content": rohan_response_msg, "timestamp": format_ts(diag_day + timedelta(minutes=random.randint(5, 15))), "sentiment": rohan_sentiment, "serviceInteractionType": rohan_interaction_type, "specialistInvolved": rohan_specialist})
            all_timeline_events.append({
                "type": "message", "sender": "Rohan", "timestamp": format_ts(diag_day + timedelta(minutes=random.randint(5, 15))),
                "content": rohan_response_msg, "pillar": rohan_pillar, "relatedTo": "Diagnostic scheduling",
                "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                "timeEfficiency": rohan_time, "serviceInteractionType": "member-initiated query", 
                "specialistInvolved": rohan_specialist, "nextSteps": rohan_next_steps, "sentiment": rohan_sentiment
            })

            # Event for diagnostic scheduled
            all_timeline_events.append({
                "type": "event", "eventId": f"diagnostic_scheduled_week_{week_index}", "timestamp": format_ts(diag_day),
                "description": f"Quarterly Diagnostic Panel Scheduled (Week {week_index})",
                "details": "Comprehensive baseline tests for metabolic and hormonal health.",
                "decisionRationale": rationale, "healthMetricsSnapshot": sim_state["metrics"].copy(),
                "interventionEffect": None, "monetaryFactor": None, "timeEfficiency": None,
                "serviceInteractionType": "diagnostic_scheduling_event", 
                "specialistInvolved": "Ruby", "nextSteps": next_steps_team
            })

            # Simulate results discussion a week later
            results_date = diag_day + timedelta(days=7)
            
            if week_index == 12: # Q1 results
                # Simulate elevated ApoB and initial metrics
                sim_state["metrics"]["ApoB"] = 105
                sim_state["metrics"]["HRV"] = 48 # Slight increase
                sim_state["metrics"]["POTS_symptoms"] = "moderate"
                sim_state["metrics"]["BackPain"] = "mild"
                
                dr_msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team, team_sentiment = generate_llm_response("Dr. Warren", f"discuss Q1 diagnostic results, elevated ApoB: {sim_state['metrics']['ApoB']}", sim_state["metrics"], all_chat_messages, all_timeline_events, current_sim_date=results_date)
                
                all_chat_messages.append({"sender": "Dr. Warren", "content": dr_msg, "timestamp": format_ts(results_date), "sentiment": team_sentiment, "serviceInteractionType": interaction_type, "specialistInvolved": specialist})
                all_timeline_events.append({
                    "type": "message", "sender": "Dr. Warren", "timestamp": format_ts(results_date),
                    "content": dr_msg, "pillar": pillar, "relatedTo": "Q1 Diagnostics",
                    "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                    "interventionEffect": effect, "monetaryFactor": monetary,
                    "timeEfficiency": time_eff, "serviceInteractionType": "diagnostic_results_review", 
                    "specialistInvolved": specialist, "nextSteps": next_steps_team, "sentiment": team_sentiment
                })
                
                rohan_response_msg, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist, rohan_next_steps, rohan_sentiment = generate_llm_response("Rohan", f"response to ApoB results. Current state: {sim_state['metrics']}", sim_state["metrics"], all_chat_messages, all_timeline_events, current_sim_date=results_date + timedelta(minutes=random.randint(5, 15)))
                all_chat_messages.append({"sender": "Rohan", "content": rohan_response_msg, "timestamp": format_ts(results_date + timedelta(minutes=random.randint(5, 15))), "sentiment": rohan_sentiment, "serviceInteractionType": rohan_interaction_type, "specialistInvolved": rohan_specialist})
                all_timeline_events.append({
                    "type": "message", "sender": "Rohan", "timestamp": format_ts(results_date + timedelta(minutes=random.randint(5, 15))),
                    "content": rohan_response_msg, "pillar": rohan_pillar, "relatedTo": "ApoB discussion",
                    "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                    "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                    "timeEfficiency": rohan_time, "serviceInteractionType": "member-initiated query", 
                    "specialistInvolved": rohan_specialist, "nextSteps": rohan_next_steps, "sentiment": rohan_sentiment
                })

                all_timeline_events.append({
                    "type": "event", "eventId": f"q1_results_week_{week_index}", "timestamp": format_ts(results_date),
                    "description": "Q1 Diagnostic Results Reviewed", "details": f"Elevated ApoB ({sim_state['metrics']['ApoB']} mg/dL) identified as primary focus.",
                    "decisionRationale": rationale, "healthMetricsSnapshot": sim_state["metrics"].copy(),
                    "interventionEffect": effect, "monetaryFactor": monetary, "timeEfficiency": time_eff,
                    "serviceInteractionType": "diagnostic_review_event", 
                    "specialistInvolved": "Dr. Warren",
                    "nextSteps": next_steps_team
                })

            elif week_index == 24: # Q2 results
                # Simulate improvement due to interventions
                sim_state["metrics"]["ApoB"] = random.randint(70, 85)
                sim_state["metrics"]["HRV"] = random.randint(55, 70)
                sim_state["metrics"]["POTS_symptoms"] = "mild"
                sim_state["metrics"]["BackPain"] = "none"
                
                dr_msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team, team_sentiment = generate_llm_response("Dr. Warren", f"discuss Q2 diagnostic results, improved ApoB: {sim_state['metrics']['ApoB']}", sim_state["metrics"], all_chat_messages, all_timeline_events, current_sim_date=results_date)
                
                all_chat_messages.append({"sender": "Dr. Warren", "content": dr_msg, "timestamp": format_ts(results_date), "sentiment": team_sentiment, "serviceInteractionType": interaction_type, "specialistInvolved": specialist})
                all_timeline_events.append({
                    "type": "message", "sender": "Dr. Warren", "timestamp": format_ts(results_date),
                    "content": dr_msg, "pillar": pillar, "relatedTo": "Q2 Diagnostics",
                    "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                    "interventionEffect": effect, "monetaryFactor": monetary,
                    "timeEfficiency": time_eff, "serviceInteractionType": "diagnostic_results_review", 
                    "specialistInvolved": specialist, "nextSteps": next_steps_team, "sentiment": team_sentiment
                })
                
                rohan_response_msg, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist, rohan_next_steps, rohan_sentiment = generate_llm_response("Rohan", f"response to improved ApoB results. Current state: {sim_state['metrics']}", sim_state["metrics"], all_chat_messages, all_timeline_events, current_sim_date=results_date + timedelta(minutes=random.randint(5, 15)))
                all_chat_messages.append({"sender": "Rohan", "content": rohan_response_msg, "timestamp": format_ts(results_date + timedelta(minutes=random.randint(5, 15))), "sentiment": rohan_sentiment, "serviceInteractionType": rohan_interaction_type, "specialistInvolved": rohan_specialist})
                all_timeline_events.append({
                    "type": "message", "sender": "Rohan", "timestamp": format_ts(results_date + timedelta(minutes=random.randint(5, 15))),
                    "content": rohan_response_msg, "pillar": rohan_pillar, "relatedTo": "ApoB discussion",
                    "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                    "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                    "timeEfficiency": rohan_time, "serviceInteractionType": "member-initiated query", 
                    "specialistInvolved": rohan_specialist, "nextSteps": rohan_next_steps, "sentiment": rohan_sentiment
                })

                all_timeline_events.append({
                    "type": "event", "eventId": f"q2_results_week_{week_index}", "timestamp": format_ts(results_date),
                    "description": "Q2 Diagnostic Results Reviewed", "details": f"Improved ApoB ({sim_state['metrics']['ApoB']} mg/dL) due to interventions.",
                    "decisionRationale": rationale, "healthMetricsSnapshot": sim_state["metrics"].copy(),
                    "interventionEffect": effect, "monetaryFactor": monetary, "timeEfficiency": time_eff,
                    "serviceInteractionType": "diagnostic_review_event", 
                    "specialistInvolved": "Dr. Warren",
                    "nextSteps": next_steps_team
                })

        # Exercise updates every EXERCISE_UPDATE_EVERY_WEEKS
    if (week_index - 1) % EXERCISE_UPDATE_EVERY_WEEKS == 0:
        ex_day = current_week_start_date + timedelta(days=random.randint(1, 4))
        
        # Simulate Rohan's adherence (50% adherence)
        if random.random() < PLAN_ADHERENCE_PROB: # Rohan adheres
            rohan_adherence_msg, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist, rohan_next_steps, rohan_sentiment = generate_llm_response("Rohan", f"adhere to exercise plan. Current state: {sim_state['metrics']}", sim_state["metrics"], all_chat_messages, all_timeline_events, current_sim_date=ex_day)
            all_chat_messages.append({"sender": "Rohan", "content": rohan_adherence_msg, "timestamp": format_ts(ex_day), "sentiment": rohan_sentiment, "serviceInteractionType": rohan_interaction_type, "specialistInvolved": rohan_specialist})
            all_timeline_events.append({
                "type": "message", "sender": "Rohan", "timestamp": format_ts(ex_day),
                "content": rohan_adherence_msg, "pillar": rohan_pillar, "relatedTo": "Exercise adherence",
                "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                "timeEfficiency": rohan_time, "serviceInteractionType": "member_adherence_report",
                "specialistInvolved": rohan_specialist, "nextSteps": rohan_next_steps, "sentiment": rohan_sentiment
            })
            # Simulate positive metric changes from adherence
            sim_state["metrics"]["HRV"] = min(90, sim_state["metrics"]["HRV"] + random.randint(1, 5))
            sim_state["metrics"]["RecoveryScore"] = min(95, sim_state["metrics"]["RecoveryScore"] + random.randint(3, 8))
            sim_state["metrics"]["RestingHR"] = max(50, sim_state["metrics"]["RestingHR"] - random.randint(0, 2))

        else: # Rohan deviates
            rohan_deviation_msg, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist, rohan_next_steps, rohan_sentiment = generate_llm_response("Rohan", f"deviate from exercise plan due to travel/time/soreness. Current state: {sim_state['metrics']}", sim_state["metrics"], all_chat_messages, all_timeline_events, current_sim_date=ex_day)
            all_chat_messages.append({"sender": "Rohan", "content": rohan_deviation_msg, "timestamp": format_ts(ex_day), "sentiment": rohan_sentiment, "serviceInteractionType": rohan_interaction_type, "specialistInvolved": rohan_specialist})
            all_timeline_events.append({
                "type": "message", "sender": "Rohan", "timestamp": format_ts(ex_day),
                "content": rohan_deviation_msg, "pillar": rohan_pillar, "relatedTo": "Exercise deviation",
                "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                "timeEfficiency": rohan_time, "serviceInteractionType": "member_adherence_report",
                "specialistInvolved": rohan_specialist, "nextSteps": rohan_next_steps, "sentiment": rohan_sentiment
            })
            # Elyx team adapts
            adapt_person = random.choice(["Rachel", "Advik"])
            adapt_msg, adapt_rationale, adapt_pillar, adapt_metrics, adapt_effect, adapt_monetary, adapt_time, adapt_interaction_type, adapt_specialist, adapt_next_steps, adapt_sentiment = generate_llm_response(adapt_person, f"adapt to Rohan's exercise deviation. Current state: {sim_state['metrics']}", sim_state["metrics"], all_chat_messages, all_timeline_events, current_sim_date=ex_day + timedelta(hours=random.randint(1, 3)))
            all_chat_messages.append({"sender": adapt_person, "content": adapt_msg, "timestamp": format_ts(ex_day + timedelta(hours=random.randint(1, 3))), "sentiment": adapt_sentiment, "serviceInteractionType": adapt_interaction_type, "specialistInvolved": adapt_specialist})
            all_timeline_events.append({
                "type": "message", "sender": adapt_person, "timestamp": format_ts(ex_day + timedelta(hours=random.randint(1, 3))),
                "content": adapt_msg, "pillar": adapt_pillar, "relatedTo": "Adaptation",
                "decisionRationale": adapt_rationale, "healthMetricsSnapshot": adapt_metrics,
                "interventionEffect": adapt_effect, "monetaryFactor": adapt_monetary,
                "timeEfficiency": adapt_time, "serviceInteractionType": adapt_interaction_type,
                "specialistInvolved": adapt_specialist, "nextSteps": adapt_next_steps, "sentiment": adapt_sentiment
            })
            # Simulate slight negative metric impact from deviation
            sim_state["metrics"]["HRV"] = max(30, sim_state["metrics"]["HRV"] - random.randint(0, 3))
            sim_state["metrics"]["RecoveryScore"] = max(10, sim_state["metrics"]["RecoveryScore"] - random.randint(3, 8))

    # Member-Initiated Queries (up to 5 per week on average)
    num_member_convs = poisson_int(AVERAGE_MEMBER_CONVS_PER_WEEK)
    num_member_convs = max(1, min(num_member_convs, 5)) # Clamp between 1 and 5
    
    for i in range(num_member_convs):
        day_offset = random.randint(0, 6)
        time_offset_hours = random.choice([8, 10, 12, 14, 16]) # Business hours
        event_time = current_week_start_date + timedelta(days=day_offset, hours=time_offset_hours, minutes=random.randint(0,59))

        # Generate Rohan message
        # Select a topic, prioritizing those not recently asked
        possible_query_keys = [k for k in ROHAN_QUERY_POOL.keys() if k not in recently_asked_topic_keys]
        if not possible_query_keys:
            # If all topics are in cool-down, Rohan asks a general query
            chosen_topic = "general_query"
        else:
            chosen_topic = random.choice(possible_query_keys)
        
        # Add the chosen query's *topic* and current timestamp to memory
        ROHAN_ASKED_TOPICS_MEMORY.append((chosen_topic, current_week_start_date)) # Store datetime object

        # Select a specific question for that topic, avoiding recent exact duplicates
        recent_user_messages_content = [
            msg['content'].lower() for msg in all_chat_messages[-5:] # Check last 5 messages in ALL chat history
            if msg['sender'] == 'Rohan'
        ]
        available_questions_for_topic = [q for q in ROHAN_QUERY_POOL[chosen_topic] if q.lower() not in recent_user_messages_content]
        if not available_questions_for_topic:
            # If all specific questions for this topic have been used recently, cycle through them
            rohan_query = random.choice(ROHAN_QUERY_POOL[chosen_topic])
        else:
            rohan_query = random.choice(available_questions_for_topic)
        
        rohan_msg, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist, rohan_next_steps, rohan_sentiment = generate_llm_response("Rohan", rohan_query, sim_state["metrics"], all_chat_messages, all_timeline_events, current_sim_date=event_time)
        
        # Add Rohan's message to the full chat history
        all_chat_messages.append({"sender": "Rohan", "content": rohan_msg, "timestamp": format_ts(event_time), "sentiment": rohan_sentiment, "serviceInteractionType": rohan_interaction_type, "specialistInvolved": rohan_specialist})
        
        # Decide which specialist responds
        responder = None
        if any(k in rohan_query.lower() for k in ["apo", "apob", "cholesterol", "lipid"]):
            responder = "Dr. Warren"
        elif any(k in rohan_query.lower() for k in ["travel", "jet", "flight", "london", "ny", "seoul", "tokyo"]):
            responder = random.choice(["Advik", "Ruby"])
        elif any(k in rohan_query.lower() for k in ["back pain", "back", "low back", "stiff", "mobility"]):
            responder = "Rachel"
        elif any(k in rohan_query.lower() for k in ["food", "oatmeal", "fiber", "sushi", "legumes", "nm n", "nmn", "nr", "supplement", "digestion", "hydration"]):
            responder = "Carla"
        elif any(k in rohan_query.lower() for k in ["whoop", "garmin", "hrv", "recovery", "sleep", "sleep apnea"]):
            responder = random.choice(["Advik", "Dr. Warren"])
        elif any(k in rohan_query.lower() for k in ["stress", "cognition", "focus", "meditation", "piano"]):
            responder = random.choice(["Neel", "Advik", "Dr. Evans"]) # Dr. Evans is an implicit persona
        elif any(k in rohan_query.lower() for k in ["diagnostic", "panel", "test", "scan", "mri", "dexa", "vo2"]):
            responder = "Ruby"
        elif any(k in rohan_query.lower() for k in ["monetary", "cost", "expensive", "budget", "roi"]):
            responder = random.choice(["Neel", "Ruby"])
        elif any(k in rohan_query.lower() for k in ["time", "busy", "quick", "efficient", "schedule"]):
            responder = random.choice(["Neel", "Ruby"])
        else: # General query, random Elyx team member responds
            responder = random.choice(list(ELYX_TEAM_PERSONAS.keys()))

        # Tone handling: if angry or frustrated, route to Neel or Neel+Ruby occasionally
        if rohan_sentiment in ["angry", "sad"] and random.random() < 0.4:
            responder = "Neel" if random.random() < 0.7 else "Ruby"

        # Generate Elyx team's response
        team_reply_msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team, team_sentiment = generate_llm_response(responder, rohan_query, sim_state["metrics"], all_chat_messages, all_timeline_events, current_sim_date=event_time + timedelta(hours=random.randint(1, 3)))
        
        # Add Elyx team's message to the full chat history
        all_chat_messages.append({"sender": responder, "content": team_reply_msg, "timestamp": format_ts(event_time + timedelta(hours=random.randint(1, 3))), "sentiment": team_sentiment, "serviceInteractionType": interaction_type, "specialistInvolved": specialist})

        # Decide if this message pair is significant enough for the timeline
        # A query/response pair is significant if it's about a major topic or involves a decision/advice
        is_significant_for_timeline = False
        if chosen_topic in ["apo_b", "illness", "diagnostic_panel", "travel", "piano", "strength_program", "movement_assessment"]:
            is_significant_for_timeline = True
        elif rationale or (effect and effect != "None"): # If there's a specific rationale or effect
            is_significant_for_timeline = True
        elif any(phrase in team_reply_msg.lower() for phrase in ["recommend", "suggest", "protocol", "plan change", "critical", "significant improvement", "elevated", "next steps", "strategy"]):
            is_significant_for_timeline = True
        
        if is_significant_for_timeline:
            all_timeline_events.append({
                "type": "message", "sender": "Rohan", "timestamp": format_ts(event_time),
                "content": rohan_msg, "pillar": rohan_pillar, "relatedTo": chosen_topic,
                "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                "timeEfficiency": rohan_time, "serviceInteractionType": rohan_interaction_type,
                "specialistInvolved": rohan_specialist, "nextSteps": rohan_next_steps, "sentiment": rohan_sentiment
            })
            all_timeline_events.append({
                "type": "message", "sender": responder, "timestamp": format_ts(event_time + timedelta(hours=random.randint(1, 3))),
                "content": team_reply_msg, "pillar": pillar, "relatedTo": chosen_topic,
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                "specialistInvolved": specialist, "nextSteps": next_steps_team, "sentiment": team_sentiment
            })
        
        # Simulate metric changes based on interactions
        if chosen_topic in ["stress", "sleep"]:
            sim_state["metrics"]["HRV"] += random.randint(-4, 4)
            sim_state["metrics"]["DeepSleep"] += random.randint(-10, 10)
        if chosen_topic in ["exercise", "strength_program"]:
            sim_state["metrics"]["RecoveryScore"] += random.randint(-4, 6)
        if chosen_topic in ["apo_b", "nutrition"]:
            sim_state["metrics"]["GlucoseAvg"] = random.randint(90, 105)


    # Simulate specific events/concerns over time (these will always be added to timeline)
    if week_index == 5: # Simulate initial back pain flare-up
        msg_context = "suggest couch stretch for back pain"
        msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team, team_sentiment = generate_llm_response("Rachel", msg_context, sim_state["metrics"], all_chat_messages, all_timeline_events, current_sim_date=current_week_start_date)
        all_chat_messages.append({"sender": "Rachel", "content": msg, "timestamp": format_ts(current_week_start_date), "sentiment": team_sentiment, "serviceInteractionType": interaction_type, "specialistInvolved": specialist})
        all_timeline_events.append({
            "type": "message", "sender": "Rachel", "timestamp": format_ts(current_week_start_date),
            "content": msg, "pillar": pillar, "relatedTo": "Back pain",
            "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
            "interventionEffect": effect, "monetaryFactor": monetary,
            "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
            "specialistInvolved": specialist, "nextSteps": next_steps_team, "sentiment": team_sentiment
        })
        all_timeline_events.append({
            "type": "event", "eventId": "back_pain_intervention", "timestamp": format_ts(current_week_start_date),
            "description": "Back pain intervention (couch stretch)", "details": "Addressing Rohan's reported lower back pain with targeted mobility.",
            "decisionRationale": rationale, "healthMetricsSnapshot": sim_state["metrics"].copy(),
            "interventionEffect": "Initial relief, focus on long-term mobility.",
            "monetaryFactor": "No direct cost, time-efficient.", "timeEfficiency": "2-minute routine.",
            "serviceInteractionType": "intervention_event", "specialistInvolved": "Rachel",
            "nextSteps": "Perform couch stretch daily and report back on effectiveness."
        })
        sim_state["metrics"]["BackPain"] = "mild" # Simulate slight improvement

    if week_index == 10: # Simulate a major illness setback
        msg_context = "initiate sick day protocol due to viral infection"
        msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team, team_sentiment = generate_llm_response("Dr. Warren", msg_context, sim_state["metrics"], all_chat_messages, all_timeline_events, current_sim_date=current_week_start_date)
        all_chat_messages.append({"sender": "Dr. Warren", "content": msg, "timestamp": format_ts(current_week_start_date), "sentiment": team_sentiment, "serviceInteractionType": interaction_type, "specialistInvolved": specialist})
        all_timeline_events.append({
            "type": "message", "sender": "Dr. Warren", "timestamp": format_ts(current_week_start_date),
            "content": msg, "pillar": pillar, "relatedTo": "Illness",
            "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
            "interventionEffect": effect, "monetaryFactor": monetary,
            "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
            "specialistInvolved": specialist, "nextSteps": next_steps_team, "sentiment": team_sentiment
        })
        all_timeline_events.append({
            "type": "event", "eventId": "illness_setback", "timestamp": format_ts(current_week_start_date),
            "description": "Major Illness Setback (Viral Infection)", "details": "Elyx Sick Day Protocol initiated, board meeting postponed.",
            "decisionRationale": rationale, "healthMetricsSnapshot": sim_state["metrics"].copy(),
            "interventionEffect": "Severe fatigue, recovery score dropped significantly.",
            "monetaryFactor": "Potential business cost due to postponed meeting, but avoids higher future medical costs.",
            "timeEfficiency": "Focus on radical rest, minimal time for other activities.",
            "serviceInteractionType": "health_crisis_event", "specialistInvolved": "Dr. Warren, Ruby",
            "nextSteps": "Engage Elyx Sick Day Protocol: rest, hydration, Ruby will reschedule meetings."
        })
        sim_state["metrics"]["RecoveryScore"] = 10 # Simulate very low recovery
        sim_state["metrics"]["POTS_symptoms"] = "severe" # Worsen POTS

    if week_index == 15: # Simulate a new health investment (piano)
        msg_context = "add weekly piano practice as trackable goal"
        msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team, team_sentiment = generate_llm_response("Neel", msg_context, sim_state["metrics"], all_chat_messages, all_timeline_events, current_sim_date=current_week_start_date)
        all_chat_messages.append({"sender": "Neel", "content": msg, "timestamp": format_ts(current_week_start_date), "sentiment": team_sentiment, "serviceInteractionType": interaction_type, "specialistInvolved": specialist})
        all_timeline_events.append({
            "type": "message", "sender": "Neel", "timestamp": format_ts(current_week_start_date),
            "content": msg, "pillar": pillar, "relatedTo": "New Goal",
            "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
            "interventionEffect": effect, "monetaryFactor": monetary,
            "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
            "specialistInvolved": specialist, "nextSteps": next_steps_team, "sentiment": team_sentiment
        })
        all_timeline_events.append({
            "type": "event", "eventId": "piano_goal_added", "timestamp": format_ts(current_week_start_date),
            "description": "Weekly Piano Practice Added to Plan", "details": "Cognitive longevity and stress management investment.",
            "decisionRationale": rationale, "healthMetricsSnapshot": sim_state["metrics"].copy(),
            "interventionEffect": "Expected long-term cognitive and stress resilience benefits.",
            "monetaryFactor": "Initial cost of piano/lessons, long-term non-monetary benefit.",
            "timeEfficiency": "Integrated into weekly routine, flexible scheduling.",
            "serviceInteractionType": "goal_setting_event", "specialistInvolved": "Neel",
            "nextSteps": "Begin weekly piano practice; track subjective focus and HRV."
        })
    
    # Simulate general metric fluctuations
    sim_state["metrics"]["HRV"] = max(30, sim_state["metrics"]["HRV"] + random.randint(-5, 7)) 
    sim_state["metrics"]["RestingHR"] = max(50, sim_state["metrics"]["RestingHR"] + random.randint(-2, 2))
    sim_state["metrics"]["GlucoseAvg"] = random.randint(90, 105) 
    sim_state["metrics"]["RecoveryScore"] = max(20, min(95, sim_state["metrics"]["RecoveryScore"] + random.randint(-8, 10))) 
    sim_state["metrics"]["DeepSleep"] = max(30, min(120, sim_state["metrics"]["DeepSleep"] + random.randint(-15, 20))) 
    
    # More dynamic POTS/BackPain status changes
    if sim_state["metrics"]["POTS_symptoms"] == "severe" and random.random() < 0.4: 
        sim_state["metrics"]["POTS_symptoms"] = "moderate"
    elif sim_state["metrics"]["POTS_symptoms"] == "moderate" and random.random() < 0.4:
        sim_state["metrics"]["POTS_symptoms"] = "mild"
    elif sim_state["metrics"]["POTS_symptoms"] == "mild" and random.random() < 0.1: 
         sim_state["metrics"]["POTS_symptoms"] = random.choice(["moderate", "severe"])
    
    if sim_state["metrics"]["BackPain"] == "severe" and random.random() < 0.4: 
        sim_state["metrics"]["BackPain"] = "moderate"
    elif sim_state["metrics"]["BackPain"] == "moderate" and random.random() < 0.4:
        sim_state["metrics"]["BackPain"] = "mild"
    elif sim_state["metrics"]["BackPain"] == "mild" and random.random() < 0.1: 
        sim_state["metrics"]["BackPain"] = random.choice(["moderate", "severe"])

    # Return both lists in a single JSON object
    return jsonify({"timeline_events": all_timeline_events, "chat_messages": all_chat_messages})

# -------------------------
# Explain decision endpoint
# -------------------------
@app.route('/api/explain-decision', methods=['POST'])
def api_explain_decision():
    data = request.json or {}
    query = (data.get('query') or "").strip()
    journey_data_context = data.get('journeyData', []) # This is actually the timeline_events from frontend
    
    if not query:
        return jsonify({"error": "Query is required."}), 400
    
    relevant_item = None
    query_lower = query.lower()
    
    searchable_items = [item for item in journey_data_context if 'decisionRationale' in item and item['decisionRationale']]
    
    for item in reversed(searchable_items): 
        content_to_search = item.get('content', '') + ' ' + item.get('description', '') + ' ' + item.get('details', '') + ' ' + item.get('decisionRationale', '')
        if query_lower in content_to_search.lower():
            relevant_item = item
            break 

    explanation_text = "I'm sorry, I couldn't find a specific decision matching your query in your journey history. Please try rephrasing or asking about a specific intervention."
    rationale = None
    pillar = None
    metrics_snap = None
    effect = None
    monetary = None
    time_eff = None
    specialist = None
    next_steps = None 
    sentiment = "neutral" # Default sentiment for explanation

    if relevant_item:
        explanation_text = relevant_item.get('content') or relevant_item.get('description') or relevant_item.get('details')
        rationale = relevant_item.get('decisionRationale')
        pillar = relevant_item.get('pillar')
        metrics_snap = relevant_item.get('healthMetricsSnapshot')
        effect = relevant_item.get('interventionEffect')
        monetary = relevant_item.get('monetaryFactor')
        time_eff = relevant_item.get('timeEfficiency')
        specialist = relevant_item.get('specialistInvolved')
        next_steps = relevant_item.get('nextSteps') 
        sentiment = relevant_item.get('sentiment', 'neutral') # Get sentiment from the found item
    else:
        # Fallback to general keyword responses if no specific journey item is found
        # This part will now also return sentiment
        explanation_text, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps, sentiment = generate_llm_response(
            role="Elyx AI Concierge",
            prompt_context=query,
            current_metrics=CURRENT_HEALTH_METRICS, # Use current global metrics as context
            chat_history=[], # Not relevant for this direct explanation
            journey_data_so_far=[] # Not relevant for this direct explanation
        )
    
    # Build the formatted explanation string
    final_text = f"{empathetic_prefix}{explanation_text}\n\n" # Use empathetic prefix here
    if rationale:
        final_text += f"**Rationale:** {rationale}\n"
    if pillar:
        final_text += f"**Pillar Impact:** {pillar}\n"
    if effect:
        final_text += f"**Observed Effect:** {effect}\n"
    if monetary:
        final_text += f"**Monetary Factor:** {monetary}\n"
    if time_eff:
        final_text += f"**Time Efficiency:** {time_eff}\n"
    if specialist:
        final_text += f"**Specialist Involved:** {specialist}\n"
    if next_steps: 
        final_text += f"**Following Steps:** {next_steps}\n"
    if metrics_snap:
        try:
            metrics_json = json.dumps(metrics_snap, indent=2)
        except Exception:
            metrics_json = str(metrics_snap)
        final_text += f"**Metrics at Time:** {metrics_json}\n"

    return jsonify({
        "explanation": final_text,
        "sentiment": sentiment
    })


# -------------------------
# Health-knowledge expand endpoint (small helper)
# -------------------------
@app.route('/api/knowledge-base', methods=['GET'])
def api_knowledge_base():
    """
    Return the Elyx knowledge base (expanded) for the frontend to reference.
    """
    return jsonify(ELYX_KNOWLEDGE_BASE)

# -------------------------
# Run
# -------------------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    debug_flag = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host='0.0.0.0', port=port, debug=debug_flag)
