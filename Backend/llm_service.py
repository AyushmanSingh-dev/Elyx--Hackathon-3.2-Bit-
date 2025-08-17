# llm_service.py
"""
Elyx Life - Synthetic Journey Generator & Keyword Agent
Produces an 8-month simulated WhatsApp-style conversation timeline for a member (Rohan)
conforming to hackathon constraints, plus a keyword-based explain endpoint.

Usage:
    python llm_service.py
Backend endpoints:
    POST /api/generate-journey   -> returns generated journey JSON (32 weeks ~ 8 months)
    POST /api/explain-decision  -> query + journeyData -> explanation + detected_sentiment
    GET  /api/journey-file      -> returns last saved journey JSON (if present)
"""
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta
import random
import copy
import re

app = Flask(__name__)
CORS(app)

# ---------------------------
# Configuration / Constants
# ---------------------------
SEED = 42
random.seed(SEED)

WEEKS = 32  # ~8 months
DIAGNOSTIC_INTERVAL_WEEKS = 12
EXERCISE_UPDATE_INTERVAL_WEEKS = 2
TRAVEL_EVERY_N_WEEKS = 4
AVG_MEMBER_QUERIES_PER_WEEK = 5  # average; we'll randomize within [1,5] or 3-6 for variability
MEMBER_HOURS_PER_WEEK = 5  # informational guidance in messages
ADHERENCE_PROBABILITY = 0.5  # ~50% adherence

OUTPUT_JOURNEY_FILEPATH = "/tmp/elyx_generated_journey.json"

# Member (Rohan) profile (used to generate contextual messages)
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
        "Annual full-body health screens"
    ],
    "chronic_condition": "elevated_apob",  # single chronic issue for scenario
    "time_commitment_hours_per_week": MEMBER_HOURS_PER_WEEK,
    "values": "Analytical, efficient, evidence-driven",
    "tech": "Garmin watch; considering Oura / Whoop"
}

# Elyx team personas
ELYX_TEAM_PERSONAS = {
    "Ruby": {"role": "Concierge / Orchestrator", "voice": "Empathetic, organized, proactive"},
    "Dr. Warren": {"role": "Medical Strategist", "voice": "Authoritative, precise, clinical"},
    "Advik": {"role": "Performance Scientist", "voice": "Analytical, curious, data-driven"},
    "Carla": {"role": "Nutritionist", "voice": "Practical, educational, behavioral-change focused"},
    "Rachel": {"role": "PT / Physiotherapist", "voice": "Direct, encouraging, functional movement focus"},
    "Neel": {"role": "Concierge Lead", "voice": "Strategic, high-level, reassuring"}
}

# Expandable knowledge base (can be enriched later)
ELYX_KNOWLEDGE_BASE = {
    "apob": {
        "specialist": "Dr. Warren",
        "summary": "ApoB is a marker associated with atherogenic lipoprotein particles; elevated levels increase cardiovascular risk.",
        "advice": "Prioritize dietary fiber, reduce saturated fat, increase cardio and weight-resistance training; re-test quarterly and consider specialist lipid clinic if persistently high."
    },
    "hypertension": {
        "specialist": "Dr. Warren",
        "summary": "High blood pressure increases cardiovascular risk. We track home BP to understand variability.",
        "advice": "Salt moderation, regular aerobic exercise, home BP logs, and consider medication only after specialist review."
    },
    "sleep apnea": {
        "specialist": "Advik",
        "summary": "Sleep apnea reduces quality of sleep and impairs recovery and HRV.",
        "advice": "Overnight oximetry/sleep study if suspected; positional therapy, weight loss, CPAP as appropriate."
    },
    "migraine": {
        "specialist": "Carla",
        "summary": "Migraines are common and can be triggered by diet, sleep, and stress.",
        "advice": "Start a trigger diary, evaluate magnesium status, consider specialist if frequent."
    },
    "travel protocol": {
        "specialist": "Advik",
        "summary": "Jet-lag protocols focus on timed light exposure, meal timing, and sleep hygiene to shift circadian rhythm.",
        "advice": "Pre-shift wake time, morning light on arrival, avoid long naps day 1, and time caffeine strategically."
    },
    "common cold": {
        "specialist": "Ruby",
        "summary": "Common viral upper respiratory tract infection.",
        "advice": "Rest, hydration, Elyx Sick Day Protocol; we can reschedule commitments."
    }
}


# ---------------------------
# Template pools (avoid >2 repeats)
# ---------------------------
# We'll keep counts to avoid exceeding 2 uses per template.
TEMPLATE_USAGE_COUNTER = {}

def choose_template(pool_name, pool):
    """Pick a template while avoiding overuse of exact strings (>2 usage)."""
    # ensure counter structure
    if pool_name not in TEMPLATE_USAGE_COUNTER:
        TEMPLATE_USAGE_COUNTER[pool_name] = {}
    # filter to templates used <2 times
    candidates = [t for t in pool if TEMPLATE_USAGE_COUNTER[pool_name].get(t, 0) < 2]
    if not candidates:
        # reset small counts to avoid getting stuck but keep variety by resetting counters for pool
        TEMPLATE_USAGE_COUNTER[pool_name] = {}
        candidates = pool[:]
    choice = random.choice(candidates)
    TEMPLATE_USAGE_COUNTER[pool_name][choice] = TEMPLATE_USAGE_COUNTER[pool_name].get(choice, 0) + 1
    return choice

# Member message templates by topic
MEMBER_TEMPLATES = {
    "initial": [
        "Honestly, things feel ad-hoc. I need a coordinated plan that fits my travel and work rhythm.",
        "I feel overwhelmed with my current routine and data from my Garmin looks inconsistent. Can we set a proper plan?"
    ],
    "diagnostic_confirm": [
        "Confirm the diagnostic panel next Tuesday morning — can a phlebotomist come to the office?",
        "Tuesday morning works for diagnostics. Please confirm which biomarkers you'll check."
    ],
    "apo_question": [
        "What's the plan for my ApoB? I want concrete steps and the expected timeline for changes.",
        "ApoB is worrying. What high-impact changes should I prioritize right away?"
    ],
    "travel_notice": [
        "Heads up — I have a last-minute trip to London next week. Can we send a jet-lag plan?",
        "Unexpected travel to Seoul for 4 days starting Thursday. Need a quick protocol."
    ],
    "adherence_deviation": [
        "I missed two sessions this week because of travel. Can we adapt the plan?",
        "Busy week — couldn't follow the workouts. Suggest alternatives I can do in hotels."
    ],
    "status_update": [
        "Quick check-in: feeling slightly better this week, energy is improving.",
        "Recovery scores dropped this week; feeling a bit flat."
    ],
    "question_general": [
        "Any new recommendations based on my latest metrics?",
        "What should I focus on this week to make the most progress?"
    ],
    "sick_query": [
        "My son has a cold — best way for me to avoid getting sick during a heavy week?",
        "I'm starting to feel scratchy throat. What's the Elyx sick-day suggestion?"
    ],
    "nutrition_travel": [
        "I'm finding it hard to source the ingredients Carla recommended while traveling. Alternatives?",
        "Low on fiber while traveling — what's the minimum effective approach?"
    ],
    "back_pain": [
        "My lower back flared up after the flight. What’s the next step?",
        "Couch stretch helped a bit but back still sore. Any escalation?"
    ],
    "cognitive": [
        "Would short meditation blocks actually help with my focus?",
        "Hard to focus during late-night calls. Any quick strategies?"
    ]
}

# Team reply templates (fallback) by persona
TEAM_TEMPLATES = {
    "Ruby": [
        "Hi Rohan, Ruby here. Thanks for flagging this — I’ll coordinate the logistics and loop in the right specialist.",
        "Ruby: We can arrange a phlebotomist at your office to make the diagnostic convenient. Confirm availability."
    ],
    "Dr. Warren": [
        "Dr. Warren: Reviewed your numbers. This suggests we should focus on metabolic optimization and re-test in 8–12 weeks.",
        "Dr. Warren: Elevated ApoB remains a concern. We'll prioritize dietary fiber and appropriate exercise adjustments."
    ],
    "Advik": [
        "Advik: For travel, we’ll use a compressed jet-lag protocol — timed light, hydration, and meal timing to shift circadian rhythm.",
        "Advik: HRV dips usually reflect fragmented sleep; let’s adjust training load and test a 10-day sleep routine."
    ],
    "Carla": [
        "Carla: For stress and energy, focus on hydration and mindful protein-forward breakfasts. Travel-proof snack options sent.",
        "Carla: Low on fiber when traveling? Try a shelf-stable soluble-fiber powder and portable high-fiber bars."
    ],
    "Rachel": [
        "Rachel: Try the 2-minute couch stretch and a 5-min mobility sequence before flights.",
        "Rachel: If workouts are missed, a 15-minute bodyweight circuit will retain gains and maintain momentum."
    ],
    "Neel": [
        "Neel: Zooming out — trends look right despite travel volatility. Let’s lock the next quarter while keeping things low cognitive-load.",
        "Neel: I’ll re-schedule non-critical items so you can prioritize recovery during travel."
    ]
}

# ---------------------------
# Utilities
# ---------------------------
def safe_now():
    return datetime.utcnow()

def detect_sentiment(text: str):
    """
    Lightweight lexicon-based sentiment detection for queries.
    Returns: 'angry', 'frustrated', 'curious', 'sad', 'positive', 'nonchalant', 'neutral'
    """
    t = text.lower()
    if re.search(r"\b(frustrat|angry|upset|furious|annoyed)\b", t):
        return "angry"
    if re.search(r"\b(sad|discourag|disappointed|down)\b", t):
        return "sad"
    if re.search(r"\b(why|how come|explain|curious|what happened|why did)\b", t):
        return "curious"
    if re.search(r"\b(great|good|amazing|happy|glad)\b", t):
        return "positive"
    if re.search(r"\b(okay|fine|meh|whatever|nonchalant)\b", t):
        return "nonchalant"
    # default neutral
    return "neutral"

def abbreviate_ts(dt: datetime):
    return dt.strftime("%Y-%m-%d %H:%M")

# ---------------------------
# Core generator
# ---------------------------
def generate_8_month_journey(seed=SEED):
    random.seed(seed)
    journey = []
    chat_history = []
    timeline_events = []

    # reset template usage counter
    global TEMPLATE_USAGE_COUNTER
    TEMPLATE_USAGE_COUNTER = {}

    # start date anchored (we'll use 2025-08-01 as before)
    start_date = datetime(2025, 8, 1, 9, 0)  # 9 AM local-ish
    current_date = start_date

    # initial health metrics
    metrics = {
        "HRV": 45, "RestingHR": 65, "GlucoseAvg": 105, "ApoB": 105,
        "RecoveryScore": 70, "DeepSleep": 60, "POTS_symptoms": "moderate", "BackPain": "mild"
    }

    # onboarding messages
    # Rohan initial
    initial_rohan = choose_template("member.initial", MEMBER_TEMPLATES["initial"])
    journey.append({
        "type": "message",
        "sender": ROHAN_PROFILE["name"],
        "timestamp": abbreviate_ts(current_date),
        "content": initial_rohan,
        "serviceInteractionType": "onboarding",
        "decisionRationale": "Member initiated onboarding with desire for coordinated plan.",
        "healthMetricsSnapshot": copy.deepcopy(metrics),
        "specialistInvolved": None
    })
    chat_history.append({"role": "user", "parts": [{"text": initial_rohan}]})

    # Ruby replies
    current_date += timedelta(hours=2)
    ruby_reply = choose_template("team.ruby", TEAM_TEMPLATES["Ruby"])
    journey.append({
        "type": "message",
        "sender": "Ruby",
        "timestamp": abbreviate_ts(current_date),
        "content": ruby_reply,
        "serviceInteractionType": "onboarding_response",
        "decisionRationale": "Concierge initiates record consolidation and schedules initial assessments.",
        "healthMetricsSnapshot": copy.deepcopy(metrics),
        "specialistInvolved": "Ruby",
        "nextSteps": "Ruby to coordinate medical records and schedule movement assessment."
    })
    chat_history.append({"role": "model", "parts": [{"text": ruby_reply}]})

    # Simulate weeks
    # We'll create a robust schedule: weekly loop with sub-events each week
    for week in range(1, WEEKS + 1):
        # advance one week (we'll use midweek messaging times)
        current_date += timedelta(weeks=1)

        # 1) Weekly summary / proactive check-ins: once per week, send a short team update alternating Neel/Ruby/Dr. Warren/Advik
        if week % 1 == 0:
            # choose a proactive persona
            persona = random.choice(list(ELYX_TEAM_PERSONAS.keys()))
            # create content depending on persona and metrics
            if persona == "Dr. Warren":
                content = f"Dr. Warren: Quick metabolic check-in. ApoB is tracking at ~{metrics['ApoB']} mg/dL. We'll continue fiber + cardio and re-test in 8-12 weeks."
                rationale = "Periodic metabolic monitoring and planning."
            elif persona == "Advik":
                content = f"Advik: Observing HRV ~{metrics['HRV']} ms and Recovery ~{metrics['RecoveryScore']}%. Recommend micro-sleep hygiene adjustments and slightly reduce training intensity if Recovery < 60%."
                rationale = "Performance monitoring to adjust training load and sleep hygiene."
            elif persona == "Carla":
                content = f"Carla: For travel weeks, prioritize anchor breakfast (protein + fiber) and pack travel-proof snacks to maintain glycemic control."
                rationale = "Nutritional strategy for travel weeks."
            elif persona == "Rachel":
                content = "Rachel: Quick mobility suggestion — perform the 2-minute couch stretch pre/post-flight to manage lower back tightness."
                rationale = "Preventive mobility cue for frequent travelers."
            else:  # Ruby or Neel
                content = f"{persona}: We reviewed your week; trends look manageable given travel. We can consolidate next steps in one weekly note."
                rationale = "High-level concierge check-in."
            journey.append({
                "type": "message",
                "sender": persona,
                "timestamp": abbreviate_ts(current_date + timedelta(hours=2)),
                "content": content,
                "serviceInteractionType": "proactive_checkin",
                "decisionRationale": rationale,
                "healthMetricsSnapshot": copy.deepcopy(metrics),
                "specialistInvolved": persona
            })
            chat_history.append({"role": "model", "parts": [{"text": content}]})

        # 2) Diagnostic panels every DIAGNOSTIC_INTERVAL_WEEKS
        if week % DIAGNOSTIC_INTERVAL_WEEKS == 0:
            # schedule diagnostics
            current_date_diag = current_date + timedelta(days=1)
            diag_msg = f"Ruby: It's time for your quarterly diagnostic panel (week {week}). We can arrange a phlebotomist at your office. Please confirm availability."
            journey.append({
                "type": "message",
                "sender": "Ruby",
                "timestamp": abbreviate_ts(current_date_diag),
                "content": diag_msg,
                "serviceInteractionType": "diagnostic_scheduling",
                "decisionRationale": "Quarterly biomarker monitoring as program requirement.",
                "healthMetricsSnapshot": copy.deepcopy(metrics),
                "specialistInvolved": "Ruby",
                "nextSteps": "Schedule phlebotomist and run the panel."
            })
            chat_history.append({"role": "model", "parts": [{"text": diag_msg}]})

            # simulate Rohan confirming
            confirm_text = choose_template("member.diagnostic_confirm", MEMBER_TEMPLATES["diagnostic_confirm"])
            journey.append({
                "type": "message",
                "sender": ROHAN_PROFILE["name"],
                "timestamp": abbreviate_ts(current_date_diag + timedelta(hours=2)),
                "content": confirm_text,
                "serviceInteractionType": "member_confirmation",
                "decisionRationale": "Member confirmed diagnostic scheduling.",
                "healthMetricsSnapshot": copy.deepcopy(metrics),
                "specialistInvolved": None
            })
            chat_history.append({"role": "user", "parts": [{"text": confirm_text}]})

            # simulate results a week later
            results_date = current_date_diag + timedelta(days=7)
            # change metrics slightly (ApoB may trend down/up depending on adherence)
            if random.random() < ADHERENCE_PROBABILITY:
                # adhere: small improvements
                metrics["ApoB"] = max(70, metrics["ApoB"] - random.randint(3, 12))
                metrics["HRV"] = min(90, metrics["HRV"] + random.randint(1, 5))
                metrics["RecoveryScore"] = min(95, metrics["RecoveryScore"] + random.randint(1, 7))
                effect = "improved"
            else:
                # non-adherence: static or worse
                metrics["ApoB"] = metrics["ApoB"] + random.randint(0, 6)
                metrics["HRV"] = max(30, metrics["HRV"] - random.randint(0, 4))
                metrics["RecoveryScore"] = max(20, metrics["RecoveryScore"] - random.randint(0, 8))
                effect = "partially effective"

            dr_msg = (f"Dr. Warren: Your quarterly results show ApoB {metrics['ApoB']} mg/dL. "
                      f"{'Good progress — keep going.' if effect == 'improved' else 'Requires continued attention and refined interventions.'}")
            journey.append({
                "type": "message",
                "sender": "Dr. Warren",
                "timestamp": abbreviate_ts(results_date),
                "content": dr_msg,
                "serviceInteractionType": "diagnostic_results",
                "decisionRationale": "Interpret diagnostic panel and recommend next steps.",
                "healthMetricsSnapshot": copy.deepcopy(metrics),
                "interventionEffect": effect,
                "specialistInvolved": "Dr. Warren",
                "nextSteps": "Carla to adjust diet; Rachel to update exercise intensity; re-test next quarter."
            })
            chat_history.append({"role": "model", "parts": [{"text": dr_msg}]})

            # Rohan reaction
            rohan_reaction = choose_template("member.apo_question", MEMBER_TEMPLATES["apo_question"])
            journey.append({
                "type": "message",
                "sender": ROHAN_PROFILE["name"],
                "timestamp": abbreviate_ts(results_date + timedelta(hours=3)),
                "content": rohan_reaction,
                "serviceInteractionType": "member_query",
                "decisionRationale": "Member asks for clear steps & financial/time implications.",
                "healthMetricsSnapshot": copy.deepcopy(metrics),
                "specialistInvolved": None
            })
            chat_history.append({"role": "user", "parts": [{"text": rohan_reaction}]})

            # Carla + Rachel respond with plan adjustments
            carla_plan = choose_template("team.carla", TEAM_TEMPLATES["Carla"])
            journey.append({
                "type": "message",
                "sender": "Carla",
                "timestamp": abbreviate_ts(results_date + timedelta(hours=5)),
                "content": f"Carla: {carla_plan} We'll emphasize soluble fiber, plant-based proteins, and travel-friendly options.",
                "serviceInteractionType": "intervention_update",
                "decisionRationale": "Dietary refinement to lower ApoB and improve glycemic stability.",
                "healthMetricsSnapshot": copy.deepcopy(metrics),
                "specialistInvolved": "Carla"
            })
            chat_history.append({"role": "model", "parts": [{"text": carla_plan}]})

            # Rachel exercise update following diagnostics
            rachel_plan = choose_template("team.rachel", TEAM_TEMPLATES["Rachel"])
            journey.append({
                "type": "message",
                "sender": "Rachel",
                "timestamp": abbreviate_ts(results_date + timedelta(hours=7)),
                "content": f"Rachel: {rachel_plan} We'll adjust intensity based on recent HRV and Recovery scores.",
                "serviceInteractionType": "exercise_update",
                "decisionRationale": "Adapt exercise to recovery status and biometrics.",
                "healthMetricsSnapshot": copy.deepcopy(metrics),
                "specialistInvolved": "Rachel"
            })
            chat_history.append({"role": "model", "parts": [{"text": rachel_plan}]})

        # 3) Exercise updates every EXERCISE_UPDATE_INTERVAL_WEEKS
        if week % EXERCISE_UPDATE_INTERVAL_WEEKS == 0:
            # Rachel posts an updated exercise plan
            rachel_note = choose_template("team.rachel", TEAM_TEMPLATES["Rachel"])
            journey.append({
                "type": "message",
                "sender": "Rachel",
                "timestamp": abbreviate_ts(current_date + timedelta(hours=3)),
                "content": f"Rachel: {rachel_note} Exercise plan updated for the next 2 weeks.",
                "serviceInteractionType": "exercise_update",
                "decisionRationale": "Biweekly exercise tuning.",
                "healthMetricsSnapshot": copy.deepcopy(metrics),
                "specialistInvolved": "Rachel",
                "nextSteps": "Implement 3 targeted sessions (total ~5 hrs/week)."
            })
            chat_history.append({"role": "model", "parts": [{"text": rachel_note}]})

            # Member adherence: 50% chance to deviate
            if random.random() < ADHERENCE_PROBABILITY:
                # adheres
                rohan_adherence = choose_template("member.status", MEMBER_TEMPLATES["status_update"])
                journey.append({
                    "type": "message",
                    "sender": ROHAN_PROFILE["name"],
                    "timestamp": abbreviate_ts(current_date + timedelta(hours=6)),
                    "content": rohan_adherence,
                    "serviceInteractionType": "member_adherence_report",
                    "decisionRationale": "Member reports adherence / status update.",
                    "healthMetricsSnapshot": copy.deepcopy(metrics),
                    "specialistInvolved": None
                })
                chat_history.append({"role": "user", "parts": [{"text": rohan_adherence}]})
                # slight positive metric drift
                metrics["HRV"] = min(90, metrics["HRV"] + random.randint(0, 3))
                metrics["RecoveryScore"] = min(95, metrics["RecoveryScore"] + random.randint(0, 5))
            else:
                # deviates
                rohan_dev = choose_template("member.adherence_deviation", MEMBER_TEMPLATES["adherence_deviation"])
                journey.append({
                    "type": "message",
                    "sender": ROHAN_PROFILE["name"],
                    "timestamp": abbreviate_ts(current_date + timedelta(hours=6)),
                    "content": rohan_dev,
                    "serviceInteractionType": "member_adherence_report",
                    "decisionRationale": "Member reports deviation due to travel/time constraints.",
                    "healthMetricsSnapshot": copy.deepcopy(metrics),
                    "specialistInvolved": None
                })
                chat_history.append({"role": "user", "parts": [{"text": rohan_dev}]})
                # team adapts with a quick plan
                adapt_persona = random.choice(["Rachel", "Advik"])
                adapt_msg = (f"{adapt_persona}: Understood. We'll send a short hotel-friendly routine and mobility flow — "
                             "15-minute sessions that preserve gains while traveling.")
                journey.append({
                    "type": "message",
                    "sender": adapt_persona,
                    "timestamp": abbreviate_ts(current_date + timedelta(hours=8)),
                    "content": adapt_msg,
                    "serviceInteractionType": "plan_adaptation",
                    "decisionRationale": "Adaptation to maintain adherence during travel/time constraints.",
                    "healthMetricsSnapshot": copy.deepcopy(metrics),
                    "specialistInvolved": adapt_persona
                })
                chat_history.append({"role": "model", "parts": [{"text": adapt_msg}]})
                # slight negative drift
                metrics["RecoveryScore"] = max(20, metrics["RecoveryScore"] - random.randint(0, 6))

        # 4) Travel every TRAVEL_EVERY_N_WEEKS (1 week out of every 4)
        if week % TRAVEL_EVERY_N_WEEKS == 0:
            # simulate travel start in that week
            travel_start = current_date + timedelta(days=random.randint(0, 2))
            travel_event = {
                "type": "event",
                "eventId": f"travel_week_{week}",
                "timestamp": abbreviate_ts(travel_start),
                "description": "Business travel (1 week)",
                "details": "Jet lag protocol, nutrition adjustments, mobility plan for hotel.",
                "decisionRationale": "Member travels frequently; proactive travel mitigation.",
                "healthMetricsSnapshot": copy.deepcopy(metrics),
                "serviceInteractionType": "travel_event",
                "specialistInvolved": "Advik, Ruby"
            }
            journey.append(travel_event)
            chat_history.append({"role": "model", "parts": [{"text": "Travel event created"}]})

            # pre-travel message
            pre_travel = choose_template("team.advik", TEAM_TEMPLATES["Advik"])
            journey.append({
                "type": "message",
                "sender": "Advik",
                "timestamp": abbreviate_ts(travel_start - timedelta(hours=6)),
                "content": f"Advik: {pre_travel} I'll send a compressed jet-lag protocol tailored to the destination.",
                "serviceInteractionType": "travel_protocol_prep",
                "decisionRationale": "Pre-travel mitigation to reduce jet lag impact.",
                "healthMetricsSnapshot": copy.deepcopy(metrics),
                "specialistInvolved": "Advik"
            })
            chat_history.append({"role": "model", "parts": [{"text": pre_travel}]})

            # member travel note (could be a request)
            travel_notice = choose_template("member.travel", MEMBER_TEMPLATES["travel_notice"])
            journey.append({
                "type": "message",
                "sender": ROHAN_PROFILE["name"],
                "timestamp": abbreviate_ts(travel_start),
                "content": travel_notice,
                "serviceInteractionType": "member_travel_notice",
                "decisionRationale": "Member informs of travel and requests protocol.",
                "healthMetricsSnapshot": copy.deepcopy(metrics),
                "specialistInvolved": None
            })
            chat_history.append({"role": "user", "parts": [{"text": travel_notice}]})

            # post-travel check-in one week after travel_start
            post_travel_date = travel_start + timedelta(days=7)
            journey.append({
                "type": "message",
                "sender": "Advik",
                "timestamp": abbreviate_ts(post_travel_date),
                "content": "Advik: Post-travel check-in — how's energy and sleep? Share HRV/Recovery if you can.",
                "serviceInteractionType": "post_travel_check_in",
                "decisionRationale": "Assess travel impact and recovery needs.",
                "healthMetricsSnapshot": copy.deepcopy(metrics),
                "specialistInvolved": "Advik"
            })
            chat_history.append({"role": "model", "parts": [{"text": "Post-travel check-in sent"}]})

            # travel effect on metrics
            metrics["HRV"] = max(30, metrics["HRV"] - random.randint(0, 6))
            metrics["RecoveryScore"] = max(20, metrics["RecoveryScore"] - random.randint(0, 12))
            metrics["DeepSleep"] = max(30, metrics["DeepSleep"] - random.randint(0, 15))

        # 5) Member-initiated random queries up to ~5/week average (simulate 1-6)
        # We'll randomly place these across the week; only add a few to journey to keep output manageable.
        num_queries = random.randint(1, max(1, AVG_MEMBER_QUERIES_PER_WEEK))  # 1..5
        for q_index in range(num_queries):
            # pick topic with weights (more likely: nutrition/travel/sleep/hrv/general)
            topics = ["nutrition_travel", "sleep", "hrv", "cognitive", "back_pain", "sick_query", "general_question", "status_update"]
            weights = [0.18, 0.15, 0.15, 0.12, 0.09, 0.06, 0.15, 0.1]
            topic = random.choices(topics, weights=weights, k=1)[0]
            # choose template
            pool_key_map = {
                "nutrition_travel": "nutrition_travel",
                "sleep": "status_update",
                "hrv": "status_update",
                "cognitive": "cognitive",
                "back_pain": "back_pain",
                "sick_query": "sick_query",
                "general_question": "question_general",
                "status_update": "status_update"
            }
            pool_key = pool_key_map[topic]
            text = choose_template(f"member.{pool_key}", MEMBER_TEMPLATES[pool_key])
            ts = current_date + timedelta(hours=random.randint(0, 48))
            journey.append({
                "type": "message",
                "sender": ROHAN_PROFILE["name"],
                "timestamp": abbreviate_ts(ts),
                "content": text,
                "serviceInteractionType": "member_query",
                "decisionRationale": None,
                "healthMetricsSnapshot": copy.deepcopy(metrics),
                "specialistInvolved": None,
                "sentiment": detect_sentiment(text)
            })
            chat_history.append({"role": "user", "parts": [{"text": text}]})

            # Elyx team replies (choose relevant persona or knowledge base hit)
            # Keyword detection to pick persona:
            reply_persona = None
            text_lower = text.lower()
            if any(k in text_lower for k in ["apob", "apo b", "apo"]):
                reply_persona = "Dr. Warren"
            elif any(k in text_lower for k in ["travel", "jet", "jet lag", "seoul", "london"]):
                reply_persona = "Advik"
            elif any(k in text_lower for k in ["fiber", "protein", "nutrition", "snack"]):
                reply_persona = "Carla"
            elif any(k in text_lower for k in ["back", "couch", "stretch"]):
                reply_persona = "Rachel"
            elif any(k in text_lower for k in ["coordinate", "sarah", "schedule", "phlebotomist"]):
                reply_persona = "Ruby"
            else:
                reply_persona = random.choice(list(ELYX_TEAM_PERSONAS.keys()))

            # Knowledge base hit
            kb_hit = None
            for kb_key in ELYX_KNOWLEDGE_BASE:
                if kb_key in text_lower or any(word in text_lower for word in kb_key.split()):
                    kb_hit = kb_key
                    break

            if kb_hit:
                kb = ELYX_KNOWLEDGE_BASE[kb_hit]
                reply = f"{kb['specialist']}: {kb['summary']} {kb['advice']}"
                persona_used = kb['specialist']
            else:
                # pick a persona reply template
                reply_template = choose_template(f"team.{reply_persona}", TEAM_TEMPLATES.get(reply_persona, ["We're on it."]))
                persona_used = reply_persona
                reply = f"{persona_used}: {reply_template}"

            journey.append({
                "type": "message",
                "sender": persona_used,
                "timestamp": abbreviate_ts(ts + timedelta(hours=2)),
                "content": reply,
                "serviceInteractionType": "response_to_member",
                "decisionRationale": "Responding to member's query with contextual advice.",
                "healthMetricsSnapshot": copy.deepcopy(metrics),
                "specialistInvolved": persona_used,
                "sentiment": detect_sentiment(reply)
            })
            chat_history.append({"role": "model", "parts": [{"text": reply}]})

            # small metric effects based on topic & reply
            if "sleep" in text_lower:
                metrics["DeepSleep"] = max(30, min(120, metrics["DeepSleep"] + random.randint(-10, 12)))
            if "hrv" in text_lower or "recovery" in text_lower:
                metrics["HRV"] = max(30, min(100, metrics["HRV"] + random.randint(-4, 6)))
            if "fiber" in text_lower or "protein" in text_lower:
                metrics["GlucoseAvg"] = max(85, min(130, metrics["GlucoseAvg"] + random.randint(-5, 3)))

        # 6) Occasional events: back pain flares, illness week, or new goal (piano)
        if week == 5:
            # back pain flare
            bp_msg = "Rachel: Try the couch stretch — it's a 2-minute mobility move that often helps lower back tightness. Report back tomorrow."
            journey.append({
                "type": "message",
                "sender": "Rachel",
                "timestamp": abbreviate_ts(current_date + timedelta(hours=1)),
                "content": bp_msg,
                "serviceInteractionType": "intervention_update",
                "decisionRationale": "Short mobility intervention to address reported lower back pain.",
                "healthMetricsSnapshot": copy.deepcopy(metrics),
                "specialistInvolved": "Rachel"
            })
            journey.append({
                "type": "event",
                "eventId": "back_pain_week5",
                "timestamp": abbreviate_ts(current_date + timedelta(hours=1)),
                "description": "Back pain intervention (couch stretch)",
                "details": "2-minute daily couch stretch assigned.",
                "healthMetricsSnapshot": copy.deepcopy(metrics)
            })
            # minor improvement
            metrics["BackPain"] = "mild"
        if week == 10:
            # illness (major setback)
            illness_msg = ("Dr. Warren: Biotelemetry suggests a viral infection. "
                           "Initiate Elyx Sick Day Protocol: rest, hydration, delay major meetings. Ruby will reschedule.")
            journey.append({
                "type": "message",
                "sender": "Dr. Warren",
                "timestamp": abbreviate_ts(current_date + timedelta(hours=1)),
                "content": illness_msg,
                "serviceInteractionType": "health_crisis_event",
                "decisionRationale": "Acute illness detected via biometrics; prioritize recovery.",
                "healthMetricsSnapshot": copy.deepcopy(metrics),
                "specialistInvolved": "Dr. Warren"
            })
            journey.append({
                "type": "event",
                "eventId": "illness_week10",
                "timestamp": abbreviate_ts(current_date + timedelta(hours=1)),
                "description": "Major Illness Setback",
                "details": "Sick Day Protocol activated.",
                "healthMetricsSnapshot": copy.deepcopy(metrics)
            })
            # significant drop
            metrics["RecoveryScore"] = max(5, metrics["RecoveryScore"] - random.randint(20, 50))
            metrics["POTS_symptoms"] = "severe"
        if week == 15:
            # add a new goal (piano)
            piano_msg = ("Neel: Adding weekly piano practice as a cognitive-longevity goal. "
                         "Track subjective focus and HRV alongside practice.")
            journey.append({
                "type": "message",
                "sender": "Neel",
                "timestamp": abbreviate_ts(current_date + timedelta(hours=2)),
                "content": piano_msg,
                "serviceInteractionType": "goal_setting_event",
                "decisionRationale": "Introduce non-medical cognitive investment to improve stress resilience.",
                "healthMetricsSnapshot": copy.deepcopy(metrics),
                "specialistInvolved": "Neel"
            })
            journey.append({
                "type": "event",
                "eventId": "piano_goal_week15",
                "timestamp": abbreviate_ts(current_date + timedelta(hours=2)),
                "description": "Weekly piano practice added",
                "details": "Cognitive practice to be tracked weekly.",
                "healthMetricsSnapshot": copy.deepcopy(metrics)
            })

        # 7) general drift in metrics (small random walk)
        metrics["HRV"] = max(30, min(90, metrics["HRV"] + random.randint(-3, 4)))
        metrics["RestingHR"] = max(50, min(85, metrics["RestingHR"] + random.randint(-2, 2)))
        metrics["GlucoseAvg"] = max(85, min(130, metrics["GlucoseAvg"] + random.randint(-5, 5)))
        metrics["RecoveryScore"] = max(10, min(95, metrics["RecoveryScore"] + random.randint(-8, 8)))
        metrics["DeepSleep"] = max(30, min(120, metrics["DeepSleep"] + random.randint(-12, 12)))

    # final: write to file for inspection and return
    try:
        with open(OUTPUT_JOURNEY_FILEPATH, "w") as f:
            json.dump(journey, f, indent=2)
    except Exception:
        pass

    return journey


# ---------------------------
# Explain-decision endpoint (keyword-agent + sentiment-aware phrasing)
# ---------------------------
def keyword_agent_explain(query: str, journey_data_context: list):
    """
    Find relevant item(s) in journey_data_context based on keywords & rationale,
    detect sentiment of the query, and return a friendly explanation plus detected sentiment.
    """

    if not query:
        return {"error": "Query is required."}, 400

    q_lower = query.lower()
    sentiment = detect_sentiment(query)

    # Keyword map (expandable)
    keyword_map = {
        "exercise": ["exercise", "workout", "training", "exercise_update", "plan_adaptation"],
        "travel": ["travel", "jet", "jet lag", "travel_event", "post_travel"],
        "diagnostic": ["diagnostic", "panel", "lab", "test", "ApoB", "apob", "biomarker"],
        "sleep": ["sleep", "deepsleep", "insomnia", "hrv", "recovery"],
        "stress": ["stress", "burnout", "cognitive", "focus", "meditation"],
        "nutrition": ["fiber", "protein", "carla", "nutrition", "glucose"],
        "back": ["back", "couch stretch", "mobility"],
        "illness": ["sick", "illness", "viral", "sick day", "sick day protocol"],
        "piano": ["piano", "cognitive", "goal"]
    }

    # Build searchable strings and search with both keyword map and direct query match
    relevant_items = []
    for item in reversed(journey_data_context):
        # only examine messages/events with rationale or content
        search_text = " ".join([
            str(item.get("content", "")),
            str(item.get("description", "")),
            str(item.get("details", "")),
            str(item.get("decisionRationale", "")),
            str(item.get("nextSteps", "")),
        ]).lower()
        matched = False
        # 1) direct substring match
        if q_lower in search_text:
            matched = True
        else:
            # 2) keyword map matching
            for k, syns in keyword_map.items():
                if k in q_lower or any(s in q_lower for s in syns):
                    if any(s in search_text for s in syns) or k in search_text:
                        matched = True
                        break
        if matched:
            relevant_items.append(item)
            # collect up to 6 relevant items
            if len(relevant_items) >= 6:
                break

    # Compose empathetic prefix depending on detected sentiment
    if sentiment in ["angry", "frustrated"]:
        prefix = "I understand this is frustrating — it's valid to feel that way. Here's what happened and why:"
    elif sentiment == "sad":
        prefix = "I’m sorry you’re feeling discouraged. Here's the background and how we plan to help:"
    elif sentiment == "curious":
        prefix = "Great question — here's the reasoning in plain terms:"
    elif sentiment == "positive":
        prefix = "Nice to see the positive note — here's the context:"
    elif sentiment == "nonchalant":
        prefix = "Sure — here's a quick explanation:"
    else:
        prefix = "Here’s the reasoning behind that decision:"

    # If we have relevant items, create a multi-item explanation
    if relevant_items:
        parts = [prefix]
        for idx, it in enumerate(relevant_items[:5], start=1):
            header = f"\n\n{idx}. On {it.get('timestamp', 'N/A')} — "
            title = it.get('sender', '') + (f": {it.get('content')[:140]}..." if it.get('content') else it.get('description', ''))
            rationale = it.get('decisionRationale') or it.get('details') or "No explicit rationale recorded."
            metrics = it.get('healthMetricsSnapshot')
            metrics_txt = ""
            if metrics:
                # include only a few load-bearing metrics
                for k in ["HRV", "ApoB", "GlucoseAvg", "RecoveryScore"]:
                    if k in metrics:
                        metrics_txt += f"{k}: {metrics[k]}, "
                metrics_txt = metrics_txt.rstrip(", ")
                if metrics_txt:
                    metrics_txt = f"\nMetrics then: {metrics_txt}"
            next_steps = it.get('nextSteps')
            part = f"{header}{title}\n**Rationale:** {rationale}{metrics_txt}"
            if next_steps:
                part += f"\n**Next steps:** {next_steps}"
            parts.append(part)
        explanation_text = "\n".join(parts)
    else:
        # fallback: provide a generic but informative response using latest metrics if available
        latest = journey_data_context[-1] if journey_data_context else {}
        latest_metrics = latest.get("healthMetricsSnapshot", {}) if latest else {}
        hrv = latest_metrics.get("HRV", "N/A")
        apo = latest_metrics.get("ApoB", "N/A")
        recovery = latest_metrics.get("RecoveryScore", "N/A")
        fallback_templates = [
            f"We didn't find a direct match in your journey for that phrase. Based on your latest snapshot (HRV {hrv} ms, ApoB {apo} mg/dL, Recovery {recovery}%), the likely reason for plan changes is to optimize recovery and reduce cardiovascular risk.",
            f"Couldn't find a specific decision in the timeline for that query. Generally, when we change a plan it's due to biomarker trends (e.g., ApoB or glucose), wearable trends (HRV/recovery), or logistical constraints like travel or adherence."
        ]
        explanation_text = prefix + "\n\n" + random.choice(fallback_templates)

    return {"explanation": explanation_text, "detected_sentiment": sentiment}

# ---------------------------
# Flask endpoints
# ---------------------------
@app.route("/api/generate-journey", methods=["POST"])
def api_generate_journey():
    """
    Generate 8 months of journey data and return it as JSON.
    POST body is ignored for now; accepts optional 'seed' for reproducible generation.
    """
    data = request.json or {}
    seed = data.get("seed", SEED)
    journey = generate_8_month_journey(seed=seed)
    return jsonify(journey), 200

@app.route("/api/explain-decision", methods=["POST"])
def api_explain_decision():
    data = request.json or {}
    query = data.get("query", "")
    journey_data_context = data.get("journeyData", [])
    if not query:
        return jsonify({"error": "Query is required."}), 400

    resp = keyword_agent_explain(query, journey_data_context)
    # If resp is (dict, code) pair from earlier, handle; otherwise return dict
    if isinstance(resp, tuple):
        return jsonify(resp[0]), resp[1]
    return jsonify(resp), 200

@app.route("/api/journey-file", methods=["GET"])
def api_journey_file():
    """
    Return stored file if available for download/inspection.
    """
    if os.path.exists(OUTPUT_JOURNEY_FILEPATH):
        try:
            return send_file(OUTPUT_JOURNEY_FILEPATH, mimetype="application/json", as_attachment=True,
                             download_name=os.path.basename(OUTPUT_JOURNEY_FILEPATH))
        except Exception as e:
            return jsonify({"error": "Unable to send file", "detail": str(e)}), 500
    else:
        return jsonify({"error": "Journey file not generated yet. Call /api/generate-journey first."}), 404

# ---------------------------
# Run app
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)

