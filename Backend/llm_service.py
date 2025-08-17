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
        "I've been feeling more headaches lately. Could they be migraines? What should I track?",
        "What's the overall strategy for my ApoB? I need something actionable and realistic, considering my time.",
        "I have only a 36-hour window next week — can we front-load labs & scans efficiently?",
        "The travel workout was manageable; I did 3/4 of it. Any adjustments or ways to make it more impactful?",
        "My son has a cold. What's the best way to avoid catching it during a heavy work week, without disrupting my routine?",
        "I only have short windows each day — what's a minimal, high-impact routine for fitness?",
        "Can we push my strength session earlier, mornings work better now. Will this impact my recovery?",
        "I felt dizzy on standing this morning. Not severe but noticeable. Is this related to my POTS?",
        "I'm low on fiber while traveling. What's the minimum effective approach for nutrition on the go?",
        "Can Sarah coordinate the water quality test and VO2 slot? What's the value of these tests?",
        "I've been getting worse jet lag than before. Any tweaks to the protocol to improve efficiency?",
        "Can we make my exercise plan more aggressive for the next two weeks? What are the risks?",
        "My deep sleep was low last night—any quick tips to improve it immediately?",
        "I want to try time-restricted eating; what's a safe protocol that fits my busy schedule?",
        "I tried oatmeal and it spiked my glucose — what's the right way to incorporate it or alternatives?",
        "I noticed a rash under the Whoop strap. Is this common, and what's the solution?",
        "Can we do a DEXA and VO2 max next month? How will this data directly inform my plan?",
        "Is a full-body MRI worth it for longevity screening, considering the cost and time commitment?",
        "How do I adjust nutrition when eating out in the US, especially for ApoB management?",
        "Would short meditation blocks really help focus and recovery, given my tight schedule?",
        "My HR zones look wrong on Garmin, can Advik review? How will this optimize my training?",
        "I feel like the plan is ad-hoc — I want a coordinated approach. What's the overarching strategy?",
        "If I add NMN or NR supplements, is it likely to help, and what's the scientific basis?",
        "I'm curious about the latest research on cognitive longevity. Any insights?",
        "What are some innovative approaches to managing high-stress periods effectively?",
        "How can I ensure my hydration is optimal, especially with frequent travel?",
        "What are the most impactful changes I can make to my diet for overall vitality, beyond ApoB?"
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
    Returns one of: 'angry', 'sad', 'curious', 'nonchalant', 'positive', 'neutral',
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
    if any(k in t for k in ["acknowledged", "understood", "okay", "noted", "confirm"]):
        return "neutral"
    
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
# Core Generator Logic
# -------------------------
def generate_week_events(week_index, current_date, state):
    """
    Generate events for a given week.
    state: dict with evolving simulation state (metrics, adherence, travel flag, next_diag_week etc.)
    Returns list of event dicts for that week.
    """
    events = []
    
    # Update Rohan's memory: remove topics older than MEMORY_RETENTION_WEEKS
    global ROHAN_ASKED_TOPICS_MEMORY
    ROHAN_ASKED_TOPICS_MEMORY = [
        (topic, ts) for topic, ts in ROHAN_ASKED_TOPICS_MEMORY
        if (current_date - ts).days / 7 < MEMORY_RETENTION_WEEKS
    ]
    recently_asked_topic_keys = {topic for topic, _ in ROHAN_ASKED_TOPICS_MEMORY}


    # Travel scheduling: if this week is a travel week (1 out of TRAVEL_EVERY_N_WEEKS)
    travel_week = ((week_index - 1) % TRAVEL_EVERY_N_WEEKS) == 0
    # Occasionally skip travel to create variation (Rohan's schedule is dynamic)
    if travel_week and random.random() < 0.15:
        travel_week = False

    if travel_week:
        state["in_travel"] = True
        travel_start = current_date + timedelta(days=random.randint(0, 2)) # Travel can start any day early in week
        travel_end = travel_start + timedelta(days=6)
        
        # Pre-travel protocol message (Advik)
        advik_msg, advik_rationale, advik_pillar, advik_metrics, advik_effect, advik_monetary, advik_time, advik_interaction_type, advik_specialist, advik_next_steps, advik_sentiment = generate_llm_response("Advik", "prepare travel protocol for upcoming trip.", state["metrics"], [], [], current_sim_date=travel_start)
        events.append({
            "type": "message", "sender": "Advik", "timestamp": format_ts(travel_start),
            "content": advik_msg, "pillar": advik_pillar, "relatedTo": "Travel",
            "decisionRationale": advik_rationale, "healthMetricsSnapshot": advik_metrics,
            "interventionEffect": advik_effect, "monetaryFactor": advik_monetary,
            "timeEfficiency": advik_time, "serviceInteractionType": advik_interaction_type,
            "specialistInvolved": advik_specialist, "nextSteps": advik_next_steps, "sentiment": advik_sentiment
        })

        # Travel logistics message (Ruby)
        ruby_msg, ruby_rationale, ruby_pillar, ruby_metrics, ruby_effect, ruby_monetary, ruby_time, ruby_interaction_type, ruby_specialist, ruby_next_steps, ruby_sentiment = generate_llm_response("Ruby", "confirm travel logistics for upcoming trip.", state["metrics"], [], [], current_sim_date=travel_start)
        events.append({
            "type": "message", "sender": "Ruby", "timestamp": format_ts(travel_start + timedelta(minutes=10)),
            "content": ruby_msg, "pillar": ruby_pillar, "relatedTo": "Travel",
            "decisionRationale": ruby_rationale, "healthMetricsSnapshot": ruby_metrics,
            "interventionEffect": ruby_effect, "monetaryFactor": ruby_monetary,
            "timeEfficiency": ruby_time, "serviceInteractionType": ruby_interaction_type,
            "specialistInvolved": ruby_specialist, "nextSteps": ruby_next_steps, "sentiment": ruby_sentiment
        })
        
        # Travel event
        events.append({
            "type": "event", "eventId": f"travel_start_week_{week_index}", "timestamp": format_ts(travel_start),
            "description": f"Rohan travels for business (Week {week_index})", "details": "Jet lag protocol, in-flight mobility, nutrition adjustments.",
            "decisionRationale": "Proactive mitigation of travel stress on health goals, maximizing performance during demanding trips.",
            "healthMetricsSnapshot": state["metrics"].copy(), "interventionEffect": "Potential for jet lag/fatigue.",
            "monetaryFactor": "Business travel cost, focus on health investment ROI.", "timeEfficiency": "Optimized for busy travel schedule.",
            "serviceInteractionType": "travel_event", "specialistInvolved": "Advik, Ruby",
            "nextSteps": "Follow travel protocol; Advik to monitor recovery post-trip."
        })
        
        # Simulate negative metric impact from travel
        state["metrics"]["HRV"] = max(30, state["metrics"]["HRV"] - random.randint(0, 8))
        state["metrics"]["RecoveryScore"] = max(10, state["metrics"]["RecoveryScore"] - random.randint(10, 25))
        state["metrics"]["DeepSleep"] = max(30, state["metrics"]["DeepSleep"] - random.randint(0, 20))

    else: # If not a travel week, check for post-travel recovery
        if state.get("in_travel"): # Just finished a travel week
            state["in_travel"] = False
            post_travel_date = current_date + timedelta(days=random.randint(0, 2))
            advik_msg, advik_rationale, advik_pillar, advik_metrics, advik_effect, advik_monetary, advik_time, advik_interaction_type, advik_specialist, advik_next_steps, advik_sentiment = generate_llm_response("Advik", "post-travel recovery check-in.", state["metrics"], [], [], current_sim_date=post_travel_date)
            events.append({
                "type": "message", "sender": "Advik", "timestamp": format_ts(post_travel_date),
                "content": advik_msg, "pillar": advik_pillar, "relatedTo": "Post-travel recovery",
                "decisionRationale": advik_rationale, "healthMetricsSnapshot": advik_metrics,
                "interventionEffect": advik_effect, "monetaryFactor": advik_monetary,
                "timeEfficiency": advik_time, "serviceInteractionType": advik_interaction_type,
                "specialistInvolved": advik_specialist, "nextSteps": advik_next_steps, "sentiment": advik_sentiment
            })
            events.append({
                "type": "event", "eventId": f"travel_end_week_{week_index}", "timestamp": format_ts(post_travel_date),
                "description": "Post-travel Recovery Check-in", "details": "Monitoring re-adaptation after business travel.",
                "decisionRationale": "Essential to mitigate accumulated travel stress and ensure quick return to baseline.",
                "healthMetricsSnapshot": state["metrics"].copy(), "interventionEffect": "Monitoring recovery from travel.",
                "monetaryFactor": None, "timeEfficiency": None, "serviceInteractionType": "post_travel_event",
                "specialistInvolved": "Advik", "nextSteps": "Continue recovery protocol."
            })


    # Diagnostic scheduling: if week is multiple of DIAGNOSTIC_EVERY_WEEKS
    if (week_index - 1) % DIAGNOSTIC_EVERY_WEEKS == 0:
        diag_day = current_date + timedelta(days=random.randint(1, 3))
        ruby_msg, ruby_rationale, ruby_pillar, ruby_metrics, ruby_effect, ruby_monetary, ruby_time, ruby_interaction_type, ruby_specialist, ruby_next_steps, ruby_sentiment = generate_llm_response("Ruby", "schedule Q1/Q2/Q3 diagnostic panel", state["metrics"], [], [], current_sim_date=diag_day)
        events.append({
            "type": "message", "sender": "Ruby", "timestamp": format_ts(diag_day),
            "content": ruby_msg, "pillar": ruby_pillar, "relatedTo": "Program requirement",
            "decisionRationale": ruby_rationale, "healthMetricsSnapshot": ruby_metrics,
            "interventionEffect": ruby_effect, "monetaryFactor": ruby_monetary,
            "timeEfficiency": ruby_time, "serviceInteractionType": ruby_interaction_type,
            "specialistInvolved": ruby_specialist, "nextSteps": ruby_next_steps, "sentiment": ruby_sentiment
        })
        events.append({
            "type": "event", "eventId": f"diagnostic_scheduled_week_{week_index}", "timestamp": format_ts(diag_day),
            "description": f"Quarterly Diagnostic Panel Scheduled (Week {week_index})",
            "details": "Comprehensive baseline tests for metabolic and hormonal health.",
            "decisionRationale": ruby_rationale, "healthMetricsSnapshot": state["metrics"].copy(),
            "interventionEffect": None, "monetaryFactor": ruby_monetary, "timeEfficiency": ruby_time,
            "serviceInteractionType": "diagnostic_scheduling_event",
            "specialistInvolved": "Ruby", "nextSteps": ruby_next_steps
        })
        state["last_diag_week"] = week_index

        # Simulate results discussion a week later
        results_date = diag_day + timedelta(days=7)
        
        # Simulate metric changes for diagnostic results
        if week_index == 12: # Q1 results
            state["metrics"]["ApoB"] = 105 # Still elevated
            state["metrics"]["HRV"] = 48 # Slight increase
            state["metrics"]["POTS_symptoms"] = "moderate"
            state["metrics"]["BackPain"] = "mild"
            
            dr_msg, dr_rationale, dr_pillar, dr_metrics, dr_effect, dr_monetary, dr_time, dr_interaction_type, dr_specialist, dr_next_steps, dr_sentiment = generate_llm_response("Dr. Warren", f"discuss Q1 diagnostic results, elevated ApoB: {state['metrics']['ApoB']}", state["metrics"], [], [], current_sim_date=results_date)
            events.append({
                "type": "message", "sender": "Dr. Warren", "timestamp": format_ts(results_date),
                "content": dr_msg, "pillar": dr_pillar, "relatedTo": "Q1 Diagnostics",
                "decisionRationale": dr_rationale, "healthMetricsSnapshot": dr_metrics,
                "interventionEffect": dr_effect, "monetaryFactor": dr_monetary,
                "timeEfficiency": dr_time, "serviceInteractionType": dr_interaction_type,
                "specialistInvolved": dr_specialist, "nextSteps": dr_next_steps, "sentiment": dr_sentiment
            })
            events.append({
                "type": "event", "eventId": f"q1_results_week_{week_index}", "timestamp": format_ts(results_date),
                "description": "Q1 Diagnostic Results Reviewed", "details": f"Elevated ApoB ({state['metrics']['ApoB']} mg/dL) identified as primary focus.",
                "decisionRationale": dr_rationale, "healthMetricsSnapshot": state["metrics"].copy(),
                "interventionEffect": dr_effect, "monetaryFactor": dr_monetary, "timeEfficiency": dr_time,
                "serviceInteractionType": "diagnostic_review_event", "specialistInvolved": "Dr. Warren",
                "nextSteps": dr_next_steps
            })

        elif week_index == 24: # Q2 results
            # Simulate significant improvement due to interventions
            state["metrics"]["ApoB"] = random.randint(70, 85)
            state["metrics"]["HRV"] = random.randint(55, 70)
            state["metrics"]["POTS_symptoms"] = "mild"
            state["metrics"]["BackPain"] = "none"
            
            dr_msg, dr_rationale, dr_pillar, dr_metrics, dr_effect, dr_monetary, dr_time, dr_interaction_type, dr_specialist, dr_next_steps, dr_sentiment = generate_llm_response("Dr. Warren", f"discuss Q2 diagnostic results, improved ApoB: {state['metrics']['ApoB']}", state["metrics"], [], [], current_sim_date=results_date)
            events.append({
                "type": "message", "sender": "Dr. Warren", "timestamp": format_ts(results_date),
                "content": dr_msg, "pillar": dr_pillar, "relatedTo": "Q2 Diagnostics",
                "decisionRationale": dr_rationale, "healthMetricsSnapshot": dr_metrics,
                "interventionEffect": dr_effect, "monetaryFactor": dr_monetary,
                "timeEfficiency": dr_time, "serviceInteractionType": dr_interaction_type,
                "specialistInvolved": dr_specialist, "nextSteps": dr_next_steps, "sentiment": dr_sentiment
            })
            events.append({
                "type": "event", "eventId": f"q2_results_week_{week_index}", "timestamp": format_ts(results_date),
                "description": "Q2 Diagnostic Results Reviewed", "details": f"Improved ApoB ({state['metrics']['ApoB']} mg/dL) due to interventions.",
                "decisionRationale": dr_rationale, "healthMetricsSnapshot": state["metrics"].copy(),
                "interventionEffect": dr_effect, "monetaryFactor": dr_monetary, "timeEfficiency": dr_time,
                "serviceInteractionType": "diagnostic_review_event", "specialistInvolved": "Dr. Warren",
                "nextSteps": dr_next_steps
            })

    # Exercise updates every EXERCISE_UPDATE_EVERY_WEEKS
    if (week_index - 1) % EXERCISE_UPDATE_EVERY_WEEKS == 0:
        ex_day = current_date + timedelta(days=random.randint(1, 4))
        
        # Simulate Rohan's adherence (50% adherence)
        if random.random() < PLAN_ADHERENCE_PROB: # Rohan adheres
            rohan_adherence_msg, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist, rohan_next_steps, rohan_sentiment = generate_llm_response("Rohan", f"adhere to exercise plan. Current state: {state['metrics']}", state["metrics"], [], [], current_sim_date=ex_day)
            events.append({
                "type": "message", "sender": "Rohan", "timestamp": format_ts(ex_day),
                "content": rohan_adherence_msg, "pillar": rohan_pillar, "relatedTo": "Exercise adherence",
                "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                "timeEfficiency": rohan_time, "serviceInteractionType": "member_adherence_report",
                "specialistInvolved": rohan_specialist, "nextSteps": rohan_next_steps, "sentiment": rohan_sentiment
            })
            # Simulate positive metric changes from adherence
            state["metrics"]["HRV"] = min(90, state["metrics"]["HRV"] + random.randint(1, 5))
            state["metrics"]["RecoveryScore"] = min(95, state["metrics"]["RecoveryScore"] + random.randint(3, 8))
            state["metrics"]["RestingHR"] = max(50, state["metrics"]["RestingHR"] - random.randint(0, 2))

        else: # Rohan deviates
            rohan_deviation_msg, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist, rohan_next_steps, rohan_sentiment = generate_llm_response("Rohan", f"deviate from exercise plan due to travel/time/soreness. Current state: {state['metrics']}", state["metrics"], [], [], current_sim_date=ex_day)
            events.append({
                "type": "message", "sender": "Rohan", "timestamp": format_ts(ex_day),
                "content": rohan_deviation_msg, "pillar": rohan_pillar, "relatedTo": "Exercise deviation",
                "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                "timeEfficiency": rohan_time, "serviceInteractionType": "member_adherence_report",
                "specialistInvolved": rohan_specialist, "nextSteps": rohan_next_steps, "sentiment": rohan_sentiment
            })
            # Elyx team adapts
            adapt_person = random.choice(["Rachel", "Advik"])
            adapt_msg, adapt_rationale, adapt_pillar, adapt_metrics, adapt_effect, adapt_monetary, adapt_time, adapt_interaction_type, adapt_specialist, adapt_next_steps, adapt_sentiment = generate_llm_response(adapt_person, f"adapt to Rohan's exercise deviation. Current state: {state['metrics']}", state["metrics"], [], [], current_sim_date=ex_day)
            events.append({
                "type": "message", "sender": adapt_person, "timestamp": format_ts(ex_day + timedelta(hours=random.randint(1, 3))),
                "content": adapt_msg, "pillar": adapt_pillar, "relatedTo": "Adaptation",
                "decisionRationale": adapt_rationale, "healthMetricsSnapshot": adapt_metrics,
                "interventionEffect": adapt_effect, "monetaryFactor": adapt_monetary,
                "timeEfficiency": adapt_time, "serviceInteractionType": adapt_interaction_type,
                "specialistInvolved": adapt_specialist, "nextSteps": adapt_next_steps, "sentiment": adapt_sentiment
            })
            # Simulate slight negative metric impact from deviation
            state["metrics"]["HRV"] = max(30, state["metrics"]["HRV"] - random.randint(0, 3))
            state["metrics"]["RecoveryScore"] = max(10, state["metrics"]["RecoveryScore"] - random.randint(3, 8))

    # Member initiated conversations for the week (up to 5 per week on average)
    num_member_convs = poisson_int(AVERAGE_MEMBER_CONVS_PER_WEEK)
    num_member_convs = max(1, min(num_member_convs, 5)) # Clamp between 1 and 5
    
    for i in range(num_member_convs):
        day_offset = random.randint(0, 6)
        time_offset_hours = random.choice([8, 10, 12, 14, 16]) # Business hours
        event_time = current_date + timedelta(days=day_offset, hours=time_offset_hours, minutes=random.randint(0,59))

        # Generate Rohan message
        # Select a topic, prioritizing those not recently asked
        possible_query_keys = [k for k in ROHAN_QUERY_POOL.keys() if k not in recently_asked_topic_keys]
        if not possible_query_keys:
            # If all topics are in cool-down, Rohan asks a general query
            chosen_topic = "general_query"
        else:
            chosen_topic = random.choice(possible_query_keys)
        
        # Add the chosen query's *topic* and current timestamp to memory
        ROHAN_ASKED_TOPICS_MEMORY.append((chosen_topic, current_date)) # Store datetime object

        # Select a specific question for that topic, avoiding recent exact duplicates
        recent_user_messages_content = [
            msg['parts'][0]['text'] for msg in chat_history[-5:] # Check last 5 messages
            if msg['role'] == 'user' and 'parts' in msg and len(msg['parts']) > 0 and 'text' in msg['parts'][0]
        ]
        available_questions_for_topic = [q for q in ROHAN_QUERY_POOL[chosen_topic] if q not in recent_user_messages_content]
        if not available_questions_for_topic:
            # If all specific questions for this topic have been used recently, cycle through them
            rohan_query = random.choice(ROHAN_QUERY_POOL[chosen_topic])
        else:
            rohan_query = random.choice(available_questions_for_topic)
        
        rohan_msg, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist, rohan_next_steps, rohan_sentiment = generate_llm_response("Rohan", rohan_query, state["metrics"], chat_history, events, current_sim_date=event_time)
        
        # Add Rohan's message to the full chat history
        chat_history.append({"role": "user", "parts": [{"text": rohan_msg}]})
        
        # Decide which specialist responds
        responder = None
        if "apo b" in rohan_query.lower() or "apob" in rohan_query.lower():
            responder = "Dr. Warren"
        elif "travel" in rohan_query.lower() or "jet lag" in rohan_query.lower():
            responder = "Advik"
        elif "back pain" in rohan_query.lower() or "stretch" in rohan_query.lower():
            responder = "Rachel"
        elif "digestion" in rohan_query.lower() or "food" in rohan_query.lower() or "nutrition" in rohan_query.lower():
            responder = "Carla"
        elif "stress" in rohan_query.lower() or "cognitive" in rohan_query.lower() or "piano" in rohan_query.lower():
            responder = random.choice(["Neel", "Advik", "Dr. Evans"]) # Dr. Evans is an implicit persona
        elif "diagnostic" in rohan_query.lower() or "test" in rohan_query.lower() or "scan" in rohan_query.lower():
            responder = "Ruby"
        elif "monetary" in rohan_query.lower() or "cost" in rohan_query.lower():
            responder = random.choice(["Neel", "Ruby"])
        elif "time" in rohan_query.lower() or "busy" in rohan_query.lower() or "efficient" in rohan_query.lower():
            responder = random.choice(["Neel", "Ruby"])
        else: # General query, random Elyx team member responds
            responder = random.choice(list(ELYX_TEAM_PERSONAS.keys()))

        # Generate Elyx team's response
        team_reply_msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team, team_sentiment = generate_llm_response(responder, rohan_query, state["metrics"], chat_history, events, current_sim_date=event_time)
        
        # Add Elyx team's message to the full chat history
        chat_history.append({"role": "model", "parts": [{"text": team_reply_msg}]})

        # Decide if this message pair is significant enough for the timeline
        is_significant_for_timeline = False
        if any(k in rohan_query.lower() for k in ["apo b", "illness", "diagnostic", "travel", "plan", "goals"]):
            is_significant_for_timeline = True
        elif any(k in team_reply_msg.lower() for k in ["recommend", "suggest", "protocol", "plan change", "critical", "significant improvement", "elevated", "next steps"]):
            is_significant_for_timeline = True
        
        if is_significant_for_timeline:
            events.append({
                "type": "message", "sender": "Rohan", "timestamp": format_ts(event_time),
                "content": rohan_msg, "pillar": rohan_pillar, "relatedTo": chosen_topic,
                "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                "timeEfficiency": rohan_time, "serviceInteractionType": rohan_interaction_type,
                "specialistInvolved": rohan_specialist, "nextSteps": rohan_next_steps, "sentiment": rohan_sentiment
            })
            events.append({
                "type": "message", "sender": responder, "timestamp": format_ts(event_time + timedelta(hours=random.randint(1, 3))),
                "content": team_reply_msg, "pillar": pillar, "relatedTo": chosen_topic,
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                "specialistInvolved": specialist, "nextSteps": next_steps_team, "sentiment": team_sentiment
            })
        
        # Simulate minor metric changes based on interactions
        if "stress" in chosen_topic:
            state["metrics"]["HRV"] += random.randint(-4, 4)
        if "sleep" in chosen_topic:
            state["metrics"]["DeepSleep"] += random.randint(-10, 10)
        if "exercise" in chosen_topic:
            state["metrics"]["RecoveryScore"] += random.randint(-4, 6)


    # Simulate specific events/concerns over time (these will always be added to timeline)
    if week_index == 5: # Simulate initial back pain flare-up
        msg_context = "suggest couch stretch for back pain"
        msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team, team_sentiment = generate_llm_response("Rachel", msg_context, state["metrics"], chat_history, events, current_sim_date=current_date)
        events.append({
            "type": "message", "sender": "Rachel", "timestamp": format_ts(current_date),
            "content": msg, "pillar": pillar, "relatedTo": "Back pain",
            "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
            "interventionEffect": effect, "monetaryFactor": monetary,
            "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
            "specialistInvolved": specialist, "nextSteps": next_steps_team, "sentiment": team_sentiment
        })
        chat_history.append({"role": "model", "parts": [{"text": msg}]})
        events.append({
            "type": "event", "eventId": "back_pain_intervention", "timestamp": format_ts(current_date),
            "description": "Back pain intervention (couch stretch)", "details": "Addressing Rohan's reported lower back pain with targeted mobility.",
            "decisionRationale": rationale, "healthMetricsSnapshot": state["metrics"].copy(),
            "interventionEffect": "Initial relief, focus on long-term mobility.",
            "monetaryFactor": "No direct cost, time-efficient.", "timeEfficiency": "2-minute routine.",
            "serviceInteractionType": "intervention_event", "specialistInvolved": "Rachel",
            "nextSteps": "Perform couch stretch daily and report back on effectiveness."
        })
        state["metrics"]["BackPain"] = "mild" # Simulate slight improvement

    if week_index == 10: # Simulate a major illness setback
        msg_context = "initiate sick day protocol due to viral infection"
        msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team, team_sentiment = generate_llm_response("Dr. Warren", msg_context, state["metrics"], chat_history, events, current_sim_date=current_date)
        events.append({
            "type": "message", "sender": "Dr. Warren", "timestamp": format_ts(current_date),
            "content": msg, "pillar": pillar, "relatedTo": "Illness",
            "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
            "interventionEffect": effect, "monetaryFactor": monetary,
            "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
            "specialistInvolved": specialist, "nextSteps": next_steps_team, "sentiment": team_sentiment
        })
        chat_history.append({"role": "model", "parts": [{"text": msg}]})
        events.append({
            "type": "event", "eventId": "illness_setback", "timestamp": format_ts(current_date),
            "description": "Major Illness Setback (Viral Infection)", "details": "Elyx Sick Day Protocol initiated, board meeting postponed.",
            "decisionRationale": rationale, "healthMetricsSnapshot": state["metrics"].copy(),
            "interventionEffect": "Severe fatigue, recovery score dropped significantly.",
            "monetaryFactor": "Potential business cost due to postponed meeting, but avoids higher future medical costs.",
            "timeEfficiency": "Focus on radical rest, minimal time for other activities.",
            "serviceInteractionType": "health_crisis_event", "specialistInvolved": "Dr. Warren, Ruby",
            "nextSteps": "Engage Elyx Sick Day Protocol: rest, hydration, Ruby will reschedule meetings."
        })
        state["metrics"]["RecoveryScore"] = 10 # Simulate very low recovery
        state["metrics"]["POTS_symptoms"] = "severe" # Worsen POTS

    if week_index == 15: # Simulate a new health investment (piano)
        msg_context = "add weekly piano practice as trackable goal"
        msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team, team_sentiment = generate_llm_response("Neel", msg_context, state["metrics"], chat_history, events, current_sim_date=current_date)
        events.append({
            "type": "message", "sender": "Neel", "timestamp": format_ts(current_date),
            "content": msg, "pillar": pillar, "relatedTo": "New Goal",
            "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
            "interventionEffect": effect, "monetaryFactor": monetary,
            "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
            "specialistInvolved": specialist, "nextSteps": next_steps_team, "sentiment": team_sentiment
        })
        chat_history.append({"role": "model", "parts": [{"text": msg}]})
        events.append({
            "type": "event", "eventId": "piano_goal_added", "timestamp": format_ts(current_date),
            "description": "Weekly Piano Practice Added to Plan", "details": "Cognitive longevity and stress management investment.",
            "decisionRationale": rationale, "healthMetricsSnapshot": state["metrics"].copy(),
            "interventionEffect": "Expected long-term cognitive and stress resilience benefits.",
            "monetaryFactor": "Initial cost of piano/lessons, long-term non-monetary benefit.",
            "timeEfficiency": "Integrated into weekly routine, flexible scheduling.",
            "serviceInteractionType": "goal_setting_event", "specialistInvolved": "Neel",
            "nextSteps": "Begin weekly piano practice; track subjective focus and HRV."
        })
    
    # Simulate general metric fluctuations
    state["metrics"]["HRV"] = max(30, state["metrics"]["HRV"] + random.randint(-5, 7)) 
    state["metrics"]["RestingHR"] = max(50, state["metrics"]["RestingHR"] + random.randint(-2, 2))
    state["metrics"]["GlucoseAvg"] = random.randint(90, 105) 
    state["metrics"]["RecoveryScore"] = max(20, min(95, state["metrics"]["RecoveryScore"] + random.randint(-8, 10))) 
    state["metrics"]["DeepSleep"] = max(30, min(120, state["metrics"]["DeepSleep"] + random.randint(-15, 20))) 
    
    # More dynamic POTS/BackPain status changes
    if state["metrics"]["POTS_symptoms"] == "severe" and random.random() < 0.4: 
        state["metrics"]["POTS_symptoms"] = "moderate"
    elif state["metrics"]["POTS_symptoms"] == "moderate" and random.random() < 0.4:
        state["metrics"]["POTS_symptoms"] = "mild"
    elif state["metrics"]["POTS_symptoms"] == "mild" and random.random() < 0.1: 
         state["metrics"]["POTS_symptoms"] = random.choice(["moderate", "severe"])
    
    if state["metrics"]["BackPain"] == "severe" and random.random() < 0.4: 
        state["metrics"]["BackPain"] = "moderate"
    elif state["metrics"]["BackPain"] == "moderate" and random.random() < 0.4:
        state["metrics"]["BackPain"] = "mild"
    elif state["metrics"]["BackPain"] == "mild" and random.random() < 0.1: 
        state["metrics"]["BackPain"] = random.choice(["moderate", "severe"])

    return events # Return events generated for this week


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
        "description": "Member Onboarding Initiated", "details": f"Rohan's initial concern: '{rohan_msg}' | Ruby's welcome: '{ruby_msg}'",
        "decisionRationale": "Standard Elyx onboarding process to establish baseline and goals for a personalized plan.",
        "healthMetricsSnapshot": sim_state["metrics"].copy(), "interventionEffect": None,
        "monetaryFactor": None, "timeEfficiency": None, "serviceInteractionType": "onboarding_event", 
        "specialistInvolved": "Elyx Team", "nextSteps": "Complete medical record consolidation and initial assessments."
    })


    # Loop through the weeks and generate events
    for week in range(1, WEEKS_TO_GENERATE + 1):
        current_week_start_date = START_DATE + timedelta(weeks=week-1)
        
        # Generate all events and messages for this week
        week_generated_events = [] # Temp list for this week's raw generated items
        
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
                "interventionEffect": None, "monetaryFactor": monetary, "timeEfficiency": time_eff,
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
            msg['parts'][0]['text'] for msg in all_chat_messages[-5:] # Check last 5 messages in ALL chat history
            if msg['sender'] == 'Rohan' and 'parts' in msg and len(msg['parts']) > 0 and 'text' in msg['parts'][0]
        ]
        available_questions_for_topic = [q for q in ROHAN_QUERY_POOL[chosen_topic] if q not in recent_user_messages_content]
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
            responder = random.choice(["Neel", "Advik", "Dr. Evans"])
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


    # Simulate general metric fluctuations (weekly drift)
    sim_state["metrics"]["HRV"] = max(30, sim_state["metrics"]["HRV"] + random.randint(-3, 5))
    sim_state["metrics"]["RestingHR"] = max(50, sim_state["metrics"]["RestingHR"] + random.randint(-1, 1))
    sim_state["metrics"]["GlucoseAvg"] = random.randint(90, 105)
    sim_state["metrics"]["RecoveryScore"] = max(20, min(95, sim_state["metrics"]["RecoveryScore"] + random.randint(-5, 8)))
    sim_state["metrics"]["DeepSleep"] = max(30, min(120, sim_state["metrics"]["DeepSleep"] + random.randint(-10, 15)))
    
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

    # Return only the significant events for the timeline, and all chat messages separately
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

    query_lower = query.lower()

    # Try matching to a journey item first (keyword-based and full-text)
    relevant_item = None
    # Search in timeline_events for direct matches or strong keyword relevance
    for item in reversed(journey_data_context): # Search recent history first
        content_to_search = " ".join([
            str(item.get("content", "")),
            str(item.get("description", "")),
            str(item.get("details", "")),
            str(item.get("decisionRationale", ""))
        ]).lower()
        
        # Direct phrase match
        if query_lower in content_to_search:
            relevant_item = item
            break
        
        # Check for keyword overlap if no direct phrase match
        query_keywords = set(query_lower.split())
        item_keywords = set(content_to_search.split())
        if len(query_keywords.intersection(item_keywords)) >= 2: # At least two common words
             if item.get('decisionRationale'): # Prioritize items with explicit rationale
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
        sentiment = relevant_item.get('sentiment', 'neutral')
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
    final_text = f"{explanation_text}\n\n"
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
