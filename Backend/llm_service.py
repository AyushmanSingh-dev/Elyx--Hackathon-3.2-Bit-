# llm_service.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta
import random
import copy
import re

app = Flask(__name__)
CORS(app)

# --------------------------
# Member profile (required)
# --------------------------
ROHAN_PROFILE = {
    "name": "Rohan Patel",
    "age": 46,
    "gender": "Male",
    "occupation": "Regional Head of Sales (FinTech)",
    "residence": "Singapore",
    "personal_assistant": "Sarah Tan",
    "health_goals": [
        "Reduce risk of heart disease (ApoB focus)",
        "Enhance cognitive function & focus",
        "Annual full-body screenings"
    ],
    "chronic_condition": "mild metabolic dyslipidemia (elevated ApoB)",  # one chronic condition
    "baseline_commitment_hours_per_week": 5
}

# --------------------------
# Elyx team personas
# --------------------------
ELYX_TEAM_PERSONAS = {
    "Ruby": {"role": "Concierge / Orchestrator", "voice": "Empathetic, organized, proactive"},
    "Dr. Warren": {"role": "Medical Strategist", "voice": "Authoritative, precise, scientific"},
    "Advik": {"role": "Performance Scientist", "voice": "Analytical, curious, data-driven"},
    "Carla": {"role": "Nutritionist", "voice": "Practical, educational, behavioral-change focused"},
    "Rachel": {"role": "PT / Physiotherapist", "voice": "Direct, encouraging, function-first"},
    "Neel": {"role": "Concierge Lead", "voice": "Strategic, reassuring, big-picture"}
}

# --------------------------
# Knowledge base (enrichment)
# --------------------------
ELYX_KNOWLEDGE_BASE = {
    "hypertension": {
        "specialist": "Dr. Warren",
        "summary": "Hypertension is sustained high blood pressure and increases cardiovascular risk.",
        "advice": "Monitor BP regularly, consider DASH-style diet, aerobic exercise, and medical review."
    },
    "sleep apnea": {
        "specialist": "Advik",
        "summary": "Sleep apnea is disrupted breathing during sleep that reduces recovery and HRV.",
        "advice": "Consider a sleep study; improve sleep hygiene and weight management; CPAP if confirmed."
    },
    "migraines": {
        "specialist": "Carla",
        "summary": "Migraines are recurrent severe headaches often triggered by food, stress, sleep.",
        "advice": "Keep a headache diary, review dietary triggers, consider magnesium supplementation after review."
    },
    "common cold": {
        "specialist": "Ruby",
        "summary": "Viral URIs that usually resolve with rest and symptomatic care.",
        "advice": "Initiate Sick Day Protocol: rest, hydration, postpone critical meetings if needed; we can help with logistics."
    },
    "gerd": {
        "specialist": "Carla",
        "summary": "Acid reflux that can be managed with dietary changes and timing of meals.",
        "advice": "Avoid trigger foods, avoid late large meals, elevate head of bed when needed."
    }
}

# --------------------------
# Global simulated metrics
# --------------------------
CURRENT_HEALTH_METRICS = {
    "HRV": 45,  # ms
    "RestingHR": 65,  # bpm
    "GlucoseAvg": 105,  # mg/dL
    "ApoB": 105,  # mg/dL (elevated)
    "RecoveryScore": 70,  # %
    "DeepSleep": 60,  # minutes
    "POTS_symptoms": "moderate",
    "BackPain": "mild"
}

# Used to avoid message repetition more than twice
MESSAGE_HISTORY = {}
MAX_REPEAT = 2

# Keep track of recent topics member asked (memory)
ROHAN_ASKED_TOPICS = set()

# --------------------------
# Helper utilities
# --------------------------
def pick_unique_message(pool, tag):
    """
    Pick a message from pool ensuring any identical text isn't repeated > MAX_REPEAT.
    tag is used to track repeats across simulation.
    """
    random.shuffle(pool)
    for candidate in pool:
        key = f"{tag}:{candidate}"
        count = MESSAGE_HISTORY.get(key, 0)
        if count < MAX_REPEAT:
            MESSAGE_HISTORY[key] = count + 1
            return candidate
    # fallback: return random (even if repeat) but increment
    candidate = random.choice(pool)
    key = f"{tag}:{candidate}"
    MESSAGE_HISTORY[key] = MESSAGE_HISTORY.get(key, 0) + 1
    return candidate

def detect_sentiment(text):
    """
    Lightweight rule-based sentiment detection for tone-awareness.
    Returns: 'angry', 'frustrated', 'sad', 'curious', 'nonchalant', 'positive', 'neutral'
    """
    t = text.lower()
    if re.search(r"\b(angry|furious|irritat|mad|upset|pissed)\b", t):
        return "angry"
    if re.search(r"\b(frustrat|disappoint|not happy|fed up)\b", t):
        return "frustrated"
    if re.search(r"\b(sad|discourag|down)\b", t):
        return "sad"
    if re.search(r"\b(why|how come|explain|curious|question)\b", t):
        return "curious"
    if re.search(r"\b(ok|fine|whatever|nonchalant|meh)\b", t):
        return "nonchalant"
    if re.search(r"\b(great|good|happy|pleased|thanks|thank you)\b", t):
        return "positive"
    return "neutral"

def generate_weekly_report(metrics, week_num):
    adherence_hours = round(random.uniform(3.5, 5.5), 1)  # around 5 hours target
    trend_notes = []
    if metrics["ApoB"] >= 100:
        trend_notes.append("ApoB remains elevated — continued focus on diet & exercise.")
    if metrics["HRV"] >= 55:
        trend_notes.append("HRV trending up — recovery improving.")
    if metrics["RecoveryScore"] < 50:
        trend_notes.append("Recovery is low — consider more rest this week.")
    if not trend_notes:
        trend_notes.append("Overall stable progress.")
    report_lines = [
        f"Weekly Report — Week {week_num}",
        f"- Hours committed this week (self-reported): {adherence_hours}h (target ~{ROHAN_PROFILE['baseline_commitment_hours_per_week']}h)",
        f"- HRV: {metrics['HRV']} ms",
        f"- Recovery: {metrics['RecoveryScore']}%",
        f"- Glucose Avg: {metrics['GlucoseAvg']} mg/dL",
        f"- ApoB: {metrics['ApoB']} mg/dL",
        "- Notes:"
    ] + [f"  • {n}" for n in trend_notes]
    urgency = "⚠️" if metrics["ApoB"] >= 100 or metrics["RecoveryScore"] < 45 else "✅"
    report_lines.append(f"{urgency} Recommended focus for next week: {('sleep and recovery' if metrics['RecoveryScore']<60 else 'maintain current plan')}.")
    return {
        "type": "weekly_report",
        "sender": "Elyx System",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "content": "\n".join(report_lines),
        "decisionRationale": "Weekly synthetic summary to track adherence and biomarker trends.",
        "healthMetricsSnapshot": copy.deepcopy(metrics),
        "serviceInteractionType": "system_report",
        "pillar": "All"
    }

def generate_team_nudge(role, metrics):
    nudges = [
        f"{role} here — quick check: how's the new routine working for you this week?",
        f"{role} checking in. Noticed a dip in recovery recently — any barriers we should know about?",
        f"{role} here. If you're finding meals hard when traveling, we can swap to simpler options. Want me to propose alternatives?"
    ]
    content = pick_unique_message(nudges, f"nudge:{role}")
    return {
        "type": "message",
        "sender": role,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "content": content,
        "decisionRationale": "Proactive engagement nudges to maintain adherence and surface barriers early.",
        "healthMetricsSnapshot": copy.deepcopy(metrics),
        "serviceInteractionType": "engagement_nudge",
        "pillar": "Engagement",
        "specialistInvolved": role
    }

# --------------------------
# Core LLM-like response generator (simulated)
# --------------------------
def generate_llm_response(role, prompt_context, current_metrics, chat_history, journey_data_so_far):
    """
    Returns a tuple:
    (response_text, decision_rationale, pillar_impact, health_metrics_snapshot,
     intervention_effect, monetary_factor, time_efficiency, service_interaction_type,
     specialist_involved, next_steps, detected_sentiment)
    """
    prompt_lower = (prompt_context or "").lower()
    snapshot = copy.deepcopy(current_metrics)
    decision_rationale = None
    pillar_impact = None
    intervention_effect = None
    monetary_factor = None
    time_efficiency = None
    service_interaction_type = "general"
    specialist_involved = role if role != "Rohan" else None
    next_steps = None

    # sentiment detection for tone-aware replies (if generated on behalf of team use prompt_context for sentiment)
    detected_sentiment = detect_sentiment(prompt_context or "")

    # -- Member (Rohan) messages (simulated) --
    if role == "Rohan":
        service_interaction_type = "member-initiated query"
        # Pools for variety
        pool = []
        if "initial" in prompt_lower or "onboard" in prompt_lower:
            pool = [
                "I'm feeling overwhelmed with my ad-hoc health routine. I need something coordinated and simple.",
                "Garmin HR seems off even on rest days — I'm not sure I'm interpreting this correctly. Need a plan.",
                "I want a structured approach that's compatible with my travel and work schedule."
            ]
        elif "apo" in prompt_lower or "apob" in prompt_lower or "lipid" in prompt_lower:
            pool = [
                "What's the plan for my elevated ApoB? I want clear, high-impact steps.",
                "How aggressive should we be on ApoB? Diet first or consider medication later?"
            ]
        elif "travel" in prompt_lower or "trip" in prompt_lower:
            pool = [
                "I have a last-minute trip to London. Can you give me a quick jet-lag and workout plan?",
                "Travel next week — what are the minimum steps to avoid derailing progress?"
            ]
        elif "back" in prompt_lower or "pain" in prompt_lower:
            pool = [
                "My lower back flared after the flight. Couch stretch helped a bit, but it's still sore.",
                "Any mobility flows I can do in a hotel room to help my back?"
            ]
        elif "headache" in prompt_lower or "migraine" in prompt_lower:
            pool = [
                "I've been getting frequent headaches. Could these be migraines and what should I track?",
                "Any quick dietary things I can try to rule out triggers for these headaches?"
            ]
        elif "time" in prompt_lower or "busy" in prompt_lower or "quick" in prompt_lower:
            pool = [
                "I only have short windows each day — what's the minimal high-impact routine?",
                "How do I get the most benefit with only ~5 hours/week?"
            ]
        else:
            pool = [
                "Quick check-in: any recommendations for this week?",
                "Just checking — what's the highest-leverage action right now?"
            ]

        response = pick_unique_message(pool, f"rohan_pool:{prompt_lower[:30]}")
        # set a likely sentiment based on current metrics
        if current_metrics["RecoveryScore"] < 50:
            detected_sentiment = random.choice(["frustrated", "sad"])
        elif current_metrics["ApoB"] > 100:
            detected_sentiment = detected_sentiment or "curious"
        else:
            detected_sentiment = detected_sentiment or "neutral"

        return (response, None, "MemberConcerns", snapshot, None, None, None, service_interaction_type, None, None, detected_sentiment)

    # -- Team responses --
    # First check knowledge base hits
    for topic, kb in ELYX_KNOWLEDGE_BASE.items():
        if topic in prompt_lower:
            specialist_involved = kb["specialist"]
            response_candidates = [
                f"Hi Rohan, {specialist_involved} here. That's a great question about {topic}. {kb['summary']} In your case: {kb['advice']}",
                f"{specialist_involved}: Thanks for asking. {kb['summary']} For you specifically, considering your history, {kb['advice']}"
            ]
            response_text = pick_unique_message(response_candidates, f"kb:{topic}")
            decision_rationale = f"Provide evidence-based guidance on {topic} and recommend targeted diagnostic follow-up if indicated."
            pillar_impact = "Clinical Education"
            next_steps = f"Offer consultation with {specialist_involved} and consider targeted diagnostics."
            return (response_text, decision_rationale, pillar_impact, snapshot, None, None, None, "intervention_update", specialist_involved, next_steps, detect_sentiment(response_text))

    # Otherwise, fall back to role-specific behaviors
    if role == "Ruby":
        # Scheduling / concierge tasks
        response_candidates = [
            "Hi Rohan — thanks, I’ve flagged this for Dr. Warren and will coordinate medical records and scheduling.",
            "Ruby here. I'll arrange a phlebotomist to collect your diagnostic panel at your office next Tuesday morning to save time.",
            "I hear you. I'll coordinate with Sarah and the team to consolidate records and minimize your admin."
        ]
        response_text = pick_unique_message(response_candidates, "ruby_sched")
        decision_rationale = "Concierge action to reduce friction and ensure tests/scheduling occur with minimal disruption."
        pillar_impact = "Logistics & Coordination"
        time_efficiency = "High"
        next_steps = "Ruby to confirm appointment and logistics with Sarah."
        return (response_text, decision_rationale, pillar_impact, snapshot, None, None, time_efficiency, "proactive_checkin", "Ruby", next_steps, detect_sentiment(response_text))

    if role == "Dr. Warren":
        # Medical strategy: interpret labs and flag next steps
        if "apo" in prompt_lower or "apob" in prompt_lower or "diagnostic" in prompt_lower:
            if current_metrics["ApoB"] < 90:
                effect_text = "ApoB is improved — continue current lifestyle plan and reassess in next panel."
                intervention_effect = "effective"
            else:
                effect_text = "ApoB remains elevated — intensify dietary intervention and re-assess."
                intervention_effect = "partially effective"
            response_text = (f"Dr. Warren here. Based on recent metrics (ApoB: {current_metrics['ApoB']} mg/dL), {effect_text} "
                             "We'll prioritize dietary and exercise changes and re-test in 3 months.")
            decision_rationale = "Prioritize risk reduction for cardiovascular disease; prefer lifestyle first, escalate if insufficient."
            pillar_impact = "Metabolic & Cardiovascular"
            next_steps = "Carla to refine diet; Rachel to adjust exercise intensity; re-test scheduled in 3 months."
            monetary_factor = "Cost-effective preventative approach"
            return (response_text, decision_rationale, pillar_impact, snapshot, intervention_effect, monetary_factor, None, "diagnostic_results_review", "Dr. Warren", next_steps, detect_sentiment(response_text))

        # generic Dr. Warren checks
        response_text = "Dr. Warren here. We'll interpret results in context and avoid knee-jerk medication choices unless clinically required."
        decision_rationale = "Ensure safe, evidence-based approach to any medical intervention."
        pillar_impact = "Clinical Safety"
        return (response_text, decision_rationale, pillar_impact, snapshot, None, None, None, "advice", "Dr. Warren", None, detect_sentiment(response_text))

    if role == "Carla":
        # Nutrition advice
        response_candidates = [
            "Carla here. For ApoB focus, prioritize soluble fiber, reduce saturated fats, and increase oily fish/plant sterols where possible.",
            "Carla: Practical tip — when traveling, aim for lean protein, steamed veg, and avoid heavy fried items to limit ApoB spikes.",
            "For digestion and headaches, keep a simple food log for 2 weeks to identify potential triggers like aged cheese or caffeine."
        ]
        response_text = pick_unique_message(response_candidates, "carla_adv")
        decision_rationale = "Deliver practical, behavior-focused nutrition advice tailored to frequent travel and limited prep time."
        pillar_impact = "Nutrition"
        next_steps = "Provide a travel-friendly meal list and simple swaps."
        time_efficiency = "High (small swaps)"
        return (response_text, decision_rationale, pillar_impact, snapshot, None, None, time_efficiency, "intervention_update", "Carla", next_steps, detect_sentiment(response_text))

    if role == "Rachel":
        # Exercise and mobility updates every 2 weeks (frontend should call accordingly)
        response_candidates = [
            "Rachel here. Let's introduce a progressive 3-week block emphasizing posterior chain strength and core for your back.",
            "Rachel: Try this 12-minute hotel room routine focusing on glute activation and thoracic mobility.",
            "We will adapt the program to bodyweight alternatives when traveling; goal: maintain stimulus and reduce low-back flare-ups."
        ]
        response_text = pick_unique_message(response_candidates, "rachel_plan")
        decision_rationale = "Adjust exercise prescription based on travel and symptom report to reduce injury risk and improve function."
        pillar_impact = "Structural Health"
        next_steps = "Start the new block next Monday; report soreness and adherence."
        time_efficiency = "Low time cost, focused effect"
        return (response_text, decision_rationale, pillar_impact, snapshot, None, None, time_efficiency, "exercise_update", "Rachel", next_steps, detect_sentiment(response_text))

    if role == "Advik":
        # Travel / sleep / HRV / recovery
        if "travel" in prompt_lower or "jet" in prompt_lower:
            response_text = ("Advik here. For last-minute travel: compressed light-exposure protocol, strategic caffeine timing, and short pre-flight naps. "
                             "We'll send tailored times based on your flight schedule.")
            decision_rationale = "Mitigate circadian disruption and POTS symptoms during international travel."
            pillar_impact = "Sleep & Autonomic"
            next_steps = "Provide specific light/caffeine schedule for flights."
            time_efficiency = "High"
            return (response_text, decision_rationale, pillar_impact, snapshot, None, None, time_efficiency, "travel_protocol", "Advik", next_steps, detect_sentiment(response_text))

        # general advik advice
        response_candidates = [
            "Advik: Small changes to sleep timing and light exposure can shift circadian rhythm quickly when traveling.",
            "Advik here. HRV is influenced by sleep consistency and hydration — small wins compound."
        ]
        response_text = pick_unique_message(response_candidates, "advik_common")
        decision_rationale = "Performance-science-based recommendations to improve recovery and HRV."
        pillar_impact = "Recovery & Sleep"
        return (response_text, decision_rationale, pillar_impact, snapshot, None, None, None, "intervention_update", "Advik", None, detect_sentiment(response_text))

    if role == "Neel":
        response_candidates = [
            "Neel here. We're monitoring long-term ROI of the plan — small improvements now reduce future clinical risk.",
            "Neel: We can shift strategy if preferences or logistics demand it — your priorities guide the plan."
        ]
        response_text = pick_unique_message(response_candidates, "neel_tone")
        decision_rationale = "High-level relationship management and strategy alignment."
        pillar_impact = "Strategy"
        return (response_text, decision_rationale, pillar_impact, snapshot, None, None, None, "relationship", "Neel", None, detect_sentiment(response_text))

    # fallback generic
    response_text = f"{role} here. Thanks — we will review this and respond with an actionable plan."
    return (response_text, "Fallback reply", "General", snapshot, None, None, None, "general", role, None, detect_sentiment(response_text))

# --------------------------
# API: Generate full 8-month journey
# --------------------------
@app.route('/api/generate-journey', methods=['POST'])
def api_generate_journey():
    """
    Generates an 8-month (approx 32-week) journey adhering to constraints:
     - Diagnostic panel every 12 weeks
     - Up to ~5 member-initiated conversations per week on average
     - Exercises updated every 2 weeks
     - Member travels at least 1 week out of every 4 weeks
     - Member commits ~5 hours / week (simulated)
     - ~50% adherence to plan (randomized)
     - Avoid message repetition > MAX_REPEAT
    """
    # Reset globals for each simulation
    global CURRENT_HEALTH_METRICS, MESSAGE_HISTORY, ROHAN_ASKED_TOPICS
    MESSAGE_HISTORY = {}
    ROHAN_ASKED_TOPICS.clear()

    # Start fresh baseline metrics
    CURRENT_HEALTH_METRICS = {
        "HRV": 45,
        "RestingHR": 65,
        "GlucoseAvg": 105,
        "ApoB": 105,
        "RecoveryScore": 70,
        "DeepSleep": 60,
        "POTS_symptoms": "moderate",
        "BackPain": "mild"
    }

    journey = []
    chat_history = []

    # onboarding
    rohan_text, _, _, metrics_snapshot, _, _, _, _, _, _, rohan_sentiment = generate_llm_response("Rohan", "initial onboarding", CURRENT_HEALTH_METRICS, chat_history, journey)
    chat_history.append({"role": "user", "parts": [{"text": rohan_text}]})
    ruby_resp = generate_llm_response("Ruby", "welcome and consolidate onboarding", CURRENT_HEALTH_METRICS, chat_history, journey)[0]
    chat_history.append({"role": "model", "parts": [{"text": ruby_resp}]})
    journey.append({
        "type": "event",
        "eventId": "onboarding_start",
        "timestamp": datetime(2025, 8, 1).strftime("%Y-%m-%d %H:%M"),
        "description": "Member Onboarding Initiated",
        "details": f"Member note: {rohan_text}",
        "decisionRationale": "Standard Elyx onboarding: consolidate records, establish baseline plan.",
        "healthMetricsSnapshot": metrics_snapshot
    })

    # Simulate 32 weeks (~8 months)
    start_date = datetime(2025, 8, 1)
    current_date = start_date

    weeks = 32
    for week in range(1, weeks + 1):
        current_date += timedelta(weeks=1)

        # --- Weekly synthetic report added at end of each week ---
        # We'll append the report at a consistent timestamp (Sunday 20:00)
        report = generate_weekly_report(CURRENT_HEALTH_METRICS, week)
        report["timestamp"] = (current_date + timedelta(days=6)).strftime("%Y-%m-%d 20:00")
        journey.append(report)

        # --- Exercises update every 2 weeks ---
        if week % 2 == 0:
            rachel_msg, rationale, pillar, metrics_snapshot, effect, monetary, time_eff, svc_type, specialist, next_steps, sentiment = generate_llm_response("Rachel", f"exercise update week {week}", CURRENT_HEALTH_METRICS, chat_history, journey)
            journey.append({
                "type": "message",
                "sender": specialist or "Rachel",
                "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "content": rachel_msg,
                "pillar": pillar,
                "decisionRationale": rationale,
                "healthMetricsSnapshot": metrics_snapshot,
                "interventionEffect": effect,
                "serviceInteractionType": "exercise_update",
                "specialistInvolved": specialist
            })
            chat_history.append({"role": "model", "parts": [{"text": rachel_msg}]})

            # 50% adherence logic
            adhered = random.random() < 0.5
            if not adhered:
                # member deviates: ask for adaptation
                rohan_msg, rohan_rationale, _, rohan_metrics, _, _, _, _, _, _, rohan_sentiment = generate_llm_response("Rohan", "deviate from exercise plan due to travel/time/soreness", CURRENT_HEALTH_METRICS, chat_history, journey)
                journey.append({
                    "type": "message",
                    "sender": "Rohan",
                    "timestamp": (current_date + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M"),
                    "content": rohan_msg,
                    "pillar": "Adherence",
                    "decisionRationale": rohan_rationale,
                    "healthMetricsSnapshot": rohan_metrics,
                    "serviceInteractionType": "member_adherence_report"
                })
                chat_history.append({"role": "user", "parts": [{"text": rohan_msg}]})
                # Adaptive response from team
                team = random.choice(["Rachel", "Advik"])
                team_msg, team_rationale, team_pillar, team_metrics, team_effect, team_monetary, team_time, team_svc, team_specialist, team_next_steps, team_sentiment = generate_llm_response(team, "adapt to deviation", CURRENT_HEALTH_METRICS, chat_history, journey)
                journey.append({
                    "type": "message",
                    "sender": team_specialist or team,
                    "timestamp": (current_date + timedelta(hours=6)).strftime("%Y-%m-%d %H:%M"),
                    "content": team_msg,
                    "pillar": team_pillar,
                    "decisionRationale": team_rationale,
                    "healthMetricsSnapshot": team_metrics,
                    "serviceInteractionType": "plan_adaptation",
                    "specialistInvolved": team_specialist
                })
                chat_history.append({"role": "model", "parts": [{"text": team_msg}]})
            else:
                # member adhered and sends a short confirmation
                rohan_msg, _, _, rohan_metrics, _, _, _, _, _, _, rohan_sentiment = generate_llm_response("Rohan", "adhere to exercise plan", CURRENT_HEALTH_METRICS, chat_history, journey)
                journey.append({
                    "type": "message",
                    "sender": "Rohan",
                    "timestamp": (current_date + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M"),
                    "content": rohan_msg,
                    "pillar": "Adherence",
                    "healthMetricsSnapshot": rohan_metrics,
                    "serviceInteractionType": "member_adherence_report"
                })
                chat_history.append({"role": "user", "parts": [{"text": rohan_msg}]})

            # small metric tweaks from exercise update
            CURRENT_HEALTH_METRICS["HRV"] = max(30, CURRENT_HEALTH_METRICS["HRV"] + random.randint(0, 3))
            CURRENT_HEALTH_METRICS["RecoveryScore"] = min(95, CURRENT_HEALTH_METRICS["RecoveryScore"] + random.randint(0, 6))
            CURRENT_HEALTH_METRICS["RestingHR"] = max(50, CURRENT_HEALTH_METRICS["RestingHR"] - random.randint(0, 1))

        # --- Travel 1 week out of 4 (business trips) ---
        if week % 4 == 0:
            travel_start = current_date + timedelta(days=random.randint(1, 2))
            # Pre-travel protocol
            advik_msg, advik_rationale, advik_pillar, advik_metrics, _, _, advik_time, advik_svc, advik_specialist, advik_next_steps, advik_sentiment = generate_llm_response("Advik", f"travel protocol week {week}", CURRENT_HEALTH_METRICS, chat_history, journey)
            journey.append({
                "type": "message",
                "sender": advik_specialist or "Advik",
                "timestamp": travel_start.strftime("%Y-%m-%d %H:%M"),
                "content": advik_msg,
                "pillar": advik_pillar,
                "decisionRationale": advik_rationale,
                "healthMetricsSnapshot": advik_metrics,
                "serviceInteractionType": "travel_protocol",
                "specialistInvolved": advik_specialist
            })
            chat_history.append({"role": "model", "parts": [{"text": advik_msg}]})
            # Travel event
            journey.append({
                "type": "event",
                "eventId": f"travel_week_{week}",
                "timestamp": travel_start.strftime("%Y-%m-%d %H:%M"),
                "description": "Business travel (1 week)",
                "details": "Jet lag mitigation, in-flight mobility and nutrition adjustments.",
                "decisionRationale": "Mitigate travel disruption to health plan.",
                "healthMetricsSnapshot": copy.deepcopy(CURRENT_HEALTH_METRICS),
                "serviceInteractionType": "travel_event",
                "specialistInvolved": "Advik, Ruby"
            })
            # post-travel check-in a week later
            post_travel_date = travel_start + timedelta(days=7)
            post_msg, post_rationale, post_pillar, post_metrics, _, _, _, post_svc, post_spec, post_next, post_sent = generate_llm_response("Advik", "post-travel check-in", CURRENT_HEALTH_METRICS, chat_history, journey)
            journey.append({
                "type": "message",
                "sender": post_spec or "Advik",
                "timestamp": post_travel_date.strftime("%Y-%m-%d %H:%M"),
                "content": post_msg,
                "pillar": post_pillar,
                "decisionRationale": post_rationale,
                "healthMetricsSnapshot": post_metrics,
                "serviceInteractionType": "post_travel_check_in",
                "specialistInvolved": post_spec
            })
            chat_history.append({"role": "model", "parts": [{"text": post_msg}]})

            # Travel impact on metrics
            CURRENT_HEALTH_METRICS["HRV"] = max(30, CURRENT_HEALTH_METRICS["HRV"] - random.randint(0, 6))
            CURRENT_HEALTH_METRICS["DeepSleep"] = max(30, CURRENT_HEALTH_METRICS["DeepSleep"] - random.randint(0, 20))
            CURRENT_HEALTH_METRICS["RecoveryScore"] = max(15, CURRENT_HEALTH_METRICS["RecoveryScore"] - random.randint(0, 12))

        # --- Diagnostic panel every ~12 weeks (quarterly) ---
        if week % 12 == 0:
            # schedule message
            ruby_msg, ruby_reason, _, _, _, _, _, _, _, ruby_next, ruby_sent = generate_llm_response("Ruby", f"schedule diagnostic panel week {week}", CURRENT_HEALTH_METRICS, chat_history, journey)
            journey.append({
                "type": "message",
                "sender": "Ruby",
                "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "content": ruby_msg,
                "decisionRationale": ruby_reason,
                "healthMetricsSnapshot": copy.deepcopy(CURRENT_HEALTH_METRICS),
                "serviceInteractionType": "diagnostic_scheduling"
            })
            chat_history.append({"role": "model", "parts": [{"text": ruby_msg}]})

            # event: diagnostics scheduled
            journey.append({
                "type": "event",
                "eventId": f"diagnostic_week_{week}",
                "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "description": "Quarterly Diagnostic Panel Scheduled",
                "details": "Comprehensive blood panel including ApoB, glucose, lipids.",
                "decisionRationale": "Program requirement: track biomarkers every 3 months.",
                "healthMetricsSnapshot": copy.deepcopy(CURRENT_HEALTH_METRICS),
                "serviceInteractionType": "diagnostic_event"
            })

            # results a week later (simulate modest change)
            results_date = current_date + timedelta(days=7)
            # simulate effect depending on prior interventions and adherence
            if random.random() < 0.6:
                # small improvement
                CURRENT_HEALTH_METRICS["ApoB"] = max(70, CURRENT_HEALTH_METRICS["ApoB"] - random.randint(5, 20))
                CURRENT_HEALTH_METRICS["HRV"] = min(80, CURRENT_HEALTH_METRICS["HRV"] + random.randint(1, 5))
                CURRENT_HEALTH_METRICS["RecoveryScore"] = min(95, CURRENT_HEALTH_METRICS["RecoveryScore"] + random.randint(1, 8))
            else:
                # stable or slight worse
                CURRENT_HEALTH_METRICS["ApoB"] = min(130, CURRENT_HEALTH_METRICS["ApoB"] + random.randint(-3, 6))
                CURRENT_HEALTH_METRICS["RecoveryScore"] = max(20, CURRENT_HEALTH_METRICS["RecoveryScore"] + random.randint(-6, 4))

            # create results message from Dr. Warren
            dr_msg, dr_rationale, dr_pillar, dr_metrics, dr_effect, dr_mon, dr_time, dr_svc, dr_spec, dr_next, dr_sent = generate_llm_response("Dr. Warren", f"diagnostic results week {week}", CURRENT_HEALTH_METRICS, chat_history, journey)
            journey.append({
                "type": "message",
                "sender": dr_spec or "Dr. Warren",
                "timestamp": results_date.strftime("%Y-%m-%d %H:%M"),
                "content": dr_msg,
                "decisionRationale": dr_rationale,
                "healthMetricsSnapshot": copy.deepcopy(CURRENT_HEALTH_METRICS),
                "interventionEffect": dr_metrics,
                "serviceInteractionType": "diagnostic_results_review",
                "specialistInvolved": dr_spec
            })
            chat_history.append({"role": "model", "parts": [{"text": dr_msg}]})

        # --- Member-initiated queries each week: up to 5 avg (simulate 1-5, weighted) ---
        # We'll simulate ~1-5 per week with probabilities
        num_queries = random.choices([1,2,3,4,5], weights=[30,30,20,12,8], k=1)[0]
        for _q in range(num_queries):
            # choose topic not recently asked if possible
            topics = ["poor digestion", "stress", "sleep", "hrv", "cognitive function", "new product", "alternative exercise", "monetary_concern", "time_constraint", "general_query"]
            available = [t for t in topics if t not in ROHAN_ASKED_TOPICS]
            if not available:
                ROHAN_ASKED_TOPICS.clear()
                available = topics
            chosen = random.choice(available)
            ROHAN_ASKED_TOPICS.add(chosen)

            # Generate a member query
            topic_prompts = {
                "poor digestion": "I'm experiencing poor digestion. Any simple suggestions?",
                "stress": "I'm feeling stressed. Any immediate tips?",
                "sleep": "My sleep quality has been poor. Suggestions?",
                "hrv": "How can I improve my HRV? What affects it most?",
                "cognitive function": "How can I improve focus and cognitive resilience?",
                "new product": "Any new wearables worth considering?",
                "alternative exercise": "What exercises can I do in a hotel room?",
                "monetary_concern": "I'm worried about costs. Any cheaper alternatives?",
                "time_constraint": "I have limited time. What are quick high-impact actions?",
                "general_query": "Any updates or new recommendations?"
            }
            member_prompt = topic_prompts[chosen]
            rohan_msg, rohan_rationale, rohan_pillar, rohan_metrics, _, _, _, _, _, rohan_next_steps, rohan_sentiment = generate_llm_response("Rohan", member_prompt, CURRENT_HEALTH_METRICS, chat_history, journey)
            journey.append({
                "type": "message",
                "sender": "Rohan",
                "timestamp": (current_date + timedelta(hours=random.randint(0, 48))).strftime("%Y-%m-%d %H:%M"),
                "content": rohan_msg,
                "decisionRationale": rohan_rationale,
                "healthMetricsSnapshot": rohan_metrics,
                "serviceInteractionType": "member_query"
            })
            chat_history.append({"role": "user", "parts": [{"text": rohan_msg}]})

            # Team picks a respondent
            responder = random.choice(list(ELYX_TEAM_PERSONAS.keys()))
            team_msg, team_rationale, team_pillar, team_metrics, team_effect, team_monetary, team_time, team_svc, team_spec, team_next, team_sent = generate_llm_response(responder, rohan_msg, CURRENT_HEALTH_METRICS, chat_history, journey)
            journey.append({
                "type": "message",
                "sender": team_spec or responder,
                "timestamp": (current_date + timedelta(hours=random.randint(1, 72))).strftime("%Y-%m-%d %H:%M"),
                "content": team_msg,
                "decisionRationale": team_rationale,
                "healthMetricsSnapshot": team_metrics,
                "serviceInteractionType": team_svc or "intervention_update",
                "specialistInvolved": team_spec or responder
            })
            chat_history.append({"role": "model", "parts": [{"text": team_msg}]})

            # Small metric drift after each interaction depending on topic (stochastic)
            if chosen == "sleep":
                CURRENT_HEALTH_METRICS["DeepSleep"] = max(30, min(120, CURRENT_HEALTH_METRICS["DeepSleep"] + random.randint(-10, 10)))
            if chosen == "hrv":
                CURRENT_HEALTH_METRICS["HRV"] = max(30, min(90, CURRENT_HEALTH_METRICS["HRV"] + random.randint(-4, 6)))

        # --- Occasional proactive nudges (~30% of weeks) ---
        if random.random() < 0.3:
            nudger = random.choice(list(ELYX_TEAM_PERSONAS.keys()))
            journey.append(generate_team_nudge(nudger, CURRENT_HEALTH_METRICS))

        # --- Random events: back pain flare or minor illness (~rare) ---
        if week == 5 and random.random() < 0.9:
            # back pain intervention
            r_msg, r_rationale, r_pillar, r_metrics, r_eff, _, _, _, r_spec, r_next, r_sent = generate_llm_response("Rachel", "couch stretch suggestion", CURRENT_HEALTH_METRICS, chat_history, journey)
            journey.append({
                "type": "message",
                "sender": r_spec or "Rachel",
                "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "content": r_msg,
                "decisionRationale": r_rationale,
                "healthMetricsSnapshot": r_metrics,
                "serviceInteractionType": "intervention_update"
            })
        if week == 10 and random.random() < 0.25:
            # minor illness: sick day protocol
            d_msg, d_rationale, d_pillar, d_metrics, d_eff, _, _, _, d_spec, d_next, d_sent = generate_llm_response("Dr. Warren", "sick day protocol", CURRENT_HEALTH_METRICS, chat_history, journey)
            journey.append({
                "type": "message",
                "sender": d_spec or "Dr. Warren",
                "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "content": d_msg,
                "decisionRationale": d_rationale,
                "healthMetricsSnapshot": d_metrics,
                "serviceInteractionType": "health_crisis_event"
            })
            # modify metrics to reflect illness
            CURRENT_HEALTH_METRICS["RecoveryScore"] = max(5, CURRENT_HEALTH_METRICS["RecoveryScore"] - random.randint(20, 50))
            CURRENT_HEALTH_METRICS["HRV"] = max(25, CURRENT_HEALTH_METRICS["HRV"] - random.randint(5, 15))
            CURRENT_HEALTH_METRICS["POTS_symptoms"] = "severe"

        # --- End of week metrics drift (general) ---
        CURRENT_HEALTH_METRICS["HRV"] = max(30, min(90, CURRENT_HEALTH_METRICS["HRV"] + random.randint(-3, 4)))
        CURRENT_HEALTH_METRICS["RestingHR"] = max(50, min(90, CURRENT_HEALTH_METRICS["RestingHR"] + random.randint(-2, 2)))
        CURRENT_HEALTH_METRICS["GlucoseAvg"] = max(85, min(120, CURRENT_HEALTH_METRICS["GlucoseAvg"] + random.randint(-4, 4)))
        CURRENT_HEALTH_METRICS["RecoveryScore"] = max(10, min(95, CURRENT_HEALTH_METRICS["RecoveryScore"] + random.randint(-8, 8)))
        CURRENT_HEALTH_METRICS["DeepSleep"] = max(30, min(120, CURRENT_HEALTH_METRICS["DeepSleep"] + random.randint(-12, 12)))

    # Deduplicate exact consecutive repeats in journey (safety)
    cleaned_journey = []
    last_content = None
    repeat_count = 0
    for item in journey:
        content = item.get("content") or item.get("description") or ""
        if content == last_content:
            repeat_count += 1
        else:
            repeat_count = 0
        # allow up to MAX_REPEAT identical consecutive entries
        if repeat_count <= MAX_REPEAT:
            cleaned_journey.append(item)
        last_content = content

    return jsonify(cleaned_journey)

# --------------------------
# API: Explain decision (keyword agent + tone aware)
# --------------------------
@app.route('/api/explain-decision', methods=['POST'])
def api_explain_decision():
    data = request.json or {}
    query = (data.get('query') or "").strip()
    journey_data_context = data.get('journeyData', []) or []

    if not query:
        return jsonify({"error": "Query is required."}), 400

    query_lower = query.lower()
    sentiment = detect_sentiment(query)

    # Keyword map for matching
    keyword_map = {
        "exercise": ["exercise", "workout", "exercise_update", "plan_adaptation"],
        "travel": ["travel", "jet", "jet lag", "travel_protocol", "travel_event"],
        "diagnostic": ["diagnostic", "panel", "lab", "apo", "apob", "blood"],
        "sleep": ["sleep", "deep", "deepsleep", "insomnia"],
        "stress": ["stress", "hrv", "recovery"],
        "digestion": ["digestion", "gerd", "stomach", "food"],
        "migraine": ["migraine", "headache", "headaches"],
        "illness": ["sick", "illness", "viral", "infection"]
    }

    # Try keyword-based search first (scan journey items in reverse for recency)
    relevant_item = None
    for item in reversed(journey_data_context):
        combined = " ".join([
            str(item.get('content') or ""),
            str(item.get('description') or ""),
            str(item.get('details') or ""),
            str(item.get('decisionRationale') or "")
        ]).lower()
        matched = False
        for key, synonyms in keyword_map.items():
            if key in query_lower or any(syn in query_lower for syn in synonyms):
                if any(syn in combined for syn in synonyms) or key in combined:
                    relevant_item = item
                    matched = True
                    break
        if matched:
            break

    # fallback: direct substring match against decisionRationale or content
    if not relevant_item:
        for item in reversed(journey_data_context):
            combined = " ".join([
                str(item.get('content') or ""),
                str(item.get('description') or ""),
                str(item.get('details') or ""),
                str(item.get('decisionRationale') or "")
            ]).lower()
            if query_lower in combined:
                relevant_item = item
                break

    # empathetic prefix based on sentiment
    if sentiment in ["angry", "frustrated"]:
        prefix = "I understand your frustration. Here's what happened and why we made that decision: "
    elif sentiment == "sad":
        prefix = "I'm sorry you're feeling discouraged. Here's the reasoning in simple terms: "
    elif sentiment == "curious":
        prefix = "Great question — here's the explanation: "
    elif sentiment == "nonchalant":
        prefix = "Sure — quick explanation: "
    elif sentiment == "positive":
        prefix = "Great to hear! For clarity: "
    else:
        prefix = "Here's some context and the rationale: "

    if relevant_item:
        explanation_text = relevant_item.get('content') or relevant_item.get('description') or relevant_item.get('details') or ""
        rationale = relevant_item.get('decisionRationale')
        pillar = relevant_item.get('pillar')
        metrics_snap = relevant_item.get('healthMetricsSnapshot')
        effect = relevant_item.get('interventionEffect')
        monetary = relevant_item.get('monetaryFactor') or relevant_item.get('monetary')
        time_eff = relevant_item.get('timeEfficiency')
        specialist = relevant_item.get('specialistInvolved') or relevant_item.get('sender')
        next_steps = relevant_item.get('nextSteps')
        formatted = prefix + explanation_text + "\n\n"
        if rationale:
            formatted += f"**Rationale:** {rationale}\n"
        if pillar:
            formatted += f"**Pillar Impact:** {pillar}\n"
        if effect:
            formatted += f"**Observed Effect:** {effect}\n"
        if monetary:
            formatted += f"**Monetary Factor:** {monetary}\n"
        if time_eff:
            formatted += f"**Time Efficiency:** {time_eff}\n"
        if specialist:
            formatted += f"**Specialist Involved:** {specialist}\n"
        if next_steps:
            formatted += f"**Following Steps:** {next_steps}\n"
        if metrics_snap:
            formatted += f"**Metrics at Time:** {json.dumps(metrics_snap, indent=2)}\n"
        return jsonify({"explanation": formatted, "detected_sentiment": sentiment})

    # If nothing found, generate a sensible fallback explanation using generate_llm_response
    fallback_text, rationale, pillar, metrics_snap, effect, monetary, time_eff, svc_type, specialist, next_steps, sent = generate_llm_response(
        role="Ruby",
        prompt_context=query,
        current_metrics=CURRENT_HEALTH_METRICS,
        chat_history=[],
        journey_data_so_far=[]
    )
    formatted = prefix + fallback_text + "\n\n"
    if rationale:
        formatted += f"**Rationale:** {rationale}\n"
    if pillar:
        formatted += f"**Pillar Impact:** {pillar}\n"
    if metrics_snap:
        formatted += f"**Metrics at Time:** {json.dumps(metrics_snap, indent=2)}\n"
    return jsonify({"explanation": formatted, "detected_sentiment": sentiment})

# --------------------------
# Run
# --------------------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host='0.0.0.0', port=port, debug=debug)
