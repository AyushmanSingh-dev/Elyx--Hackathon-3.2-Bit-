# Backend/llm_service.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import random

app = Flask(__name__)
CORS(app)

# ------------------------------
# 1) Profile & Team Personas
# ------------------------------
ROHAN_PROFILE = {
    "name": "Rohan Patel",
    "age": 46,
    "gender": "Male",
    "occupation": "Regional Head of Sales (FinTech), high-stress, frequent international travel (UK, US, South Korea, Jakarta)",
    "residence": "Singapore",
    "personal_assistant": "Sarah Tan",
    "health_goals": [
        "Reduce risk of heart disease (family history, ApoB focus)",
        "Enhance cognitive function and focus",
        "Implement annual full-body health screenings"
    ],
    "concerns": [
        "POTS/autonomic dysfunction (dizziness, high intensity HR)",
        "Work-related stress, cognitive fatigue",
        "Lower back pain (from travel/desk work)",
        "Sleep quality issues",
        "Elevated ApoB (metabolic health)",
        "Dietary adherence due to travel/busy schedule"
    ],
    "values": "Analytical, driven, values efficiency, evidence-based approaches",
    "tech_stack": "Garmin watch (for runs), considering Whoop/Oura, willing to share data",
    "lifestyle": "Exercises mornings (20 min), occasional runs, employs a cook (Javier), supportive wife, 2 young kids, ~50% plan adherence."
}

TEAM = {
    "Ruby": {
        "role": "Concierge / Orchestrator",
        "voice": "Empathetic, organized, proactive, removes friction",
        "style": "warm"
    },
    "Dr. Warren": {
        "role": "Medical Strategist",
        "voice": "Authoritative, precise, scientific, explains complex topics",
        "style": "clinical"
    },
    "Advik": {
        "role": "Performance Scientist",
        "voice": "Analytical, curious, pattern-oriented, data-driven insights",
        "style": "analytical"
    },
    "Carla": {
        "role": "Nutritionist",
        "voice": "Practical, educational, focused on behavioral change",
        "style": "coach"
    },
    "Rachel": {
        "role": "PT / Physiotherapist",
        "voice": "Direct, encouraging, focused on form and function",
        "style": "direct"
    },
    "Neel": {
        "role": "Concierge Lead / Relationship Manager",
        "voice": "Strategic, reassuring, focused on the big picture",
        "style": "reassuring"
    }
}

# ------------------------------
# 2) Knowledge Nuggets (for quick, grounded replies across domains)
# ------------------------------
KNOWLEDGE = {
    "apob": {
        "specialist": "Dr. Warren",
        "summary": "Elevated ApoB reflects a higher number of atherogenic particles; lowering typically combines diet quality, fiber, exercise, weight management, and sometimes medication.",
        "advice": "Short-term: increase viscous fiber, reduce saturated fat, add 2–3 cardio sessions/week. Re-test in 8–12 weeks. If still elevated, consider pharmacotherapy after shared decision-making."
    },
    "sleep": {
        "specialist": "Advik",
        "summary": "Fragmented sleep depresses HRV and recovery. Jet lag, late meals, and late caffeine are common drivers.",
        "advice": "Stabilize wake time, front-load light & movement, finish last meal 3+ hours before bed, keep bedroom cool/dark, experiment with 10–15 min wind-down breathwork."
    },
    "jet_lag": {
        "specialist": "Ruby",
        "summary": "Timed light, movement, hydration, and meal timing shift circadian rhythm efficiently.",
        "advice": "Pre-shift wake time by 30–45min over 3–4 days, seek morning light at destination, avoid long naps day 1, and time caffeine after first light exposure."
    },
    "diet_adherence": {
        "specialist": "Carla",
        "summary": "In travel-heavy weeks, adherence hinges on defaults and environment design.",
        "advice": "Anchor breakfast protein/fiber, carry shelf-stable options, pre-order room-service basics, set a ‘no dessert on weekdays’ rule unless planned."
    },
    "back_pain": {
        "specialist": "Rachel",
        "summary": "Long-haul sitting + weak hip extension drives low back tightness.",
        "advice": "Micro-breaks each 45–60 min, hip flexor/couch stretch 90s/side, glute bridges, suitcase carries; modify lifts till pain <3/10 for 72h."
    },
    "cognition_fatigue": {
        "specialist": "Dr. Warren",
        "summary": "Cognitive dips often mirror sleep deficits, stress load, and glucose variability.",
        "advice": "90-min focus blocks + 10-min reset, brighten workspace AM, time caffeine 60–90m after waking, small protein-forward meals to blunt post-lunch dip."
    },
    "hypertension": {
        "specialist": "Dr. Warren",
        "summary": "BP risk responds to sodium reduction, aerobic volume, and weight control.",
        "advice": "DASH-style eating, 150+ min/wk moderate cardio, reduce alcohol; confirm with home BP log: AM/PM x 7–10 days."
    }
}

# ------------------------------
# 3) Simulated Metrics & Memory
# ------------------------------
CURRENT_HEALTH_METRICS = {
    "HRV": 45,          # ms
    "RestingHR": 65,    # bpm
    "GlucoseAvg": 105,  # mg/dL
    "ApoB": 105,        # mg/dL
    "RecoveryScore": 70, # %
    "DeepSleep": 60,    # minutes
    "POTS_symptoms": "moderate",
    "BackPain": "mild"
}

# Memory to avoid repetition and keep story coherent
ROHAN_ASKED_TOPICS = set()
LAST_SPECIALIST_TOUCH = {}  # topic -> week index

# ------------------------------
# 4) Utility: small natural variations
# ------------------------------
def nudge_metric(value, lo, hi, step=(-2, 2)):
    dv = random.randint(step[0], step[1])
    return max(lo, min(hi, value + dv))

def drift_metrics(week):
    """
    Gradual, imperfect trend with occasional setbacks.
    """
    global CURRENT_HEALTH_METRICS
    m = CURRENT_HEALTH_METRICS

    # Slight weekly improvements with randomness; occasional setbacks around travel weeks
    travel_setback = (week % 5 == 0)
    setback = -3 if travel_setback else 0

    m["HRV"] = nudge_metric(m["HRV"] + (1 if week % 3 == 0 else 0) + setback, 30, 80)
    m["RestingHR"] = nudge_metric(m["RestingHR"] - (1 if week % 4 == 0 else 0) - setback, 52, 72)
    m["GlucoseAvg"] = nudge_metric(m["GlucoseAvg"] - (1 if week % 6 == 0 else 0) + (2 if travel_setback else 0), 88, 115)
    # ApoB trends down slowly with occasional plateau
    m["ApoB"] = nudge_metric(m["ApoB"] - (1 if week % 4 == 0 else 0) + (1 if travel_setback else 0), 80, 120, step=(-1, 1))
    m["RecoveryScore"] = nudge_metric(m["RecoveryScore"] + (1 if week % 2 == 0 else 0) - (3 if travel_setback else 0), 45, 92)
    m["DeepSleep"] = nudge_metric(m["DeepSleep"] + (1 if week % 3 == 0 else 0) - (2 if travel_setback else 0), 35, 110)
    if travel_setback and random.random() < 0.3:
        m["BackPain"] = random.choice(["mild", "moderate"])
    else:
        if random.random() < 0.2:
            m["BackPain"] = "mild"

# ------------------------------
# 5) Core: Response Generator
# ------------------------------
def make_follow_up(style):
    followups = {
        "warm": [
            "Does that plan feel doable this week?",
            "Want me to loop in Sarah to remove logistics?",
            "What’s your biggest blocker here?"
        ],
        "analytical": [
            "Can you share 2–3 mornings of HRV/RestingHR trends?",
            "Would you be open to a 10-day experiment and we compare metrics?",
            "If we adjust training load by 10–15%, how confident are you it fits your schedule?"
        ],
        "coach": [
            "Which meal is most at risk this week — breakfast, lunch, or dinner?",
            "If I give you 3 travel-proof options, will you try one daily?",
            "Shall we set a simple rule: protein + fiber at every meal?"
        ],
        "direct": [
            "Rate your pain now 0–10. If >3, we regress the plan for 72h.",
            "Can you add two 5-minute mobility breaks today?",
            "Do you have bands in your bag? If yes, I’ll program a 12-minute circuit."
        ],
        "clinical": [
            "Any new meds/supplements or acute illness recently?",
            "Shall we add labs or a home BP log to clarify the picture?",
            "Are you okay if I document this and set a re-check in 4 weeks?"
        ],
        "reassuring": [
            "Let’s keep the big picture in view — you’re trending the right way.",
            "Do you want me on your next review call to align priorities?",
            "We’ll pace changes so nothing breaks your work rhythm."
        ]
    }
    return random.choice(followups.get(style, ["Sound good?"]))

def persona_prefix(name):
    return f"{name} ({TEAM.get(name, {}).get('role','')}) here. "

def knowledge_reply(topic_key, user_text):
    node = KNOWLEDGE[topic_key]
    who = node["specialist"]
    style = TEAM[who]["style"]
    msg = (
        f"{persona_prefix(who)}Thanks for flagging this. {node['summary']} "
        f"For you, {node['advice']} {make_follow_up(style)}"
    )
    return who, msg, f"Topic: {topic_key}", \
        f"Evidence-based guidance on {topic_key} tailored to Rohan’s profile.", \
        "General Education"

def generate_llm_response(role, prompt_context, current_metrics, chat_history):
    """
    Produces a natural reply for a given team role.
    Returns:
      text, decision_rationale, pillar, next_steps, sentiment
    """
    txt = prompt_context.lower()

    # Map text to knowledge topics
    if "apob" in txt:
        who, msg, rel, rationale, pillar = knowledge_reply("apob", prompt_context)
        return msg, rationale, pillar, "Re-test in 8–12 weeks.", "neutral"

    if any(k in txt for k in ["sleep", "fragmented", "snor", "insomnia"]):
        who, msg, rel, rationale, pillar = knowledge_reply("sleep", prompt_context)
        return msg, rationale, pillar, "Adopt wind-down + fixed wake for 10 days; report HRV/subjective energy.", "neutral"

    if any(k in txt for k in ["jet lag", "travel", "flight", "london", "seoul", "new york"]):
        who, msg, rel, rationale, pillar = knowledge_reply("jet_lag", prompt_context)
        return msg, rationale, pillar, "We’ll send a timed light/meal schedule; confirm arrival times with Ruby.", "neutral"

    if any(k in txt for k in ["adherence", "late dinner", "snack", "protein", "fiber"]):
        who, msg, rel, rationale, pillar = knowledge_reply("diet_adherence", prompt_context)
        return msg, rationale, pillar, "Carla will push a 3-option travel menu to WhatsApp.", "neutral"

    if any(k in txt for k in ["back", "shoulder", "posture", "pain"]):
        who, msg, rel, rationale, pillar = knowledge_reply("back_pain", prompt_context)
        return msg, rationale, pillar, "Rachel to send a 12-minute mobility + activation routine.", "neutral"

    if any(k in txt for k in ["focus", "fatigue", "cognitive"]):
        who, msg, rel, rationale, pillar = knowledge_reply("cognition_fatigue", prompt_context)
        return msg, rationale, pillar, "Trial 90-min focus blocks + post-lunch walk x7 days.", "neutral"

    # Generic role-driven fallback
    style = TEAM.get(role, {}).get("style", "warm")
    msg = (
        f"{persona_prefix(role)}Got it. I’m integrating this into your plan. "
        f"Current snapshot — HRV {current_metrics['HRV']}ms, Recovery {current_metrics['RecoveryScore']}%. "
        f"{make_follow_up(style)}"
    )
    return msg, "Routine check-in adjusted to current metrics.", "General", None, "neutral"

# ------------------------------
# 6) Conversation Events
# ------------------------------
ROHAN_UTTERANCES = {
    "metrics_concern": [
        "My recovery scores are trending down this week. Am I pushing too hard?",
        "HRV is lower the past few mornings even with similar sleep. Adjust training?",
        "Sleep feels fragmented despite 7 hours. Any quick wins?"
    ],
    "travel_related": [
        "Flying to New York next week — can you refresh the travel protocol?",
        "Back from Seoul — energy was flat mid-day. How do we tweak jet lag?",
        "London again. Can we adapt meals to local dining options?"
    ],
    "diet_query": [
        "Adherence slipped this week — too many late client dinners.",
        "I’m low on fiber while traveling. What’s the minimum effective approach?",
        "Need easy protein snacks I can keep in my bag."
    ],
    "pain_update": [
        "Back pain flared up after the flight. What’s the next step?",
        "Shoulder is tight after the new block. Worth modifying?",
        "Desk posture is aggravating my low back. Can we address this?"
    ],
    "cognitive_fatigue": [
        "Hard to focus during late-night calls. Any quick strategies?",
        "Mental fatigue creeping in — HRV seems to mirror it.",
        "Would short meditation blocks actually help focus and recovery?"
    ],
    "family_cold": [
        "My son has a cold — best way for me to avoid it during a heavy week?"
    ],
    "logistics": [
        "Can Sarah coordinate the water quality test and VO2 slot?",
        "I’ve got a 36-hour window next week — can we front-load labs & scans?"
    ]
}

CATEGORY_TO_SPECIALIST = {
    "metrics_concern": "Advik",
    "travel_related": "Ruby",
    "diet_query": "Carla",
    "pain_update": "Rachel",
    "cognitive_fatigue": "Dr. Warren",
    "family_cold": "Neel",
    "logistics": "Ruby"
}

def pick_fresh_category():
    # Prefer something we haven't used recently
    all_cats = list(ROHAN_UTTERANCES.keys())
    unused = [c for c in all_cats if c not in ROHAN_ASKED_TOPICS]
    pool = unused if unused else all_cats
    cat = random.choice(pool)
    ROHAN_ASKED_TOPICS.add(cat)
    return cat

def build_event(sender, timestamp, content, pillar="General", related="General", rationale=None,
                effect=None, monetary=None, time_eff=None, svc_type="general",
                specialist=None, next_steps=None, sentiment="neutral"):
    return {
        "type": "message",
        "sender": sender,
        "timestamp": timestamp,
        "content": content,
        "pillar": pillar,
        "relatedTo": related,
        "decisionRationale": rationale,
        "healthMetricsSnapshot": CURRENT_HEALTH_METRICS.copy(),
        "interventionEffect": effect,
        "monetaryFactor": monetary,
        "timeEfficiency": time_eff,
        "serviceInteractionType": svc_type,
        "specialistInvolved": specialist or sender,
        "nextSteps": next_steps,
        "sentiment": sentiment
    }

def build_timeline_event(timestamp, description, details, rationale=None, pillar="General"):
    return {
        "type": "event",
        "eventId": f"evt_{abs(hash(description+timestamp))%999999}",
        "timestamp": timestamp,
        "description": description,
        "details": details,
        "decisionRationale": rationale or "",
        "healthMetricsSnapshot": CURRENT_HEALTH_METRICS.copy(),
        "interventionEffect": None,
        "monetaryFactor": None,
        "timeEfficiency": None,
        "pillar": pillar,
        "nextSteps": None
    }

def generate_dynamic_convo(week, current_date, chat_history):
    """
    One short back-and-forth on a fresh topic.
    """
    cat = pick_fresh_category()
    rohan_text = random.choice(ROHAN_UTTERANCES[cat])
    t1 = (current_date + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
    rohan_ev = build_event(
        sender="Rohan",
        timestamp=t1,
        content=rohan_text,
        pillar="Member Engagement",
        related=cat,
        svc_type="member-initiated query",
        specialist=None
    )
    chat_history.append({"role": "user", "parts": [{"text": rohan_text}]})

    specialist = CATEGORY_TO_SPECIALIST.get(cat, "Ruby")
    reply, rationale, pillar, next_steps, sentiment = generate_llm_response(
        role=specialist,
        prompt_context=rohan_text,
        current_metrics=CURRENT_HEALTH_METRICS,
        chat_history=chat_history
    )
    t2 = (current_date + timedelta(days=1, hours=2)).strftime("%Y-%m-%d %H:%M")
    team_ev = build_event(
        sender=specialist,
        timestamp=t2,
        content=reply,
        pillar=pillar,
        related=f"Response to {cat}",
        rationale=rationale,
        svc_type="intervention_update",
        specialist=specialist,
        next_steps=next_steps,
        sentiment=sentiment
    )
    chat_history.append({"role": "model", "parts": [{"text": reply}]})

    return [rohan_ev, team_ev]

# ------------------------------
# 7) API: Generate Journey
# ------------------------------
@app.route('/api/generate-journey', methods=['POST'])
def api_generate_journey():
    """
    Generates ~8 months of realistic, varied conversation + events.
    """
    global CURRENT_HEALTH_METRICS, ROHAN_ASKED_TOPICS, LAST_SPECIALIST_TOUCH
    # Reset state each run
    CURRENT_HEALTH_METRICS = {
        "HRV": 45, "RestingHR": 65, "GlucoseAvg": 105, "ApoB": 105,
        "RecoveryScore": 70, "DeepSleep": 60, "POTS_symptoms": "moderate", "BackPain": "mild"
    }
    ROHAN_ASKED_TOPICS = set()
    LAST_SPECIALIST_TOUCH = {}

    timeline = []
    chat_history = []

    start_date = datetime(2025, 8, 1)
    now = start_date

    # Onboarding pair
    onboarding_user = "Ruby (Concierge / Orchestrator) here. Welcome, Rohan. We'll remove friction and coordinate everything behind the scenes. What feels most urgent right now?"
    timeline.append(build_event("Ruby", now.strftime("%Y-%m-%d %H:%M"), onboarding_user,
                                pillar="Onboarding", related="welcome",
                                rationale="Set expectations; reduce friction; invite first concern.",
                                svc_type="proactive check-in"))
    chat_history.append({"role": "model", "parts": [{"text": onboarding_user}]})

    rohan_first = "Honestly, things feel ad-hoc. High travel, inconsistent routines. I want a coordinated plan that fits my work rhythm."
    timeline.append(build_event("Rohan", (now + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"), rohan_first,
                                pillar="Member Engagement", related="initial_plan",
                                svc_type="member-initiated query"))
    chat_history.append({"role": "user", "parts": [{"text": rohan_first}]})

    # Ruby reassures
    reassurance = f"{persona_prefix('Ruby')}Understood. We'll coordinate diagnostics, training, and nutrition so you only see the next clear step. I’ll loop in Dr. Warren for baselining."
    timeline.append(build_event("Ruby", (now + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"), reassurance,
                                pillar="Onboarding", related="coordination",
                                rationale="Position single front door; reduce overwhelm.",
                                svc_type="intervention_update"))

    # Add a baseline diagnostics event
    diag_evt = build_timeline_event(
        (now + timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
        "Baseline diagnostics scheduled",
        "Fasting labs + wearable data ingestion. ApoB, fasting glucose, lipids, hsCRP.",
        rationale="Create shared baseline for longitudinal tracking.",
        pillar="Diagnostics"
    )
    timeline.append(diag_evt)

    # Simulate 32 weeks
    for week in range(1, 33):
        now += timedelta(weeks=1)
        drift_metrics(week)

        # Every 2 weeks: one realistic back-and-forth on a fresh topic
        if week % 2 == 0:
            timeline.extend(generate_dynamic_convo(week, now, chat_history))

        # Every 4 weeks: short ApoB/metabolic touch from Dr. Warren (but phrased naturally & not repetitive)
        if week % 4 == 0:
            style = TEAM["Dr. Warren"]["style"]
            msg = (
                f"{persona_prefix('Dr. Warren')}Quick metabolic check-in. ApoB is tracking at ~{CURRENT_HEALTH_METRICS['ApoB']} mg/dL. "
                "We’ll stay the course on fiber and cardio, and reassess in 8–12 weeks. "
                f"{make_follow_up(style)}"
            )
            timeline.append(build_event(
                "Dr. Warren",
                (now + timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
                msg,
                pillar="Metabolic Health",
                related="apob_followup",
                rationale="Periodic checkpoint tied to goal; avoids over-rotation.",
                svc_type="proactive check-in"
            ))

        # Occasional logistics or travel event (non-chat timeline entry)
        if week % 5 == 0:
            desc = random.choice([
                "Long-haul travel week",
                "Board-level review week (late calls)",
                "Regional sales summit (dense schedule)"
            ])
            details = random.choice([
                "Expect reduced RecoveryScore; pre-schedule light exposure windows.",
                "Nutrition defaults pre-ordered via Sarah.",
                "Add 2× micro mobility sessions to reduce back tightness."
            ])
            timeline.append(build_timeline_event(
                (now + timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
                desc, details, pillar="Context"
            ))

    # Final wrap with Neel to keep arc coherent
    final_msg = f"{persona_prefix('Neel')}Zooming out: trends are heading the right way despite travel volatility. Let’s lock in the next quarter’s plan so you keep gains without extra cognitive load."
    timeline.append(build_event("Neel",
                                (now + timedelta(days=5)).strftime("%Y-%m-%d %H:%M"),
                                final_msg,
                                pillar="Strategy",
                                related="quarterly_planning",
                                rationale="Sustainability & alignment to role load.",
                                svc_type="proactive check-in"))

    return jsonify(timeline)

# ------------------------------
# 8) API: Explain a Decision
# ------------------------------
@app.route('/api/explain-decision', methods=['POST'])
def api_explain_decision():
    data = request.json
    query = data.get('query')
    journey_data_context = data.get('journeyData', [])

    if not query:
        return jsonify({"error": "Query is required."}), 400

    relevant_item = None
    ql = query.lower()

    searchable = [
        it for it in journey_data_context
        if it.get('decisionRationale') or it.get('content') or it.get('description') or it.get('details')
    ]

    for item in reversed(searchable):
        blob = " ".join([
            str(item.get('content', '')),
            str(item.get('description', '')),
            str(item.get('details', '')),
            str(item.get('decisionRationale', ''))
        ])
        if ql in blob.lower():
            relevant_item = item
            break

    # Pull latest snapshot
    last_entry = journey_data_context[-1] if journey_data_context else {}
    metrics = last_entry.get("healthMetricsSnapshot", {})
    hrv = metrics.get("HRV", "N/A")
    glucose = metrics.get("GlucoseAvg", "N/A")
    recovery = metrics.get("RecoveryScore", "N/A")

    templates = [
        f"This recommendation balanced impact with your workload. Your recovery is {recovery}%, suggesting we can progress without overloading you.",
        f"We weighed recent patterns — HRV ~{hrv}ms and glucose avg ~{glucose} mg/dL — and picked the next safest, highest-leverage step.",
        f"The plan shifts now because readiness looks adequate (Recovery {recovery}%). The choice minimizes friction during travel-heavy weeks.",
        f"Based on adherence signals and metrics (HRV {hrv}ms), we chose an option that preserves consistency over intensity.",
        f"This wasn’t random — it follows the trend line we’ve been tracking and your stated priorities around time-efficiency."
    ]

    prefix = "Here’s the context: "
    if any(w in ql for w in ["why", "confused", "unclear", "doubt"]):
        prefix = "I get why you’re asking — that’s reasonable. "
    elif any(w in ql for w in ["angry", "frustrated", "upset"]):
        prefix = "I hear your frustration. "
    elif any(w in ql for w in ["great", "good", "progress", "happy"]):
        prefix = "Great observation. "

    if relevant_item:
        rationale = relevant_item.get('decisionRationale')
        pillar = relevant_item.get('pillar') or relevant_item.get('relatedTo')
        effect = relevant_item.get('interventionEffect')
        monetary = relevant_item.get('monetaryFactor')
        time_eff = relevant_item.get('timeEfficiency')
        specialist = relevant_item.get('specialistInvolved') or relevant_item.get('sender')
        next_steps = relevant_item.get('nextSteps')

        base = relevant_item.get('content') or relevant_item.get('description') or relevant_item.get('details') or "This was a plan update."
        explanation_text = prefix + random.choice(templates) + "\n\n" + base

        lines = []
        if rationale: lines.append(f"**Rationale:** {rationale}")
        if pillar: lines.append(f"**Pillar Impact:** {pillar}")
        if effect: lines.append(f"**Observed Effectiveness:** {effect}")
        if monetary: lines.append(f"**Cost Consideration:** {monetary}")
        if time_eff: lines.append(f"**Time Efficiency:** {time_eff}")
        if specialist: lines.append(f"**Specialist Involved:** {specialist}")
        if next_steps: lines.append(f"**Next Steps:** {next_steps}")

        return jsonify({"explanation": explanation_text + ("\n" + "\n".join(lines) if lines else ""),
                        "sentiment": relevant_item.get("sentiment", "neutral")})

    # Fallback: synthesize a reasonable explanation using knowledge routes
    synth_reply, rationale, pillar, next_steps, _ = generate_llm_response(
        role="Neel",
        prompt_context=query,
        current_metrics=CURRENT_HEALTH_METRICS,
        chat_history=[]
    )
    explanation_text = prefix + random.choice(templates) + "\n\n" + synth_reply
    extra = []
    if rationale: extra.append(f"**Rationale:** {rationale}")
    if pillar: extra.append(f"**Pillar Impact:** {pillar}")
    if next_steps: extra.append(f"**Next Steps:** {next_steps}")

    return jsonify({"explanation": explanation_text + ("\n" + "\n".join(extra) if extra else ""),
                    "sentiment": "neutral"})

# ------------------------------
# 9) Entrypoint
# ------------------------------
if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1',
            host='0.0.0.0',
            port=int(os.environ.get('PORT', 5001)))
