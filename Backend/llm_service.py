# llm_service.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
from datetime import datetime, timedelta
import json
import os
import math

app = Flask(__name__)
CORS(app)

# -------------------------
# Config / Global Settings
# -------------------------
START_DATE = datetime(2025, 8, 1)  # journey start
WEEKS_TO_GENERATE = 34  # ~8 months
DIAGNOSTIC_EVERY_WEEKS = 12  # every 3 months ~12 weeks
EXERCISE_UPDATE_EVERY_WEEKS = 2
TRAVEL_EVERY_N_WEEKS = 4  # travel 1 week out of every 4
AVERAGE_MEMBER_CONVS_PER_WEEK = 5  # average (poisson)
MEMBER_HOURS_PER_WEEK = 5
PLAN_ADHERENCE_PROB = 0.5  # ~50% adherence
MAX_MESSAGES_PER_PERSON = 9999  # safety cap

# Seed for reproducible runs during dev; remove or randomize in production
RANDOM_SEED = os.environ.get("SYNTH_SEED")
if RANDOM_SEED:
    random.seed(int(RANDOM_SEED))
else:
    random.seed(42)


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
    "commitment_hours_per_week": MEMBER_HOURS_PER_WEEK
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
    "sleep apnea": {
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
    }
}

# -------------------------
# Message Pools (expanded)
# -------------------------
# For each persona we create a large pool of unique messages. We'll pop messages to avoid reuse.
def make_pool(prefix, items):
    return [f"{prefix}{text}" for text in items]

# Rohan: member-initiated questions / updates (expanded ~4x)
ROHAN_POOL = make_pool("",
    [
        "Just a quick check-in. The new meal plan from Carla has been helpful, energy is slightly better.",
        "My back pain flared up again after that long flight. What's next?",
        "Heads up — I have a last-minute trip to London next week. Can we get a jet-lag strategy?",
        "I've been feeling more headaches lately. Could they be migraines?",
        "What's the plan for my ApoB? I want something actionable and realistic.",
        "I have only a 36-hour window next week — can we front-load labs & scans?",
        "The travel workout was manageable; I did 3/4 of it. Any adjustments?",
        "My son has a cold. Best way to avoid catching it during a heavy week?",
        "I only have short windows each day — what's a minimal high-impact routine?",
        "Can we push my strength session earlier, mornings work better now.",
        "I felt dizzy on standing this morning. Not severe but noticeable.",
        "I'm low on fiber while traveling. What's the minimum effective approach?",
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
        "Thanks for the update — I'm coordinating with the team and will confirm times by EOD.",
        "I can arrange a phlebotomist at your office next week; which morning works?",
        "Got it. I've flagged this as Priority 1 for Dr. Warren to review immediately.",
        "I've scheduled the VO2 slot and emailed Javier to coordinate meals.",
        "Reservation confirmed and added to your calendar. Want me to arrange transport?",
        "I'll loop Sarah in and handle the logistics so you don't have to worry.",
        "Understood. I'll put a travel-ready meal plan together with Carla.",
        "I'll overnight a breathable strap for your Whoop. Please switch wrists in the meantime.",
        "We received the records from Dr. Tan's clinic — thank you for the patience.",
        "I've scheduled Advik for a morning consult — options at 07:30 or 08:30, which do you prefer?",
        "I will coordinate the Prenuvo MRI and send you options for late September.",
        "We can have a phlebotomist come to your office at 08:30; fasting instructions sent.",
        "I'm arranging meal delivery and electrolyte beverages under the Sick Day Protocol.",
        "I'll handle the environmental lab for water testing next Thursday.",
        "Noted. I'll confirm with Rachel the hotel-friendly workout plan and share it tonight.",
        "I'll coordinate with your cook Javier by email to align evening meals to the plan.",
        "I'll set a reminder for your 3-month diagnostic panel and coordinate the lab."
    ]
)

# Dr. Warren: medical strategist
DRWARREN_POOL = make_pool("Dr. Warren: ",
    [
        "I've reviewed your records. Elevated ApoB at 110 mg/dL is an important target for risk reduction.",
        "We'll interpret results in context and avoid knee-jerk medication choices unless clinically required.",
        "ApoB is a key marker—we'll prioritize dietary and exercise changes and re-test in 3 months.",
        "For dizziness on standing, let's consolidate past autonomic tests and consider orthostatic vitals.",
        "Before starting any complex supplement like NMN/NR, let's look at your metabolic panel first.",
        "Add a home BP log and re-run the lipid panel; we will make medication choices if lifestyle fails.",
        "Cognitive dips often mirror sleep deficits and glucose variability — try 90-min focus blocks + 10-min reset.",
        "Given your symptoms, upgrading to higher-resolution telemetry (Whoop) is sensible.",
        "If recovery stays poor after 12 weeks, we may escalate diagnostics (tilt table / autonomic clinic).",
        "We will document plan rationale and set a re-check in 8–12 weeks to review progress."
    ]
)

# Advik: performance scientist
ADVIK_POOL = make_pool("Advik: ",
    [
        "Small changes to sleep timing and light exposure can shift circadian rhythm quickly when traveling.",
        "Let's try a compressed light-exposure protocol for your upcoming flight — I'll send times.",
        "HRV dips could be due to fragmented sleep; let's test a 10-day experiment on sleep timing.",
        "For last-minute travel: morning light, avoid naps >20min on day 1, and time caffeine after first light.",
        "Your Whoop shows good responsiveness — let's increase Zone 2 minutes by 10% over 2 weeks.",
        "We can replace one cardio day with a short Zone 5 interval once per week to boost VO2 max.",
        "I see a pattern — deep sleep dips after late-afternoon Zoom calls; try blue-light blocking glasses after 4 PM.",
        "We'll monitor objective signals after each experiment to check signal validity.",
        "If your HR zones are miscalibrated, we'll do a metabolic step test to individualize training zones."
    ]
)

# Carla: nutritionist
CARLA_POOL = make_pool("Carla: ",
    [
        "For ApoB focus, prioritize soluble fiber, reduce saturated fats, and increase oily fish or plant sterols.",
        "Try adding psyllium to a morning smoothie for soluble fiber — let me know how it goes.",
        "When traveling, pick a vegetable or fruit at every meal — simple, high-impact rule.",
        "Sushi can spike glucose; pair rice with protein and fat to blunt the curve.",
        "If legumes cause bloating, soak them overnight and introduce slowly to allow adaptation.",
        "We will design travel-friendly substitutions for your cook Javier to follow.",
        "Time-restricted eating (10h window) is a good experiment — we'll monitor glucose and deep sleep.",
        "If ApoB remains high after lifestyle changes, we may need a conversation about pharmacologic options."
    ]
)

# Rachel: physiotherapist
RACHEL_POOL = make_pool("Rachel: ",
    [
        "Try this 12-minute hotel room routine focusing on glute activation and thoracic mobility.",
        "I'll create a travel-ready bodyweight routine that keeps stimulus without heavy equipment.",
        "Introduce a 15-minute pre-workout activation routine to improve form and reduce injury risk.",
        "We'll progress your strength program gradually — focus on movement quality for the first 2 weeks.",
        "If low-back flare-ups recur after flights, we'll add daily mobility and modify lifting cues.",
        "Log your weights in the app so we can track progressive overload and reduce injury risk."
    ]
)

# Neel: concierge lead / relationship
NEEL_POOL = make_pool("Neel: ",
    [
        "Zooming out: trends are heading the right way despite travel volatility. Let's lock the next quarter's plan.",
        "We can shift strategy if preferences or logistics demand it — your priorities guide the plan.",
        "Thanks for the transparency. This is design constraints, not failure. We'll adapt and keep the big picture.",
        "I'll handle escalations and ensure the team reduces your cognitive load so you can focus on outcomes."
    ]
)

# System / automated nudge templates (non-personal)
SYSTEM_POOL = make_pool("System: ",
    [
        "Weekly adherence report: member committed ~5 hours this week; adherence ~50%.",
        "Diagnostic panel scheduled: 12-week follow-up recommended.",
        "Exercise plan auto-update executed (bi-weekly cadence).",
        "Travel protocol deployed for upcoming trip; team has been notified."
    ]
)

PERSONA_POOLS = {}
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
    while pool:
        msg = pool.pop(0)  # pop in deterministic order (seed controls pool order)
        if msg not in USED_MESSAGES[persona]:
            USED_MESSAGES[persona].add(msg)
            return msg
    # Fallback: synthesize a unique message
    fallback = f"{persona}: (auto-generated unique message at {datetime.utcnow().isoformat()})"
    USED_MESSAGES[persona].add(fallback)
    return fallback

def detect_sentiment(text):
    """
    Simple keyword-based sentiment detector: returns one of:
    'angry', 'frustrated', 'curious', 'sad', 'nonchalant', 'positive', 'neutral'
    """
    if not text:
        return "neutral"
    t = text.lower()
    if any(k in t for k in ["angry", "frustrated", "upset", "annoyed", "pissed"]):
        return "angry"
    if any(k in t for k in ["sad", "down", "discourag", "depressed"]):
        return "sad"
    if any(k in t for k in ["why", "how", "what", "could", "would", "maybe", "curious", "question"]):
        return "curious"
    if any(k in t for k in ["fine", "okay", "alright", "nonchalant", "meh"]):
        return "nonchalant"
    if any(k in t for k in ["great", "good", "awesome", "happy"]):
        return "positive"
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
    week_label = f"week_{week_index}"
    # member-conversations this week: poisson around average
    member_convs = poisson_int(AVERAGE_MEMBER_CONVS_PER_WEEK)
    # clamp a bit
    member_convs = max(1, min(member_convs, 8))

    # Travel scheduling: if this week is a travel week (1 out of TRAVEL_EVERY_N_WEEKS)
    travel_week = ((week_index - 1) % TRAVEL_EVERY_N_WEEKS) == 0  # travel at week 1,5,9...
    # Occasionally skip travel to create variation
    if travel_week and random.random() < 0.15:
        travel_week = False

    if travel_week:
        state["in_travel"] = True
        # schedule travel start as Monday of the week
        travel_start = current_date + timedelta(days=1)
        travel_end = travel_start + timedelta(days=6)
        events.append({
            "type": "travel_start",
            "specialist": None,
            "sender": "System",
            "timestamp": format_ts(travel_start),
            "content": f"Travel scheduled: {travel_start.date()} -> {travel_end.date()} ({ROHAN_PROFILE['occupation']} trip). Destination: {random.choice(['London', 'NYC', 'Seoul', 'Tokyo'])}"
        })
    else:
        # possibly return from travel if state indicated in_travel
        if state.get("in_travel"):
            state["in_travel"] = False
            events.append({
                "type": "travel_end",
                "specialist": None,
                "sender": "System",
                "timestamp": format_ts(current_date + timedelta(days=2)),
                "content": "Back in Singapore. Travel protocol complete; monitoring re-adaptation."
            })

    # Diagnostic scheduling: if week is multiple of DIAGNOSTIC_EVERY_WEEKS
    if (week_index - 1) % DIAGNOSTIC_EVERY_WEEKS == 0:
        diag_day = current_date + timedelta(days=random.randint(1, 3))
        events.append({
            "type": "diagnostic_scheduling",
            "specialist": "Ruby",
            "sender": "Ruby",
            "timestamp": format_ts(diag_day),
            "content": pop_unique("Ruby")  # Ruby message
        })
        state["last_diag_week"] = week_index

    # Exercise updates every EXERCISE_UPDATE_EVERY_WEEKS
    if (week_index - 1) % EXERCISE_UPDATE_EVERY_WEEKS == 0:
        # Rachel posts an update
        ex_day = current_date + timedelta(days=random.randint(1, 4))
        events.append({
            "type": "exercise_update",
            "specialist": "Rachel",
            "sender": "Rachel",
            "timestamp": format_ts(ex_day + timedelta(hours=2)),
            "content": pop_unique("Rachel")
        })
        # small chance Rachel suggests progressive block which may help ApoB indirectly
        if random.random() < 0.2:
            # attach a plan change event
            events.append({
                "type": "plan_adaptation",
                "specialist": "Neel",
                "sender": "Neel",
                "timestamp": format_ts(ex_day + timedelta(hours=3)),
                "content": pop_unique("Neel")
            })

    # Member proactive updates approx every 3-5 weeks inserted separately (we sprinkle one sometimes)
    if week_index % random.randint(3, 6) == 0 and random.random() < 0.7:
        # A proactive Rohan message
        msg_day = current_date + timedelta(days=random.randint(1, 5))
        msg = pop_unique("Rohan")
        events.append({
            "type": "message",
            "specialist": None,
            "sender": "Rohan",
            "timestamp": format_ts(msg_day),
            "content": msg,
            "serviceInteractionType": "member-initiated query",
            "decisionRationale": None,
            "healthMetricsSnapshot": state["metrics"].copy(),
            "sentiment": detect_sentiment(msg)
        })
        # Team reply
        responder = random.choice(list(ELYX_TEAM_PERSONAS.keys()))
        reply = pop_unique(responder)
        events.append({
            "type": "message",
            "specialist": responder,
            "sender": responder,
            "timestamp": format_ts(msg_day + timedelta(hours=2)),
            "content": reply,
            "serviceInteractionType": "intervention_update",
            "decisionRationale": f"Response to member-initiated topic from {responder}.",
            "healthMetricsSnapshot": state["metrics"].copy(),
            "sentiment": detect_sentiment(reply)
        })

    # Generate member initiated conversations for the week
    for i in range(member_convs):
        day_offset = random.randint(0, 6)
        time_offset_hours = random.choice([0, 2, 8, 14, 20])  # morning, midday, evening variety
        event_time = current_date + timedelta(days=day_offset, hours=time_offset_hours)
        # Generate Rohan message
        rohan_msg = pop_unique("Rohan")
        sentiment = detect_sentiment(rohan_msg)
        rohan_event = {
            "type": "message",
            "specialist": None,
            "sender": "Rohan",
            "timestamp": format_ts(event_time),
            "content": rohan_msg,
            "serviceInteractionType": "member-initiated query",
            "healthMetricsSnapshot": state["metrics"].copy(),
            "sentiment": sentiment
        }
        events.append(rohan_event)

        # Choose which specialist should respond based on keywords in rohan_msg or state
        lower = rohan_msg.lower()
        responder = None
        # routing rules
        if any(k in lower for k in ["apo", "apob", "cholesterol", "lipid"]):
            responder = "Dr. Warren"
        elif any(k in lower for k in ["travel", "jet", "flight", "london", "ny", "seoul", "tokyo"]):
            responder = random.choice(["Advik", "Ruby"])
        elif any(k in lower for k in ["back pain", "back", "low back", "stiff", "mobility"]):
            responder = "Rachel"
        elif any(k in lower for k in ["food", "oatmeal", "fiber", "sushi", "legumes", "nm n", "nmn", "nr", "supplement"]):
            responder = "Carla"
        elif any(k in lower for k in ["whoop", "garmin", "hrv", "recovery"]):
            responder = random.choice(["Advik", "Dr. Warren"])
        else:
            responder = random.choice(list(ELYX_TEAM_PERSONAS.keys()))

        # Tone handling: if angry or frustrated, route to Neel or Neel+Ruby occasionally
        if sentiment in ["angry", "frustrated"] and random.random() < 0.4:
            responder = "Neel"

        # Build reply
        reply_text = pop_unique(responder)
        reply_event = {
            "type": "message",
            "specialist": responder,
            "sender": responder,
            "timestamp": format_ts(event_time + timedelta(hours=1 + random.randint(0,3))),
            "content": reply_text,
            "serviceInteractionType": "intervention_update",
            "decisionRationale": f"Auto-generated rationale for {responder} responding to member query.",
            "healthMetricsSnapshot": state["metrics"].copy(),
            "sentiment": detect_sentiment(reply_text)
        }
        events.append(reply_event)

        # If message relates to symptoms (e.g., dizzy), escalate to Dr. Warren and Ruby with Priority
        if any(k in lower for k in ["dizz", "dizzy", "sick", "sore throat", "fever", "infection"]):
            # Ruby confirms and Dr. Warren triages
            ruby_msg = pop_unique("Ruby")
            events.append({
                "type": "message",
                "specialist": "Ruby",
                "sender": "Ruby",
                "timestamp": format_ts(event_time + timedelta(hours=2)),
                "content": ruby_msg,
                "serviceInteractionType": "proactive_checkin",
                "decisionRationale": "Flagged for clinical triage.",
                "healthMetricsSnapshot": state["metrics"].copy(),
                "sentiment": detect_sentiment(ruby_msg)
            })
            dr_msg = pop_unique("Dr. Warren")
            events.append({
                "type": "message",
                "specialist": "Dr. Warren",
                "sender": "Dr. Warren",
                "timestamp": format_ts(event_time + timedelta(hours=3)),
                "content": dr_msg,
                "serviceInteractionType": "clinical_triage",
                "decisionRationale": "Medical triage based on reported symptoms.",
                "healthMetricsSnapshot": state["metrics"].copy(),
                "sentiment": detect_sentiment(dr_msg)
            })
            # Modify metrics lightly to reflect illness
            state["metrics"]["RestingHR"] += random.randint(5, 12)
            state["metrics"]["HRV"] = max(20, state["metrics"]["HRV"] - random.randint(8, 20))
            state["metrics"]["RecoveryScore"] = max(0, state["metrics"]["RecoveryScore"] - random.randint(10, 40))

        # If plan adherence low or travel interfering, schedule adaptation
        if random.random() > PLAN_ADHERENCE_PROB:
            # plan adaptation
            adapt_person = "Ruby" if random.random() < 0.6 else "Neel"
            adapt_msg = pop_unique(adapt_person)
            events.append({
                "type": "plan_adaptation",
                "specialist": adapt_person,
                "sender": adapt_person,
                "timestamp": format_ts(event_time + timedelta(hours=4)),
                "content": adapt_msg,
                "serviceInteractionType": "plan_adaptation",
                "decisionRationale": "Adapting plan due to low adherence / logistics.",
                "healthMetricsSnapshot": state["metrics"].copy(),
                "sentiment": detect_sentiment(adapt_msg)
            })

    # Weekly system summary (1 per week)
    summary_day = current_date + timedelta(days=6)
    summary = pop_unique("System")
    events.append({
        "type": "weekly_report",
        "specialist": "System",
        "sender": "System",
        "timestamp": format_ts(summary_day),
        "content": summary,
        "healthMetricsSnapshot": state["metrics"].copy(),
        "serviceInteractionType": "report",
        "sentiment": "neutral"
    })

    # Occasionally insert proactive suggestions from specialists (neel/advik)
    if random.random() < 0.3:
        pro_person = random.choice(["Advik", "Carla", "Dr. Warren", "Neel"])
        pro_msg = pop_unique(pro_person)
        events.append({
            "type": "proactive_checkin",
            "specialist": pro_person,
            "sender": pro_person,
            "timestamp": format_ts(current_date + timedelta(days=random.randint(0,6), hours=9)),
            "content": pro_msg,
            "serviceInteractionType": "proactive_checkin",
            "healthMetricsSnapshot": state["metrics"].copy(),
            "sentiment": detect_sentiment(pro_msg)
        })

    # Occasionally add internal metrics tracking event
    if random.random() < 0.25:
        events.append({
            "type": "internal_metric",
            "specialist": None,
            "sender": "System",
            "timestamp": format_ts(current_date + timedelta(days=random.randint(0,6))),
            "content": json.dumps({
                "physician_hours_this_week": random.choice([0.5, 1, 1.5, 2]),
                "coach_hours_this_week": random.choice([0.5, 1, 2]),
                "concierge_actions": random.randint(1, 5)
            })
        })

    # Minor drift in metrics: simulate gradual improvements or variations
    drift = random.uniform(-2, 2)
    state["metrics"]["HRV"] = max(20, min(90, int(state["metrics"]["HRV"] + drift)))
    state["metrics"]["RestingHR"] = max(50, min(90, int(state["metrics"]["RestingHR"] + (-drift / 2))))
    # glucose drifts slightly
    state["metrics"]["GlucoseAvg"] = max(80, min(140, int(state["metrics"]["GlucoseAvg"] + random.uniform(-3, 3))))
    # recovery nudges
    state["metrics"]["RecoveryScore"] = max(10, min(95, int(state["metrics"]["RecoveryScore"] + random.uniform(-3, 3))))

    # success: return events sorted by timestamp
    events_sorted = sorted(events, key=lambda e: e["timestamp"])
    return events_sorted

# -------------------------
# --- FIX --- Main generate function and new API endpoint
# -------------------------
def generate_full_journey():
    """
    This is the main orchestrator function that generates the entire journey from scratch.
    """
    # CRITICAL: Reset pools at the start of every generation request
    reset_pools()

    all_events = []
    # Initialize the simulation state
    sim_state = {
        "metrics": {
            "HRV": 55, "RestingHR": 62, "GlucoseAvg": 95,
            "RecoveryScore": 75, "ApoB": 110
        },
        "in_travel": False,
        "last_diag_week": 0
    }

    # Loop through the weeks and generate events
    for week in range(1, WEEKS_TO_GENERATE + 1):
        # Calculate the date for the start of the current week
        current_week_start_date = START_DATE + timedelta(weeks=week-1)
        # Generate all events for this week
        week_events = generate_week_events(week, current_week_start_date, sim_state)
        all_events.extend(week_events)

    return all_events

@app.route("/api/generate-full-journey", methods=["GET"])
def get_full_journey():
    """
    This new endpoint correctly calls the main generator to get the full, dynamic journey.
    """
    journey_data = generate_full_journey()
    return jsonify(journey_data)


# -------------------------
# Original journey summary endpoint (now for milestones only)
# -------------------------
@app.route("/api/journey", methods=["GET"])
def get_journey():
    """ This endpoint now correctly serves its purpose of providing a static, high-level summary. """
    return jsonify(generate_journey_summary(user_name="Rohan Patel"))


def generate_journey_summary(user_name="Rohan Patel"):
    """Generate a milestone-only journey (no chat dumps).
    Focused on significant results and events only.
    """
    now = datetime.now()
    journey = []

    milestones = [
        # Diagnostics
        f"{user_name} completed the first full diagnostic panel — ApoB was flagged at 106 mg/dL, leading to a fiber + cardio protocol.",
        f"{user_name} repeated diagnostic tests at 3 months — ApoB improved to 98 mg/dL, confirming plan effectiveness.",
        f"{user_name} underwent VO₂ max testing — score improved by 12%, supporting aerobic training progression.",
        
        # Travel adaptation
        f"{user_name} trialed travel recovery protocol. Post-flight HRV recovery was 20% faster than baseline.",
        
        # Illness / recovery
        f"{user_name} successfully navigated a viral infection using Elyx Sick Day Protocol — recovery was 3 days faster than expected.",
        
        # Sleep & cognitive health
        f"{user_name} trialed blue-light glasses and circadian realignment strategies — recorded best deep sleep metrics to date.",
        f"{user_name} committed to piano training as a cognitive longevity goal, supported by Sarah and Dr. Warren.",
        
        # Nutrition & lifestyle
        f"{user_name} integrated personal chef Javier into nutrition planning — adherence rose to ~80% with travel-proof options.",
        
        # Strength / performance
        f"{user_name} baseline DEXA and strength scan completed — muscle mass gain of +1.5 kg over 8 weeks.",
        f"{user_name} initiated Keynote Peak Performance Protocol for major work event, aligning all pillars (nutrition, sleep, recovery).",
    ]

    # Only log each once (no duplicates, no filler)
    for i, event in enumerate(milestones):
        journey.append({
            "timestamp": (now - timedelta(days=i*10)).strftime("%A, %B %d, %Y"),
            "entry": event
        })

    return list(reversed(journey))

# -------------------------
# Explain decision endpoint
# -------------------------
@app.route('/api/explain-decision', methods=['POST'])
def api_explain_decision():
    data = request.json or {}
    query = (data.get('query') or "").strip()
    journey_data_context = data.get('journeyData', [])

    if not query:
        return jsonify({"error": "Query is required."}), 400

    query_lower = query.lower()

    # Keyword map to route queries to topics
    keyword_map = {
        "exercise": ["exercise", "workout", "training", "zone 2", "zone 5"],
        "travel": ["travel", "jet", "flight", "jet-lag", "timezone"],
        "diagnostic": ["diagnostic", "panel", "blood", "lab", "apo", "apob", "glucose"],
        "sleep": ["sleep", "deep sleep", "whoop", "hrv", "recovery"],
        "stress": ["stress", "anxious", "work stress", "cognition"],
        "nutrition": ["food", "oatmeal", "fiber", "sushi", "psyllium", "diet"],
        "back": ["back", "low-back", "couch stretch", "mobility"],
        "illness": ["sick", "infection", "fever", "cold"]
    }

    # Try matching to a journey item first (keyword-based and full-text)
    relevant_item = None
    for item in reversed(journey_data_context):
        # build searchable text
        content = " ".join([
            str(item.get("content", "")),
            str(item.get("description", "")),
            str(item.get("details", "")),
            str(item.get("decisionRationale", ""))
        ]).lower()
        # direct match
        if query_lower in content:
            relevant_item = item
            break
        # keyword map match
        for k, syns in keyword_map.items():
            if k in query_lower or any(s in query_lower for s in syns):
                if any(s in content for s in syns) or k in content:
                    relevant_item = item
                    break
        if relevant_item:
            break

    # If no item matched, consult knowledge base
    selected_kb = None
    for kb_key in ELYX_KNOWLEDGE_BASE.keys():
        if kb_key in query_lower or kb_key.replace('_', ' ') in query_lower:
            selected_kb = ELYX_KNOWLEDGE_BASE[kb_key]
            break

    # sentiment aware prefix
    sentiment = detect_sentiment(query)
    empathetic_prefix = ""
    if sentiment in ["angry", "frustrated"]:
        empathetic_prefix = "I understand your frustration — that's valid. Here's what happened and why: "
    elif sentiment == "sad":
        empathetic_prefix = "I'm sorry this has been discouraging. Here's the reasoning and the next steps: "
    elif sentiment == "curious":
        empathetic_prefix = "Good question — here's a clear explanation: "
    elif sentiment == "nonchalant":
        empathetic_prefix = "Sure — here's the reasoning: "
    else:
        empathetic_prefix = "Here's the reasoning: "

    explanation_text = None
    rationale = None
    pillar = None
    metrics_snap = None
    effect = None
    monetary = None
    time_eff = None
    specialist = None
    next_steps = None

    if relevant_item:
        # Use fields from the matched journey event
        explanation_text = relevant_item.get('content') or relevant_item.get('description') or relevant_item.get('details') or "We made a decision here based on available data."
        rationale = relevant_item.get('decisionRationale') or "Clinical/team rationale recorded in timeline."
        pillar = relevant_item.get('pillar')
        metrics_snap = relevant_item.get('healthMetricsSnapshot')
        effect = relevant_item.get('interventionEffect')
        monetary = relevant_item.get('monetaryFactor')
        time_eff = relevant_item.get('timeEfficiency')
        specialist = relevant_item.get('specialistInvolved') or relevant_item.get('specialist')
        next_steps = relevant_item.get('nextSteps')
    elif selected_kb:
        # Provide KB-based explanation
        specialist = selected_kb.get("specialist")
        explanation_text = f"{selected_kb.get('summary')} {selected_kb.get('advice')}"
        rationale = f"General clinical knowledge on {specialist}'s domain — contextualized to member needs."
        # metrics snapshot sourced from current metrics if available
        metrics_snap = data.get("currentMetrics")
        next_steps = f"Consider follow-up with {specialist} for formal assessment."
    else:
        # fallback: generate a diverse template using last metrics if provided
        last_entry = journey_data_context[-1] if journey_data_context else {}
        metrics = last_entry.get("healthMetricsSnapshot", {})
        hrv = metrics.get("HRV", "N/A")
        glucose = metrics.get("GlucoseAvg", "N/A")
        recovery = metrics.get("RecoveryScore", "N/A")

        templates = [
            f"This recommendation was made to help improve your long-term health. Specifically, your recovery score is {recovery}, which suggested readiness for the adjustment.",
            f"We adjusted your plan after noticing changes in your metrics — for example, your HRV is {hrv} and your glucose average is {glucose}.",
            f"The rationale is linked to your progress. With HRV at {hrv} and recovery at {recovery}, the system identified a safe point to make changes.",
            f"Your recent results guided this decision. Improvements in recovery and glucose stability ({glucose} mg/dL) showed readiness for the next step.",
            f"This wasn’t random — it was based on patterns in your data. For instance, your recovery is trending around {recovery}, which supports the plan update."
        ]
        explanation_text = random.choice(templates)

    # Build explanation with empathetic prefix and structured fields
    final_text = empathetic_prefix + (explanation_text or "")
    if rationale:
        final_text += f"\n\n**Rationale:** {rationale}"
    if pillar:
        final_text += f"\n**Pillar Impact:** {pillar}"
    if effect:
        final_text += f"\n**Observed Effect:** {effect}"
    if monetary:
        final_text += f"\n**Monetary Factor:** {monetary}"
    if time_eff:
        final_text += f"\n**Time Efficiency:** {time_eff}"
    if specialist:
        final_text += f"\n**Specialist Involved:** {specialist}"
    if next_steps:
        final_text += f"\n**Following Steps:** {next_steps}"
    if metrics_snap:
        try:
            metrics_json = json.dumps(metrics_snap, indent=2)
        except Exception:
            metrics_json = str(metrics_snap)
        final_text += f"\n**Metrics at Time:** {metrics_json}"

    return jsonify({
        "explanation": final_text,
        "detected_sentiment": sentiment
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
