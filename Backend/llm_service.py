# Backend/llm_service.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta
import random

app = Flask(__name__)
CORS(app)

# --- Rohan Patel's Profile (Summarized for LLM context) ---
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

# --- Elyx Team Personas (Summarized for LLM context) ---
ELYX_TEAM_PERSONAS = {
    "Ruby": {"role": "Concierge / Orchestrator", "voice": "Empathetic, organized, proactive, removes friction"},
    "Dr. Warren": {"role": "Medical Strategist", "voice": "Authoritative, precise, scientific, explains complex topics"},
    "Advik": {"role": "Performance Scientist", "voice": "Analytical, curious, pattern-oriented, data-driven insights"},
    "Carla": {"role": "Nutritionist", "voice": "Practical, educational, focused on behavioral change"},
    "Rachel": {"role": "PT / Physiotherapist", "voice": "Direct, encouraging, focused on form and function"},
    "Neel": {"role": "Concierge Lead / Relationship Manager", "voice": "Strategic, reassuring, focused on the big picture"}
}

# --- Simulated Health Metrics (dynamic & global for generation) ---
# This dictionary will be modified during the journey generation to reflect changes.
CURRENT_HEALTH_METRICS = {
    "HRV": 45, # ms
    "RestingHR": 65, # bpm
    "GlucoseAvg": 105, # mg/dL
    "ApoB": 105, # mg/dL (elevated)
    "RecoveryScore": 70, # %
    "DeepSleep": 60, # minutes
    "POTS_symptoms": "moderate", # mild, moderate, severe
    "BackPain": "mild" # none, mild, moderate, severe
}

# --- LLM Response Function (Simulated & Enriched) ---
def generate_llm_response(role, prompt_context, current_metrics, chat_history, journey_data_so_far):
    prompt_lower = prompt_context.lower()
    response_text = ""
    decision_rationale = None
    pillar_impact = None
    health_metrics_snapshot = current_metrics.copy() # Snapshot current metrics
    intervention_effect = None
    monetary_factor = None
    time_efficiency = None
    service_interaction_type = "general"
    specialist_involved = role if role != "Rohan" else None

    # --- Rohan's Responses (Patient Concerns & Priorities) ---
    if role == "Rohan":
        service_interaction_type = "member-initiated query"
        if "coordinated plan" in prompt_lower:
            response_text = "Ruby, I'm feeling overwhelmed with my ad-hoc health routine. High work stress, and my Garmin HR seems off even on rest days. I need a proper, coordinated plan. My current supplement list is attached."
        elif "medical records" in prompt_lower:
            response_text = "Acknowledged. How long will that take? And what about my fitness goals?"
        elif "movement assessment" in prompt_lower:
            response_text = "Understood. I'm also thinking about my stress levels. Any immediate tips?"
        elif "couch stretch" in prompt_lower and "helped" in prompt_lower:
            response_text = "The couch stretch helped a bit! Also, for stress, any immediate dietary tips? I struggle with consistent energy."
        elif "diagnostic panel" in prompt_lower:
            response_text = "Yes, next Tuesday works. Confirmed. I'm keen to see the numbers, though I'm always a bit skeptical until I see tangible results."
        elif "apo b" in prompt_lower or "apob" in prompt_lower:
            response_text = "What's the plan for the ApoB? I want clear, actionable steps. Monetary factors are important too."
        elif "jet lag" in prompt_lower or "travel" in prompt_lower:
            response_text = "This sounds critical. I need a clear, minute-by-minute guide for my upcoming trip. How can we make it time-efficient?"
        elif "not feeling great" in prompt_lower or "illness" in prompt_lower:
            response_text = "This is a major setback. The board meeting is critical. What's the immediate plan? I need to maximize my recovery output."
        elif "recovery" in prompt_lower and "green" in prompt_lower:
            response_text = "Good. I feel it. Let's get back to the plan."
        elif "piano" in prompt_lower:
            response_text = "I've always wanted to learn piano. From a health and performance perspective, is this a worthwhile use of my time?"
        elif "poor digestion" in prompt_lower:
            response_text = "I'm experiencing poor digestion. Any suggestions that are easy to integrate into my busy schedule?"
        elif "monetary" in prompt_lower or "cost" in prompt_lower or "expensive" in prompt_lower:
            response_text = "I'm looking for cost-effective options. Can you suggest alternatives for X?"
        elif "time" in prompt_lower or "busy" in prompt_lower or "quick" in prompt_lower:
            response_text = "I have limited time. What's the most time-efficient way to achieve Y?"
        else:
            response_text = random.choice([
                "Understood. Thanks for the update. What's next?",
                "Okay, I'll look into that. Is there a more efficient way?",
                "Good. Let's keep pushing that number down. Any tips for integrating this seamlessly?",
                "I'm starting to look for a piano. I see this as part of my health investment."
            ])
    # --- Elyx Team Member Responses (Prioritizing, Value-Driven, Adaptable) ---
    else:
        service_interaction_type = "proactive check-in" if "check-in" in prompt_lower else "intervention update"
        if "initial submission" in prompt_lower and role == "Ruby":
            response_text = "Hi Rohan, thank you for sharing this. We understand. Our goal is to bring coordination to your health. I'm flagging your concerns for Dr. Warren to review immediately. We're here to make this seamless for you."
            decision_rationale = "Prioritizing Rohan's core concern of 'ad-hoc health' by initiating a coordinated clinical review, maximizing early engagement output."
            time_efficiency = "Immediate flagging for quick initial response."
        elif "medical records" in prompt_lower and role == "Dr. Warren":
            response_text = "Rohan, Dr. Warren here. I've reviewed your initial submission. The symptoms and data strongly suggest autonomic dysfunction (Pillar 1). To proceed, we must consolidate your complete medical records. This is non-negotiable for safety. Ruby will manage the process."
            decision_rationale = "To establish a clinical-grade strategy, ensure safety, and avoid redundant testing by consolidating complete medical history. This is a foundational step for maximizing long-term health output and preventing future costly errors."
            pillar_impact = "Pillar 1 (Autonomic Health)"
        elif "medical records" in prompt_lower and role == "Ruby":
            response_text = "The timeline can vary depending on clinics' response speed, but we will manage the entire process. We typically aim for records within 2-3 weeks. We'll provide daily updates to keep you in the loop, saving your time."
            time_efficiency = "Elyx team handles logistics to save Rohan's time."
        elif "fitness goals" in prompt_lower and role == "Advik":
            response_text = "Rohan, Advik here. A good first step is a comprehensive movement assessment to understand your baseline and identify any imbalances. Ruby can help schedule this with Rachel. This will inform your personalized exercise plan, maximizing your workout output."
            decision_rationale = "To establish a data-driven baseline for personalized exercise programming, optimizing for Rohan's time constraints and avoiding injury. This maximizes efficiency and adherence for long-term gains."
            pillar_impact = "Pillar 4 (Structural Health)"
        elif "stress levels" in prompt_lower and role == "Carla":
            response_text = "Rohan, Carla here. For immediate stress support, focus on consistent hydration and mindful eating. Avoiding processed snacks can also help. These are simple, low-cost dietary adjustments that integrate easily."
            pillar_impact = "Pillar 3 (Fuel), Pillar 5 (Stress Resilience)"
            monetary_factor = "Low-cost/no-cost dietary adjustments."
            time_efficiency = "Easy to integrate, minimal time commitment."
        elif "couch stretch" in prompt_lower and role == "Rachel":
            response_text = "Hi Rohan, Rachel here. Given your frequent travel and desk work, let's try a simple 2-minute 'couch stretch' for your lower back pain. It targets hip flexor tightness. Try it and let me know if it helps. This is a quick, effective intervention."
            decision_rationale = "To address Rohan's reported lower back pain, a common issue from prolonged sitting during travel, with a time-efficient, non-invasive intervention that integrates into his daily routine for maximum relief."
            pillar_impact = "Pillar 4 (Structural Health)"
            time_efficiency = "2-minute, quick intervention."
        elif "q1 diagnostic panel" in prompt_lower and role == "Ruby":
            response_text = "Rohan, it's time to schedule your Q1 diagnostic panel. This comprehensive test will give us a baseline for your metabolic and hormonal health. We can arrange a phlebotomist to come to your office. Does next Tuesday morning work? This maximizes your convenience."
            decision_rationale = "Full diagnostic test panel every three months is a core program requirement to track progress on biomarkers and identify new areas for intervention. This maximizes long-term health output by providing critical data for personalized adjustments, minimizing future health costs."
            pillar_impact = "Pillar 1 (Autonomic), Pillar 3 (Fuel), Pillar 5 (Stress Resilience)"
            time_efficiency = "Phlebotomist to office for convenience."
        elif "apo b" in prompt_lower and role == "Dr. Warren":
            response_text = "Rohan, your ApoB is 105 mg/dL. This is elevated and a primary focus for long-term heart disease risk reduction, aligning with your top health goal. Carla will lead dietary interventions (reducing saturated fat, increasing fiber), and Rachel's exercise plan will be critical. We will aggressively target this with lifestyle changes and re-test in Q2."
            decision_rationale = "Elevated ApoB is a serious cardiovascular risk factor based on Q1 diagnostics. The intervention prioritizes Rohan's top health goal, using integrated lifestyle changes for maximum impact and long-term investment. This approach is more sustainable than medication alone and is a cost-effective preventative measure."
            pillar_impact = "Pillar 3 (Fuel), Pillar 4 (Structural), Pillar 1 (Autonomic)"
            monetary_factor = "Cost-effective preventative measure."
        elif "travel protocol" in prompt_lower and role == "Advik":
            response_text = "For your Tokyo trip, we'll build a precise light exposure and avoidance schedule to shift your circadian rhythm, and Rachel will find a suitable gym near your hotel. This proactive approach aims to minimize jet lag and maintain your health routine, maximizing your performance during demanding travel."
            decision_rationale = "To proactively mitigate the known impact of international travel on Rohan's POTS and overall performance, ensuring his demanding work schedule doesn't derail health progress. Focus on time-efficient, integrated solutions that fit his travel lifestyle, maximizing his output during business trips."
            pillar_impact = "Pillar 1 (Autonomic), Pillar 2 (Sleep), Pillar 4 (Structural), Pillar 5 (Stress Resilience)"
            time_efficiency = "Precise schedule for jet lag, gym finding for efficiency."
        elif "illness" in prompt_lower and role == "Dr. Warren":
            response_text = "Rohan, the biotelemetry strongly suggests a viral infection. We are initiating the Elyx Sick Day Protocol immediately. You must postpone your board meeting. Your cognitive function will be severely impaired, and you risk a much longer recovery if you push through. Ruby will manage rescheduling."
            decision_rationale = "Prioritizing immediate health stabilization and long-term recovery over short-term business commitments, as pushing through illness risks severe setbacks and prolonged recovery, ultimately impacting long-term performance and health investment. This maximizes long-term output and avoids higher future medical costs."
            pillar_impact = "All Pillars (Acute Health Crisis)"
            monetary_factor = "Avoids higher future medical costs."
        elif "piano" in prompt_lower and role == "Neel":
            response_text = "We agree. Learning piano is an excellent intervention for cognitive longevity, engaging multiple brain domains. We will add 'Weekly Piano Practice' as a trackable goal within Pillar 5 (Stress Management) of your Plan. This integrates a personal interest with health investment and offers a non-monetary health benefit."
            decision_rationale = "To align with Rohan's interest in cognitive longevity and stress management, providing a personalized, engaging, and long-term health investment that integrates naturally into his lifestyle and offers a non-monetary benefit, maximizing his personal growth output."
            pillar_impact = "Pillar 5 (Stress Resilience), Cognitive Health"
            monetary_factor = "Non-monetary health benefit."
            time_efficiency = "Integrated into weekly routine."
        elif "deviate from exercise" in prompt_lower:
            response_text = "Understood, Rohan. It's common for plans to need adjustments. Let's adapt. We can explore shorter, more flexible routines for your travel weeks, or bodyweight alternatives that require no equipment, maximizing adherence even when time is tight. Your health journey is dynamic."
            decision_rationale = "Adapting to Rohan's dynamic schedule and adherence patterns to ensure continued progress, focusing on flexible and time-efficient alternatives to maximize health output without feeling forced."
            monetary_factor = "Suggests bodyweight alternatives (cost-effective)."
            time_efficiency = "Shorter, more flexible routines."
        elif "monetary concern" in prompt_lower:
            response_text = "We hear your concern about monetary factors. We always strive to provide cost-effective alternatives and ensure every recommendation is a justified investment in your long-term health. For example, simple dietary changes can have a huge impact on ApoB without high cost."
            decision_rationale = "Prioritizing Rohan's financial considerations by offering cost-effective alternatives and justifying investments as long-term health benefits, ensuring the plan is sustainable and maximizes value."
            monetary_factor = "Emphasizes cost-effectiveness and justified investment."
        elif "time" in prompt_lower or "busy" in prompt_lower or "quick" in prompt_lower:
            response_text = "We understand your time constraints. Our goal is to seamlessly integrate health into your busy life. We can focus on micro-interventions, like 5-minute mobility breaks or strategic meal prepping with Javier, to maximize health output with minimal time investment."
            decision_rationale = "Adapting the plan to Rohan's severe time constraints by focusing on micro-interventions and efficient strategies, ensuring health activities are integrated seamlessly and maximize output per minute invested."
            time_efficiency = "Focus on micro-interventions and strategic planning."
        else:
            response_text = random.choice([
                f"Hi Rohan, {role} here. We're continuously optimizing your plan based on your feedback and data to maximize your health output. How are things going with your current priorities?",
                f"Understood. We'll integrate this into your personalized plan to maximize your health output, considering your time and monetary factors. Thanks for the feedback.",
                f"That's a great point, {ELYX_TEAM_PERSONAS[role]['role']} will look into that for you, ensuring it aligns with your priorities and lifestyle.",
                f"We're always looking for ways to make your health journey more seamless and impactful, turning medical procedures into lifestyle habits. What's on your mind?"
            ])
            decision_rationale = "Routine check-in / general response, emphasizing personalized care, value, and lifestyle integration."
            pillar_impact = "General"
            monetary_factor = "General emphasis on value."
            time_efficiency = "General emphasis on efficiency."

    return response_text, decision_rationale, pillar_impact, health_metrics_snapshot, intervention_effect, monetary_factor, time_efficiency, service_interaction_type, specialist_involved

# --- API Endpoints ---
@app.route('/api/generate-journey', methods=['POST'])
def api_generate_journey():
    """
    Generates the full 8-month journey data dynamically.
    This endpoint is called by the frontend to get the entire simulated log.
    """
    journey_data = []
    chat_history = []
    start_date = datetime(2025, 8, 1)
    current_date = start_date

    # Reset metrics for a fresh simulation
    global CURRENT_HEALTH_METRICS
    CURRENT_HEALTH_METRICS = {
        "HRV": 45, "RestingHR": 65, "GlucoseAvg": 105, "ApoB": 105,
        "RecoveryScore": 70, "DeepSleep": 60, "POTS_symptoms": "moderate", "BackPain": "mild"
    }

    # Initial onboarding
    rohan_msg, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist = generate_llm_response("Rohan", "Initial onboarding: I need a proper, coordinated plan. My Garmin HR seems off.", CURRENT_HEALTH_METRICS, chat_history, journey_data)
    journey_data.append({
        "type": "message", "sender": "Rohan", "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
        "content": rohan_msg, "pillar": rohan_pillar, "relatedTo": "Initial onboarding",
        "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
        "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
        "timeEfficiency": rohan_time, "serviceInteractionType": rohan_interaction_type,
        "specialistInvolved": rohan_specialist
    })
    chat_history.append({"role": "user", "parts": [{"text": rohan_msg}]})

    ruby_msg, ruby_rationale, ruby_pillar, ruby_metrics, ruby_effect, ruby_monetary, ruby_time, ruby_interaction_type, ruby_specialist = generate_llm_response("Ruby", "welcome Rohan and acknowledge concerns", CURRENT_HEALTH_METRICS, chat_history, journey_data)
    journey_data.append({
        "type": "message", "sender": "Ruby", "timestamp": (current_date + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M"),
        "content": ruby_msg, "pillar": ruby_pillar, "relatedTo": "Rohan_Initial",
        "decisionRationale": ruby_rationale, "healthMetricsSnapshot": ruby_metrics,
        "interventionEffect": ruby_effect, "monetaryFactor": ruby_monetary,
        "timeEfficiency": ruby_time, "serviceInteractionType": ruby_interaction_type,
        "specialistInvolved": ruby_specialist
    })
    chat_history.append({"role": "model", "parts": [{"text": ruby_msg}]})
    
    journey_data.append({
        "type": "event", "eventId": "onboarding_start", "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
        "description": "Member Onboarding Initiated", "details": "Rohan shares medical history and goals.",
        "decisionRationale": "Standard Elyx onboarding process to establish baseline and goals for a personalized plan.",
        "healthMetricsSnapshot": CURRENT_HEALTH_METRICS.copy(), "interventionEffect": None,
        "monetaryFactor": None, "timeEfficiency": None, "serviceInteractionType": "onboarding",
        "specialistInvolved": "Elyx Team"
    })

    # Simulate 8 months (approx 32 weeks)
    for week in range(1, 33):
        current_date += timedelta(weeks=1)
        
        # --- Weekly Check-in (Ruby/Neel) ---
        if week % 4 == 0: # Monthly review
            team_member = random.choice(["Neel", "Ruby"])
            msg_context = f"weekly/monthly check-in for progress review and alignment with goals. Current metrics: {CURRENT_HEALTH_METRICS}. Rohan's adherence is ~50%."
            msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist = generate_llm_response(team_member, msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": team_member, "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "content": msg, "pillar": pillar, "relatedTo": "Previous interactions",
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                "specialistInvolved": specialist
            })
            chat_history.append({"role": "model", "parts": [{"text": msg}]})
            
            rohan_response, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist = generate_llm_response("Rohan", f"response to monthly check-in. Current state: {CURRENT_HEALTH_METRICS}", CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": "Rohan", "timestamp": (current_date + timedelta(minutes=random.randint(5, 15))).strftime("%Y-%m-%d %H:%M"),
                "content": rohan_response, "pillar": rohan_pillar, "relatedTo": "Monthly check-in",
                "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                "timeEfficiency": rohan_time, "serviceInteractionType": rohan_interaction_type,
                "specialistInvolved": rohan_specialist
            })
            chat_history.append({"role": "user", "parts": [{"text": rohan_response}]})


        # --- Diagnostic Tests (Every 3 months) ---
        if week % 12 == 0: # Roughly every 3 months
            msg_context = "schedule Q1/Q2/Q3 diagnostic panel"
            msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist = generate_llm_response("Ruby", msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": "Ruby", "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "content": msg, "pillar": pillar, "relatedTo": "Program requirement",
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                "specialistInvolved": specialist
            })
            chat_history.append({"role": "model", "parts": [{"text": msg}]})
            
            rohan_response, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist = generate_llm_response("Rohan", f"response to diagnostic scheduling. Current state: {CURRENT_HEALTH_METRICS}", CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": "Rohan", "timestamp": (current_date + timedelta(minutes=random.randint(5, 15))).strftime("%Y-%m-%d %H:%M"),
                "content": rohan_response, "pillar": rohan_pillar, "relatedTo": "Diagnostic scheduling",
                "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                "timeEfficiency": rohan_time, "serviceInteractionType": rohan_interaction_type,
                "specialistInvolved": rohan_specialist
            })
            chat_history.append({"role": "user", "parts": [{"text": rohan_response}]})

            # Simulate event for diagnostic scheduled
            journey_data.append({
                "type": "event", "eventId": f"diagnostic_scheduled_week_{week}", "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "description": f"Quarterly Diagnostic Panel Scheduled (Week {week})",
                "details": "Comprehensive baseline tests for metabolic and hormonal health.",
                "decisionRationale": rationale, "healthMetricsSnapshot": CURRENT_HEALTH_METRICS.copy(),
                "interventionEffect": None, "monetaryFactor": monetary, "timeEfficiency": time_eff,
                "serviceInteractionType": "diagnostic_scheduling", "specialistInvolved": "Ruby"
            })

            # Simulate results discussion a week later
            results_date = current_date + timedelta(days=7)
            if week == 12: # Q1 results
                # Simulate elevated ApoB and initial metrics
                CURRENT_HEALTH_METRICS["ApoB"] = 105
                CURRENT_HEALTH_METRICS["HRV"] = 48 # Slight increase
                CURRENT_HEALTH_METRICS["POTS_symptoms"] = "moderate"
                msg_context = f"discuss Q1 diagnostic results, elevated ApoB: {CURRENT_HEALTH_METRICS['ApoB']}"
                msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist = generate_llm_response("Dr. Warren", msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
                journey_data.append({
                    "type": "message", "sender": "Dr. Warren", "timestamp": results_date.strftime("%Y-%m-%d %H:%M"),
                    "content": msg, "pillar": pillar, "relatedTo": "Q1 Diagnostics",
                    "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                    "interventionEffect": effect, "monetaryFactor": monetary,
                    "timeEfficiency": time_eff, "serviceInteractionType": "diagnostic_results",
                    "specialistInvolved": specialist
                })
                chat_history.append({"role": "model", "parts": [{"text": msg}]})
                
                rohan_response, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist = generate_llm_response("Rohan", f"response to ApoB results. Current state: {CURRENT_HEALTH_METRICS}", CURRENT_HEALTH_METRICS, chat_history, journey_data)
                journey_data.append({
                    "type": "message", "sender": "Rohan", "timestamp": (results_date + timedelta(minutes=random.randint(5, 15))).strftime("%Y-%m-%d %H:%M"),
                    "content": rohan_response, "pillar": rohan_pillar, "relatedTo": "ApoB discussion",
                    "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                    "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                    "timeEfficiency": rohan_time, "serviceInteractionType": rohan_interaction_type,
                    "specialistInvolved": rohan_specialist
                })
                chat_history.append({"role": "user", "parts": [{"text": rohan_response}]})

                journey_data.append({
                    "type": "event", "eventId": f"q1_results_week_{week}", "timestamp": results_date.strftime("%Y-%m-%d %H:%M"),
                    "description": "Q1 Diagnostic Results Reviewed", "details": f"Elevated ApoB ({CURRENT_HEALTH_METRICS['ApoB']} mg/dL) identified as primary focus.",
                    "decisionRationale": rationale, "healthMetricsSnapshot": CURRENT_HEALTH_METRICS.copy(),
                    "interventionEffect": "ApoB elevated, focus shifted to metabolic health.",
                    "monetaryFactor": "Preventative measures to avoid future high costs.", "timeEfficiency": "Efficient diagnosis.",
                    "serviceInteractionType": "diagnostic_review", "specialistInvolved": "Dr. Warren"
                })

            elif week == 24: # Q2 results
                # Simulate improvement due to interventions
                CURRENT_HEALTH_METRICS["ApoB"] = random.randint(70, 85) # Improved
                CURRENT_HEALTH_METRICS["HRV"] = random.randint(55, 70) # Improved
                CURRENT_HEALTH_METRICS["POTS_symptoms"] = "mild"
                CURRENT_HEALTH_METRICS["BackPain"] = "none"
                msg_context = f"discuss Q2 diagnostic results, improved ApoB: {CURRENT_HEALTH_METRICS['ApoB']}"
                msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist = generate_llm_response("Dr. Warren", msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
                journey_data.append({
                    "type": "message", "sender": "Dr. Warren", "timestamp": results_date.strftime("%Y-%m-%d %H:%M"),
                    "content": msg, "pillar": pillar, "relatedTo": "Q2 Diagnostics",
                    "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                    "interventionEffect": effect, "monetaryFactor": monetary,
                    "timeEfficiency": time_eff, "serviceInteractionType": "diagnostic_results",
                    "specialistInvolved": specialist
                })
                chat_history.append({"role": "model", "parts": [{"text": msg}]})
                
                rohan_response, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist = generate_llm_response("Rohan", f"response to improved ApoB results. Current state: {CURRENT_HEALTH_METRICS}", CURRENT_HEALTH_METRICS, chat_history, journey_data)
                journey_data.append({
                    "type": "message", "sender": "Rohan", "timestamp": (results_date + timedelta(minutes=random.randint(5, 15))).strftime("%Y-%m-%d %H:%M"),
                    "content": rohan_response, "pillar": rohan_pillar, "relatedTo": "ApoB discussion",
                    "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                    "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                    "timeEfficiency": rohan_time, "serviceInteractionType": rohan_interaction_type,
                    "specialistInvolved": rohan_specialist
                })
                chat_history.append({"role": "user", "parts": [{"text": rohan_response}]})

                journey_data.append({
                    "type": "event", "eventId": f"q2_results_week_{week}", "timestamp": results_date.strftime("%Y-%m-%d %H:%M"),
                    "description": "Q2 Diagnostic Results Reviewed", "details": f"Improved ApoB ({CURRENT_HEALTH_METRICS['ApoB']} mg/dL) due to interventions.",
                    "decisionRationale": rationale, "healthMetricsSnapshot": CURRENT_HEALTH_METRICS.copy(),
                    "interventionEffect": "ApoB significantly improved, HRV increased, POTS symptoms mild.",
                    "monetaryFactor": "Positive ROI on health investment.", "timeEfficiency": "Efficient progress.",
                    "serviceInteractionType": "diagnostic_review", "specialistInvolved": "Dr. Warren"
                })

        # --- Exercise Updates (Every 2 weeks) ---
        if week % 2 == 0:
            team_member = "Rachel"
            msg_context = f"update exercise plan based on progress. Current metrics: {CURRENT_HEALTH_METRICS}. Rohan's adherence is ~50%."
            msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist = generate_llm_response(team_member, msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": team_member, "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "content": msg, "pillar": pillar, "relatedTo": "Exercise progress",
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                "specialistInvolved": specialist
            })
            chat_history.append({"role": "model", "parts": [{"text": msg}]})
            
            # Simulate Rohan's adherence (50% adherence)
            if random.random() < 0.5: # Rohan deviates
                rohan_deviation, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist = generate_llm_response("Rohan", f"deviate from exercise plan due to travel/time/soreness. Current state: {CURRENT_HEALTH_METRICS}", CURRENT_HEALTH_METRICS, chat_history, journey_data)
                journey_data.append({
                    "type": "message", "sender": "Rohan", "timestamp": (current_date + timedelta(minutes=random.randint(30, 60))).strftime("%Y-%m-%d %H:%M"),
                    "content": rohan_deviation, "pillar": rohan_pillar, "relatedTo": "Exercise deviation",
                    "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                    "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                    "timeEfficiency": rohan_time, "serviceInteractionType": rohan_interaction_type,
                    "specialistInvolved": rohan_specialist
                })
                chat_history.append({"role": "user", "parts": [{"text": rohan_deviation}]})
                
                # Elyx team adapts
                adapt_msg, adapt_rationale, adapt_pillar, adapt_metrics, adapt_effect, adapt_monetary, adapt_time, adapt_interaction_type, adapt_specialist = generate_llm_response(random.choice(["Rachel", "Advik"]), f"adapt to Rohan's exercise deviation. Current state: {CURRENT_HEALTH_METRICS}", CURRENT_HEALTH_METRICS, chat_history, journey_data)
                journey_data.append({
                    "type": "message", "sender": random.choice(["Rachel", "Advik"]), "timestamp": (current_date + timedelta(minutes=random.randint(90, 120))).strftime("%Y-%m-%d %H:%M"),
                    "content": adapt_msg, "pillar": adapt_pillar, "relatedTo": "Adaptation",
                    "decisionRationale": adapt_rationale, "healthMetricsSnapshot": adapt_metrics,
                    "interventionEffect": adapt_effect, "monetaryFactor": adapt_monetary,
                    "timeEfficiency": adapt_time, "serviceInteractionType": adapt_interaction_type,
                    "specialistInvolved": adapt_specialist
                })
                chat_history.append({"role": "model", "parts": [{"text": adapt_msg}]})

            else: # Rohan adheres
                rohan_adherence, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist = generate_llm_response("Rohan", f"adhere to exercise plan. Current state: {CURRENT_HEALTH_METRICS}", CURRENT_HEALTH_METRICS, chat_history, journey_data)
                journey_data.append({
                    "type": "message", "sender": "Rohan", "timestamp": (current_date + timedelta(minutes=random.randint(30, 60))).strftime("%Y-%m-%d %H:%M"),
                    "content": rohan_adherence, "pillar": rohan_pillar, "relatedTo": "Exercise adherence",
                    "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                    "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                    "timeEfficiency": rohan_time, "serviceInteractionType": rohan_interaction_type,
                    "specialistInvolved": rohan_specialist
                })
                chat_history.append({"role": "user", "parts": [{"text": rohan_adherence}]})
            
            # Simulate slight metric changes from exercise
            CURRENT_HEALTH_METRICS["HRV"] += random.randint(0, 3)
            CURRENT_HEALTH_METRICS["RecoveryScore"] += random.randint(0, 5)
            CURRENT_HEALTH_METRICS["RestingHR"] -= random.randint(0, 1)

        # --- Travel (1 week out of 4) ---
        if week % 4 == 0 and week > 0: # Simulate travel every 4th week after initial onboarding
            travel_start_date = current_date + timedelta(days=random.randint(1, 3))
            
            # Pre-travel protocol
            msg_context = f"prepare travel protocol for upcoming trip. Current state: {CURRENT_HEALTH_METRICS}"
            msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist = generate_llm_response("Advik", msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": "Advik", "timestamp": travel_start_date.strftime("%Y-%m-%d %H:%M"),
                "content": msg, "pillar": pillar, "relatedTo": "Travel",
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                "specialistInvolved": specialist
            })
            chat_history.append({"role": "model", "parts": [{"text": msg}]})

            msg_context = f"confirm travel logistics for upcoming trip. Current state: {CURRENT_HEALTH_METRICS}"
            msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist = generate_llm_response("Ruby", msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": "Ruby", "timestamp": (travel_start_date + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M"),
                "content": msg, "pillar": pillar, "relatedTo": "Travel",
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                "specialistInvolved": specialist
            })
            chat_history.append({"role": "model", "parts": [{"text": msg}]})
            
            journey_data.append({
                "type": "event", "eventId": f"travel_start_week_{week}", "timestamp": travel_start_date.strftime("%Y-%m-%d %H:%M"),
                "description": f"Rohan travels for business (Week {week})", "details": "Jet lag protocol, in-flight mobility, nutrition adjustments.",
                "decisionRationale": "Proactive mitigation of travel stress on health goals, maximizing performance during demanding trips.",
                "healthMetricsSnapshot": CURRENT_HEALTH_METRICS.copy(), "interventionEffect": "Potential for jet lag/fatigue.",
                "monetaryFactor": "Business travel cost, focus on health investment ROI.", "timeEfficiency": "Optimized for busy travel schedule.",
                "serviceInteractionType": "travel_event", "specialistInvolved": "Advik, Ruby"
            })
            
            # Simulate post-travel check-in
            post_travel_date = travel_start_date + timedelta(days=7)
            msg_context = f"post-travel recovery check-in. Current state: {CURRENT_HEALTH_METRICS}"
            msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist = generate_llm_response("Advik", msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": "Advik", "timestamp": post_travel_date.strftime("%Y-%m-%d %H:%M"),
                "content": msg, "pillar": pillar, "relatedTo": "Post-travel recovery",
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                "specialistInvolved": specialist
            })
            chat_history.append({"role": "model", "parts": [{"text": msg}]})
            
            # Simulate negative metric impact from travel
            CURRENT_HEALTH_METRICS["HRV"] -= random.randint(0, 5)
            CURRENT_HEALTH_METRICS["RecoveryScore"] -= random.randint(0, 10)
            CURRENT_HEALTH_METRICS["DeepSleep"] -= random.randint(0, 15)

        # --- Member-Initiated Queries (Up to 5 per week on average) ---
        if random.random() < 0.7: # Simulate Rohan asking questions
            num_questions = random.randint(1, 3) # Simulate 1-3 questions per week
            for _ in range(num_questions):
                query_topics = ["poor digestion", "stress", "sleep", "HRV", "cognitive function", "new product", "alternative exercise", "monetary concern", "time constraint"]
                chosen_topic = random.choice(query_topics)
                
                rohan_query, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist = generate_llm_response("Rohan", f"ask about {chosen_topic}. Current state: {CURRENT_HEALTH_METRICS}", CURRENT_HEALTH_METRICS, chat_history, journey_data)
                journey_data.append({
                    "type": "message", "sender": "Rohan", "timestamp": (current_date + timedelta(hours=random.randint(1, 24))).strftime("%Y-%m-%d %H:%M"),
                    "content": rohan_query, "pillar": rohan_pillar, "relatedTo": chosen_topic,
                    "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                    "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                    "timeEfficiency": rohan_time, "serviceInteractionType": rohan_interaction_type,
                    "specialistInvolved": rohan_specialist
                })
                chat_history.append({"role": "user", "parts": [{"text": rohan_query}]})
                
                # Elyx team responds to query
                team_member = random.choice(list(ELYX_TEAM_PERSONAS.keys()))
                response_to_query, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist = generate_llm_response(team_member, f"respond to Rohan's query about {chosen_topic}. Current state: {CURRENT_HEALTH_METRICS}", CURRENT_HEALTH_METRICS, chat_history, journey_data)
                journey_data.append({
                    "type": "message", "sender": team_member, "timestamp": (current_date + timedelta(hours=random.randint(2, 48))).strftime("%Y-%m-%d %H:%M"),
                    "content": response_to_query, "pillar": pillar, "relatedTo": chosen_topic,
                    "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                    "interventionEffect": effect, "monetaryFactor": monetary,
                    "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                    "specialistInvolved": specialist
                })
                chat_history.append({"role": "model", "parts": [{"text": response_to_query}]})
                
                # Simulate metric changes based on interventions/deviations (simplified)
                if "stress" in chosen_topic:
                    CURRENT_HEALTH_METRICS["HRV"] += random.randint(-3, 3)
                if "sleep" in chosen_topic:
                    CURRENT_HEALTH_METRICS["DeepSleep"] += random.randint(-5, 5)
                if "exercise" in chosen_topic:
                    CURRENT_HEALTH_METRICS["RecoveryScore"] += random.randint(-3, 3)

        # --- Simulate specific events/concerns over time ---
        if week == 5: # Simulate initial back pain flare-up
            msg_context = "suggest couch stretch for back pain"
            msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist = generate_llm_response("Rachel", msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": "Rachel", "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "content": msg, "pillar": pillar, "relatedTo": "Back pain",
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                "specialistInvolved": specialist
            })
            chat_history.append({"role": "model", "parts": [{"text": msg}]})
            journey_data.append({
                "type": "event", "eventId": "back_pain_intervention", "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "description": "Back pain intervention (couch stretch)", "details": "Addressing Rohan's reported lower back pain with targeted mobility.",
                "decisionRationale": rationale, "healthMetricsSnapshot": CURRENT_HEALTH_METRICS.copy(),
                "interventionEffect": "Initial relief, focus on long-term mobility.",
                "monetaryFactor": "No direct cost, time-efficient.", "timeEfficiency": "2-minute routine.",
                "serviceInteractionType": "intervention_event", "specialistInvolved": "Rachel"
            })
            CURRENT_HEALTH_METRICS["BackPain"] = "mild" # Simulate slight improvement

        if week == 10: # Simulate a major illness setback
            msg_context = "initiate sick day protocol due to viral infection"
            msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist = generate_llm_response("Dr. Warren", msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": "Dr. Warren", "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "content": msg, "pillar": pillar, "relatedTo": "Illness",
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                "specialistInvolved": specialist
            })
            chat_history.append({"role": "model", "parts": [{"text": msg}]})
            journey_data.append({
                "type": "event", "eventId": "illness_setback", "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "description": "Major Illness Setback (Viral Infection)", "details": "Elyx Sick Day Protocol initiated, board meeting postponed.",
                "decisionRationale": rationale, "healthMetricsSnapshot": CURRENT_HEALTH_METRICS.copy(),
                "interventionEffect": "Severe fatigue, recovery score dropped significantly.",
                "monetaryFactor": "Potential business cost due to postponed meeting, but avoids higher future medical costs.",
                "timeEfficiency": "Focus on radical rest, minimal time for other activities.",
                "serviceInteractionType": "health_crisis_event", "specialistInvolved": "Dr. Warren, Ruby"
            })
            CURRENT_HEALTH_METRICS["RecoveryScore"] = 10 # Simulate very low recovery
            CURRENT_HEALTH_METRICS["POTS_symptoms"] = "severe" # Worsen POTS

        if week == 15: # Simulate a new health investment (piano)
            msg_context = "add weekly piano practice as trackable goal"
            msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist = generate_llm_response("Neel", msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": "Neel", "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "content": msg, "pillar": pillar, "relatedTo": "New Goal",
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                "specialistInvolved": specialist
            })
            chat_history.append({"role": "model", "parts": [{"text": msg}]})
            journey_data.append({
                "type": "event", "eventId": "piano_goal_added", "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "description": "Weekly Piano Practice Added to Plan", "details": "Cognitive longevity and stress management investment.",
                "decisionRationale": rationale, "healthMetricsSnapshot": CURRENT_HEALTH_METRICS.copy(),
                "interventionEffect": "Expected long-term cognitive and stress resilience benefits.",
                "monetaryFactor": "Initial cost of piano/lessons, long-term non-monetary benefit.",
                "timeEfficiency": "Integrated into weekly routine, flexible scheduling.",
                "serviceInteractionType": "goal_setting_event", "specialistInvolved": "Neel"
            })
        
        # Simulate general metric fluctuations
        CURRENT_HEALTH_METRICS["HRV"] = max(30, CURRENT_HEALTH_METRICS["HRV"] + random.randint(-2, 4))
        CURRENT_HEALTH_METRICS["RestingHR"] = max(50, CURRENT_HEALTH_METRICS["RestingHR"] + random.randint(-1, 1))
        CURRENT_HEALTH_METRICS["GlucoseAvg"] = random.randint(90, 100)
        CURRENT_HEALTH_METRICS["RecoveryScore"] = max(20, min(95, CURRENT_HEALTH_METRICS["RecoveryScore"] + random.randint(-5, 8)))
        CURRENT_HEALTH_METRICS["DeepSleep"] = max(30, min(120, CURRENT_HEALTH_METRICS["DeepSleep"] + random.randint(-10, 10)))
        
        if CURRENT_HEALTH_METRICS["POTS_symptoms"] == "severe" and random.random() < 0.3:
            CURRENT_HEALTH_METRICS["POTS_symptoms"] = "moderate"
        elif CURRENT_HEALTH_METRICS["POTS_symptoms"] == "moderate" and random.random() < 0.3:
            CURRENT_HEALTH_METRICS["POTS_symptoms"] = "mild"
        
        if CURRENT_HEALTH_METRICS["BackPain"] == "severe" and random.random() < 0.3:
            CURRENT_HEALTH_METRICS["BackPain"] = "moderate"
        elif CURRENT_HEALTH_METRICS["BackPain"] == "moderate" and random.random() < 0.3:
            CURRENT_HEALTH_METRICS["BackPain"] = "mild"

    return jsonify(journey_data) # Return as JSON response

@app.route('/api/explain-decision', methods=['POST'])
def api_explain_decision():
    data = request.json
    query = data.get('query')
    journey_data_context = data.get('journeyData', []) # Get the full journey data as context
    
    if not query:
        return jsonify({"error": "Query is required."}), 400
    
    # Use the generate_llm_response function to get the explanation
    # Pass Rohan's profile and the full journey data as context to simulate a smarter response
    explanation, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist = generate_llm_response(
        role="Elyx AI Concierge", # Simulate AI persona for explanation
        prompt_context=query,
        current_metrics=CURRENT_HEALTH_METRICS, # Pass current metrics
        chat_history=[], # Not directly used for this specific explanation, but can be
        journey_data_so_far=journey_data_context # Pass the full journey for context
    )
    
    # Format the explanation to include the new fields
    formatted_explanation = f"{explanation}\n\n"
    if rationale:
        formatted_explanation += f"**Rationale:** {rationale}\n"
    if pillar:
        formatted_explanation += f"**Pillar Impact:** {pillar}\n"
    if effect:
        formatted_explanation += f"**Observed Effect:** {effect}\n"
    if monetary:
        formatted_explanation += f"**Monetary Factor:** {monetary}\n"
    if time_eff:
        formatted_explanation += f"**Time Efficiency:** {time_eff}\n"
    if specialist:
        formatted_explanation += f"**Specialist Involved:** {specialist}\n"
    if metrics_snap:
        formatted_explanation += f"**Metrics at Time:** {json.dumps(metrics_snap, indent=2)}\n"

    return jsonify({"explanation": formatted_explanation})

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
