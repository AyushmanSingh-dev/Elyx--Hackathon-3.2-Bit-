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
            response_text = random.choice([
                "Ruby, I'm feeling overwhelmed with my ad-hoc health routine. High work stress, and my Garmin HR seems off even on rest days. I need a proper, coordinated plan. My current supplement list is attached.",
                "My current health efforts feel disjointed. Can we establish a more cohesive plan? My wearable data feels inconsistent.",
                "I'm ready for a structured health approach. My current stress levels are high, and my Garmin data isn't reflecting recovery. Attached is my supplement list.",
                "The current health approach isn't sustainable for my schedule. I need a streamlined, effective plan. My metrics are concerning."
            ])
        elif "medical records" in prompt_lower:
            response_text = random.choice([
                "Acknowledged. How long will that take? And what about my fitness goals?",
                "Understood. What's the typical turnaround for record consolidation? Also, let's discuss optimizing my workouts.",
                "Okay, I'll ensure Sarah assists with records. Separately, I'm keen to refine my fitness strategy.",
                "Records are in progress. Meanwhile, I'm eager to discuss my exercise regimen and how to maximize its impact."
            ])
        elif "movement assessment" in prompt_lower:
            response_text = random.choice([
                "Understood. I'm also thinking about my stress levels. Any immediate tips?",
                "A movement assessment makes sense. On another note, I've been feeling more stressed. Any quick stress relief techniques?",
                "Good. While we schedule that, what are some immediate strategies for managing cognitive load?",
                "I'm on board for the assessment. What are some rapid techniques for mental clarity and stress reduction?"
            ])
        elif "couch stretch" in prompt_lower and "helped" in prompt_lower:
            response_text = random.choice([
                "The couch stretch helped a bit! Also, for stress, any immediate dietary tips? I struggle with consistent energy.",
                "That stretch provided some relief. What about nutritional strategies for managing stress and energy dips?",
                "Good call on the stretch. What are some quick dietary hacks for energy and stress during busy days?",
                "The stretch was beneficial. Now, can we address nutritional support for my energy levels and stress resilience?"
            ])
        elif "diagnostic panel" in prompt_lower:
            response_text = random.choice([
                "Yes, next Tuesday works. Confirmed. I'm keen to see the numbers, though I'm always a bit skeptical until I see tangible results.",
                "Tuesday works for diagnostics. I'm interested in the data, but I need to see actionable insights, not just numbers.",
                "Confirmed for diagnostics next week. I value data, but ultimately, it's about practical improvements. What should I expect?",
                "I've scheduled the diagnostic panel for Tuesday. What are the key metrics we're tracking, and how will they inform my plan?"
            ])
        elif "apo b" in prompt_lower or "apob" in prompt_lower:
            response_text = random.choice([
                "What's the plan for the ApoB? I want clear, actionable steps. Monetary factors are important too.",
                "Elevated ApoB is a concern. What are the most effective, efficient interventions? Please consider cost-effectiveness.",
                "Understood on ApoB. Let's prioritize interventions. Are there any cost-efficient alternatives for dietary changes or supplements?",
                "Given the ApoB results, what's the immediate, high-impact strategy? I need to know the financial implications and time commitment."
            ])
        elif "jet lag" in prompt_lower or "travel" in prompt_lower:
            response_text = random.choice([
                "This sounds critical. I need a clear, minute-by-minute guide for my upcoming trip. How can we make it time-efficient?",
                "My travel schedule is intense. What's the most time-efficient jet lag protocol? I need practical advice for on-the-go.",
                "Preparing for travel. What are the key strategies to minimize disruption to my health, especially given my limited time?",
                "Upcoming international travel. What specific protocols can I implement to mitigate jet lag and maintain my routine effectively?"
            ])
        elif "not feeling great" in prompt_lower or "illness" in prompt_lower:
            response_text = random.choice([
                "This is a major setback. The board meeting is critical. What's the immediate plan? I need to maximize my recovery output.",
                "Feeling unwell. This is impacting my ability to perform. What's the fastest way to recover without compromising long-term health?",
                "I'm experiencing symptoms. What's the Elyx protocol for this? I need to get back on track efficiently.",
                "I'm feeling a dip in health. What's the recommended course of action to minimize downtime and prevent further impact on my schedule?"
            ])
        elif "recovery" in prompt_lower and "green" in prompt_lower:
            response_text = random.choice([
                "Good. I feel it. Let's get back to the plan.",
                "Excellent. I'm seeing the positive effects. What's the next optimization?",
                "Great news on recovery. I'm ready for the next challenge.",
                "My recovery metrics are strong. What advanced strategies can we implement now to push further?"
            ])
        elif "piano" in prompt_lower:
            response_text = random.choice([
                "I've always wanted to learn piano. From a health and performance perspective, is this a worthwhile use of my time?",
                "Considering learning piano. What are the cognitive benefits, and how does it fit into my overall health investment strategy?",
                "Is piano a good investment for cognitive longevity and stress? What's the commitment like?",
                "I'm exploring new hobbies. Is learning piano a recommended activity for long-term brain health and stress reduction?"
            ])
        elif "poor digestion" in prompt_lower:
            response_text = random.choice([
                "I'm experiencing poor digestion. Any suggestions that are easy to integrate into my busy schedule?",
                "What are some practical dietary adjustments for improving digestion, considering my travel and time constraints?",
                "My digestion feels off. Are there any simple, effective strategies I can implement immediately?",
                "Can you provide quick, actionable tips for better digestion that won't disrupt my routine?"
            ])
        elif "monetary" in prompt_lower or "cost" in prompt_lower or "expensive" in prompt_lower:
            response_text = random.choice([
                "I'm looking for cost-effective options. Can you suggest alternatives for X?",
                "How can we optimize for value without compromising results? Are there budget-friendly alternatives?",
                "What's the ROI on this recommendation, and are there less expensive but still effective options?",
                "I need to balance health investments with financial prudence. What are some high-impact, low-cost recommendations?"
            ])
        elif "time" in prompt_lower or "busy" in prompt_lower or "quick" in prompt_lower:
            response_text = random.choice([
                "I have limited time. What's the most time-efficient way to achieve Y?",
                "My schedule is packed. Can we focus on high-impact, low-time-commitment interventions?",
                "What are some quick wins for health that fit into a demanding schedule?",
                "I need strategies that deliver maximum health output for minimal time investment. Any suggestions?"
            ])
        else:
            response_text = random.choice([
                "Understood. Thanks for the update. What's next?",
                "Okay, I'll look into that. Is there a more efficient way?",
                "Good. Let's keep pushing that number down. Any tips for integrating this seamlessly?",
                "I'm starting to look for a piano. I see this as part of my health investment.",
                "I'm curious about optimizing my current routine. Any thoughts on that?",
                "What's the latest insight from my data? Any new areas of focus?"
            ])
    # --- Elyx Team Member Responses (Prioritizing, Value-Driven, Adaptable) ---
    else:
        service_interaction_type = "proactive check-in" if "check-in" in prompt_lower else "intervention update"
        if "initial submission" in prompt_lower and role == "Ruby":
            response_text = random.choice([
                "Hi Rohan, thank you for sharing this. We understand. Our goal is to bring coordination to your health. I'm flagging your concerns for Dr. Warren to review immediately. We're here to make this seamless for you.",
                "Welcome, Rohan! We've received your initial details. Your concerns about stress and Garmin data are noted. We're initiating a comprehensive review with Dr. Warren to build your coordinated plan.",
                "Rohan, great to have you onboard! We're already working to consolidate your health data and address your initial concerns about routine and stress. Expect a prompt follow-up from Dr. Warren.",
                "Elyx is here to streamline your health journey, Rohan. Your initial input is valuable; we're now mobilizing the team to craft your personalized, efficient plan."
            ])
            decision_rationale = "Prioritizing Rohan's core concern of 'ad-hoc health' by initiating a coordinated clinical review, maximizing early engagement output."
            time_efficiency = "Immediate flagging for quick initial response."
        elif "medical records" in prompt_lower and role == "Dr. Warren":
            response_text = random.choice([
                "Rohan, Dr. Warren here. I've reviewed your initial submission. The symptoms and data strongly suggest autonomic dysfunction (Pillar 1). To proceed, we must consolidate your complete medical records. This is non-negotiable for safety. Ruby will manage the process.",
                "Dr. Warren. Your initial data points towards autonomic imbalance. Full medical records are vital for a safe, effective strategy. Ruby will handle the logistics.",
                "This is Dr. Warren. To build a robust plan for your autonomic health, complete medical records are essential. Ruby will streamline this process for you.",
                "For precise clinical strategy, Rohan, comprehensive medical records are a foundational requirement. This ensures we maximize safety and avoid redundant efforts. Ruby will manage the collection."
            ])
            decision_rationale = "To establish a clinical-grade strategy, ensure safety, and avoid redundant testing by consolidating complete medical history. This is a foundational step for maximizing long-term health output and preventing future costly errors."
            pillar_impact = "Pillar 1 (Autonomic Health)"
        elif "medical records" in prompt_lower and role == "Ruby":
            response_text = random.choice([
                "The timeline can vary depending on clinics' response speed, but we will manage the entire process. We typically aim for records within 2-3 weeks. We'll provide daily updates to keep you in the loop, saving your time.",
                "We're on it! Consolidating your records is our priority. We'll handle all communication with clinics and keep you updated every step of the way, minimizing your effort.",
                "Don't worry about the record collection. We'll streamline the process, aiming for completion within 2-3 weeks, and notify you as soon as they're ready. Your time is valuable.",
                "Sarah has been briefed on the medical record collection. We anticipate completion within 2-3 weeks, and you'll receive real-time updates, ensuring minimal disruption to your schedule."
            ])
            time_efficiency = "Elyx team handles logistics to save Rohan's time."
        elif "fitness goals" in prompt_lower and role == "Advik":
            response_text = random.choice([
                "Rohan, Advik here. A good first step is a comprehensive movement assessment to understand your baseline and identify any imbalances. Ruby can help schedule this with Rachel. This will inform your personalized exercise plan, maximizing your workout output.",
                "Advik. To optimize your workouts and prevent injury, a baseline movement assessment is key. Ruby can coordinate with Rachel for this. It's a data-driven approach to maximize your fitness investment.",
                "For your fitness goals, Advik recommends a detailed movement assessment. This will ensure your personalized plan is efficient and effective, fitting your demanding schedule. Ruby will assist with scheduling.",
                "To truly elevate your fitness, Rohan, Advik advises a foundational movement assessment. This data will allow Rachel to craft a highly efficient, personalized exercise program. Ruby will manage the scheduling."
            ])
            decision_rationale = "To establish a data-driven baseline for personalized exercise programming, optimizing for Rohan's time constraints and avoiding injury. This maximizes efficiency and adherence for long-term gains."
            pillar_impact = "Pillar 4 (Structural Health)"
        elif "stress levels" in prompt_lower and role == "Carla":
            response_text = random.choice([
                "Rohan, Carla here. For immediate stress support, focus on consistent hydration and mindful eating. Avoiding processed snacks can also help. These are simple, low-cost dietary adjustments that integrate easily.",
                "Carla. To combat stress and energy dips, prioritize hydration and mindful eating. Small, consistent efforts here yield significant benefits without major lifestyle overhauls or cost.",
                "For quick stress relief, Carla advises focusing on hydration and making conscious food choices. These are fundamental, zero-cost practices that can make an immediate difference.",
                "Carla suggests immediate, low-effort nutritional tweaks for stress: consistent hydration and mindful eating. These foundational habits are highly impactful and seamlessly integrate into your day."
            ])
            pillar_impact = "Pillar 3 (Fuel), Pillar 5 (Stress Resilience)"
            monetary_factor = "Low-cost/no-cost dietary adjustments."
            time_efficiency = "Easy to integrate, minimal time commitment."
        elif "couch stretch" in prompt_lower and role == "Rachel":
            response_text = random.choice([
                "Hi Rohan, Rachel here. Given your frequent travel and desk work, let's try a simple 2-minute 'couch stretch' for your lower back pain. It targets hip flexor tightness. Try it and let me know if it helps. This is a quick, effective intervention.",
                "Rachel. For your lower back, the 2-minute couch stretch is highly effective for hip flexor tightness from sitting. Integrate it into your pre-flight or post-desk routine for quick relief.",
                "Rohan, Rachel here. A quick win for your lower back is the couch stretch. It's only 2 minutes and directly addresses travel-induced tightness. Give it a try; it's a high-impact, low-time investment.",
                "Rachel suggests the 2-minute couch stretch for your lower back. It's a targeted, time-efficient solution for hip flexor tightness common with travel and desk work, aiming for immediate comfort and long-term mobility."
            ])
            decision_rationale = "To address Rohan's reported lower back pain, a common issue from prolonged sitting during travel, with a time-efficient, non-invasive intervention that integrates into his daily routine for maximum relief."
            pillar_impact = "Pillar 4 (Structural Health)"
            time_efficiency = "2-minute, quick intervention."
        elif "q1 diagnostic panel" in prompt_lower and role == "Ruby":
            response_text = random.choice([
                "Rohan, it's time to schedule your Q1 diagnostic panel. This comprehensive test will give us a baseline for your metabolic and hormonal health. We can arrange a phlebotomist to come to your office. Does next Tuesday morning work? This maximizes your convenience.",
                "Your quarterly diagnostic is due. This panel is key to tracking your metabolic health. We can send a phlebotomist to your office for ultimate convenience. Let us know your availability next week.",
                "Time for your Q1 diagnostic panel! This essential data helps us fine-tune your plan. We can schedule a phlebotomist at your office to save your valuable time. What day next week works best?",
                "Ruby here. Your Q1 diagnostic panel is ready for scheduling. To maximize your time efficiency, we can arrange a phlebotomist to visit your office. Please confirm your availability next Tuesday."
            ])
            decision_rationale = "Full diagnostic test panel every three months is a core program requirement to track progress on biomarkers and identify new areas for intervention. This maximizes long-term health output by providing critical data for personalized adjustments, minimizing future health costs."
            pillar_impact = "Pillar 1 (Autonomic), Pillar 3 (Fuel), Pillar 5 (Stress Resilience)"
            time_efficiency = "Phlebotomist to office for convenience."
        elif "apo b" in prompt_lower and role == "Dr. Warren":
            response_text = random.choice([
                "Rohan, your ApoB is 105 mg/dL. This is elevated and a primary focus for long-term heart disease risk reduction, aligning with your top health goal. Carla will lead dietary interventions (reducing saturated fat, increasing fiber), and Rachel's exercise plan will be critical. We will aggressively target this with lifestyle changes and re-test in Q2.",
                "Dr. Warren. Your ApoB at 105 mg/dL is a priority. We're launching a targeted intervention led by Carla (diet) and Rachel (exercise) to reduce your cardiovascular risk. This is a crucial investment in your longevity, with re-testing planned.",
                "Your Q1 diagnostics show elevated ApoB. This is a serious indicator for heart health, directly impacting your primary goal. Our strategy involves aggressive, integrated lifestyle changes via Carla and Rachel, aiming for significant reduction by Q2. This is a high-ROI health investment.",
                "Dr. Warren: Elevated ApoB is our immediate focus for your cardiovascular health. Carla and Rachel will implement aggressive, integrated lifestyle interventions. This is a critical, cost-effective step towards your longevity goals, with re-evaluation in Q2."
            ])
            decision_rationale = "Elevated ApoB is a serious cardiovascular risk factor based on Q1 diagnostics. The intervention prioritizes Rohan's top health goal, using integrated lifestyle changes for maximum impact and long-term investment. This approach is more sustainable than medication alone and is a cost-effective preventative measure."
            pillar_impact = "Pillar 3 (Fuel), Pillar 4 (Structural), Pillar 1 (Autonomic)"
            monetary_factor = "Cost-effective preventative measure."
        elif "travel protocol" in prompt_lower and role == "Advik":
            response_text = random.choice([
                "For your Tokyo trip, we'll build a precise light exposure and avoidance schedule to shift your circadian rhythm, and Rachel will find a suitable gym near your hotel. This proactive approach aims to minimize jet lag and maintain your health routine, maximizing your performance during demanding travel.",
                "Advik. To ensure your demanding travel doesn't derail your progress, we're implementing a bespoke travel protocol. This includes circadian rhythm adjustment via light exposure and pre-vetted exercise options near your hotel, maximizing your efficiency on the road.",
                "Your upcoming travel is an opportunity to optimize your resilience. Advik will provide a detailed jet lag protocol and Rachel will identify convenient workout spots, ensuring your health remains a priority even with time constraints.",
                "Advik here. For your upcoming travel, we've designed a comprehensive protocol to combat jet lag and maintain your routine. This includes personalized light exposure plans and vetted local gym options, ensuring peak performance on your trip."
            ])
            decision_rationale = "To proactively mitigate the known impact of international travel on Rohan's POTS and overall performance, ensuring his demanding work schedule doesn't derail health progress. Focus on time-efficient, integrated solutions that fit his travel lifestyle, maximizing his output during business trips."
            pillar_impact = "Pillar 1 (Autonomic), Pillar 2 (Sleep), Pillar 4 (Structural), Pillar 5 (Stress Resilience)"
            time_efficiency = "Precise schedule for jet lag, gym finding for efficiency."
        elif "illness" in prompt_lower and role == "Dr. Warren":
            response_text = random.choice([
                "Rohan, the biotelemetry strongly suggests a viral infection. We are initiating the Elyx Sick Day Protocol immediately. You must postpone your board meeting. Your cognitive function will be severely impaired, and you risk a much longer recovery if you push through. Ruby will manage rescheduling.",
                "Dr. Warren here. Your current biometrics indicate a significant viral load. It's critical you engage the Elyx Sick Day Protocol and postpone your meeting. Pushing through will severely extend recovery and compromise your long-term health investment. Ruby will assist.",
                "This is Dr. Warren. Immediate rest and the Elyx Sick Day Protocol are paramount. Your current state demands full recovery focus; attempting the board meeting will be counterproductive and costly in the long run. Ruby is on standby for logistics.",
                "Dr. Warren: Biotelemetry confirms a viral infection. We're activating the Elyx Sick Day Protocol. Postponing your meeting is non-negotiable; pushing now will severely extend your recovery and incur greater long-term costs. Ruby will handle the rescheduling."
            ])
            decision_rationale = "Prioritizing immediate health stabilization and long-term recovery over short-term business commitments, as pushing through illness risks severe setbacks and prolonged recovery, ultimately impacting long-term performance and health investment. This maximizes long-term output and avoids higher future medical costs."
            pillar_impact = "All Pillars (Acute Health Crisis)"
            monetary_factor = "Avoids higher future medical costs."
        elif "piano" in prompt_lower and role == "Neel":
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
        elif "deviate from exercise" in prompt_lower:
            response_text = random.choice([
                "Understood, Rohan. It's common for plans to need adjustments. Let's adapt. We can explore shorter, more flexible routines for your travel weeks, or bodyweight alternatives that require no equipment, maximizing adherence even when time is tight. Your health journey is dynamic.",
                "Rachel/Advik here. We understand adherence can fluctuate. Instead of skipping, let's pivot to a quick 15-minute bodyweight circuit or a targeted mobility flow. The goal is consistency and adaptability, maximizing your output even on challenging days.",
                "It's okay to deviate; the key is quick adaptation. We'll revise your plan to include more flexible, time-efficient options that fit your dynamic schedule, ensuring you maintain momentum without feeling overwhelmed. This maximizes long-term adherence.",
                "We anticipated dynamic adherence, Rohan. Rachel and Advik will provide adaptable, time-efficient exercise alternatives, like hotel room workouts, ensuring your progress continues uninterrupted, even with unforeseen schedule changes."
            ])
            decision_rationale = "Adapting to Rohan's dynamic schedule and adherence patterns to ensure continued progress, focusing on flexible and time-efficient alternatives to maximize health output without feeling forced."
            monetary_factor = "Suggests bodyweight alternatives (cost-effective)."
            time_efficiency = "Shorter, more flexible routines."
        elif "monetary concern" in prompt_lower:
            response_text = random.choice([
                "We hear your concern about monetary factors. We always strive to provide cost-effective alternatives and ensure every recommendation is a justified investment in your long-term health. For example, simple dietary changes can have a huge impact on ApoB without high cost.",
                "Elyx is about maximizing health ROI. We'll always present cost-effective alternatives and clearly articulate the long-term value of any investment, ensuring your plan is sustainable and delivers maximum output within your budget.",
                "Your financial considerations are important. We focus on high-impact, low-cost interventions where possible, and for any investment, we'll outline the long-term health benefits and how it prevents future, higher costs.",
                "We prioritize value, Rohan. For every recommendation, we consider cost-effectiveness and demonstrate its long-term health ROI, ensuring your investments are prudent and maximize your healthy years."
            ])
            decision_rationale = "Prioritizing Rohan's financial considerations by offering cost-effective alternatives and justifying investments as long-term health benefits, ensuring the plan is sustainable and maximizes value."
            monetary_factor = "Emphasizes cost-effectiveness and justified investment."
        elif "time" in prompt_lower or "busy" in prompt_lower or "quick" in prompt_lower:
            response_text = random.choice([
                "We understand your time constraints. Our goal is to seamlessly integrate health into your busy life. We can focus on micro-interventions, like 5-minute mobility breaks or strategic meal prepping with Javier, to maximize health output with minimal time investment.",
                "Your time is precious. We design interventions for maximum impact in minimal time. Think strategic 10-minute bursts, or leveraging your cook for efficient meal prep, turning health into an integrated lifestyle, not a chore.",
                "We specialize in optimizing for busy schedules. We'll streamline your health activities, focusing on high-leverage actions that fit into your existing routine, ensuring consistent progress without adding burden.",
                "Elyx excels at time-optimization. We'll identify high-impact, low-time interventions and integrate them seamlessly into your demanding schedule, maximizing your health benefits without adding friction."
            ])
            decision_rationale = "Adapting the plan to Rohan's severe time constraints by focusing on micro-interventions and efficient strategies, ensuring health activities are integrated seamlessly and maximize output per minute invested."
            time_efficiency = "Focus on micro-interventions and strategic planning."
        else:
            response_text = random.choice([
                f"Hi Rohan, {role} here. We're continuously optimizing your plan based on your feedback and data to maximize your health output. How are things going with your current priorities?",
                f"Understood. We'll integrate this into your personalized plan to maximize your health output, considering your time and monetary factors. Thanks for the feedback.",
                f"That's a great point, {ELYX_TEAM_PERSONAS[role]['role']} will look into that for you, ensuring it aligns with your priorities and lifestyle.",
                f"We're always looking for ways to make your health journey more seamless and impactful, turning medical procedures into lifestyle habits. What's on your mind?",
                f"Just checking in, Rohan. How are you feeling about your current progress and any new challenges you're facing? {role} is here to support.",
                f"We've noted your recent activity. {role} is reviewing your latest data for potential optimizations. Anything specific you'd like to discuss?"
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
```
You're right, the message section still generating the same content is frustrating, especially with the updates I've made to increase randomness.

The issue isn't that the backend *can't* generate different random sequences; it's that the **frontend might not be triggering a *new* generation every time, or the randomness in the backend's `generate_llm_response` for specific scenarios isn't diverse enough to be immediately noticeable.**

To truly test if the backend is generating varied data, and to give you control, I'm going to add a **"Refresh Journey" button to the frontend**. When clicked, this button will explicitly make a new request to your backend's `/api/generate-journey` endpoint, forcing a fresh 8-month simulation.

---

## Updated Frontend: `index.html` (with "Refresh Journey" Button) 🌐

I've added a "Refresh Journey" button to the "Messages" and "Journey" sections. Clicking this button will trigger a new `fetchJourneyData` call, which in turn hits your backend's `/api/generate-journey` endpoint. This will allow you to see if the backend is indeed producing different data on subsequent requests.


```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Elyx Health Journey</title>

    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Inter Font -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
    <!-- Chart.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
        /* Global styles and custom spinner for loading indicators */
        body {
            font-family: 'Inter', sans-serif;
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        .spinner {
            border: 4px solid rgba(0, 0, 0, 0.1);
            border-left-color: #6366f1; /* Indigo 500 */
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>

    <!-- React and ReactDOM CDNs -->
    <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>

    <!-- Firebase CDNs (for authentication). Ensure these are loaded before your app script. -->
    <script src="https://www.gstatic.com/firebasejs/11.6.1/firebase-app.js"></script>
    <script src="https://www.gstatic.com/firebasejs/11.6.1/firebase-auth.js"></script>
    <!-- Add other Firebase services if needed, e.g., Firestore: -->
    <!-- <script src="https://www.gstatic.com/firebasejs/11.6.1/firebase-firestore.js"></script> -->

    <script type="module">
        // Access React from global scope
        const { useState, useEffect, useCallback, useRef } = window.React;
        const ReactDOM = window.ReactDOM;
        const Chart = window.Chart; // Access Chart.js from global scope

        // --- NavItem Component (defined locally within this script) ---
        const NavItem = ({ label, section, activeSection, setActiveSection }) => {
            const React = window.React; // Access React from global scope
            return (
                React.createElement('button', {
                    className: `px-4 py-2 rounded-md text-white font-medium transition-colors duration-300 ${activeSection === section ? 'bg-indigo-600 shadow-lg' : 'hover:bg-indigo-700'}`,
                    onClick: () => setActiveSection(section)
                }, label)
            );
        };

        // --- Sample Journey Data (Embedded) ---
        // This data is now defined directly within this script, no import needed.
        const sampleJourneyData = [
            { type: "message", sender: "Rohan", timestamp: "2025-08-01 10:00", content: "Ruby, I'm feeling overwhelmed with my ad-hoc health routine. High work stress, and my Garmin HR seems off even on rest days. I need a proper, coordinated plan. My current supplement list is attached.", pillar: null, relatedTo: null },
            { type: "message", sender: "Ruby", timestamp: "2025-08-01 10:05", content: "Hi Rohan, thank you for sharing this. We understand. Our goal is to bring coordination to your health. I'm flagging your concerns for Dr. Warren to review immediately. We're here to make this seamless for you.", pillar: null, relatedTo: "Rohan_Initial" },
            { type: "event", eventId: "onboarding_start", timestamp: "2025-08-01 10:00", description: "Member Onboarding Initiated", details: "Rohan shares medical history and goals." },
            { type: "message", sender: "Dr. Warren", timestamp: "2025-08-08 14:00", content: "Rohan, Dr. Warren here. I've reviewed your initial submission. The symptoms and data strongly suggest autonomic dysfunction (Pillar 1). To proceed, we must consolidate your complete medical records. This is non-negotiable for safety. Ruby will manage the process.", pillar: "Pillar 1", relatedTo: "Ruby_Welcome", decisionRationale: "To establish a clinical-grade strategy, ensure safety, and avoid redundant testing by consolidating complete medical history. This is a foundational step for maximizing long-term health output and preventing future costly errors." },
            { type: "message", sender: "Rohan", timestamp: "2025-08-08 14:05", content: "Acknowledged. How long will that take? And what about my fitness goals?", pillar: null, relatedTo: "DrWarren_Records" },
            { type: "message", sender: "Advik", timestamp: "2025-08-08 14:10", content: "Rohan, Advik here. A good first step is a comprehensive movement assessment to understand your baseline and identify any imbalances. Ruby can help schedule this with Rachel. This will inform your personalized exercise plan, maximizing your workout output.", pillar: "Pillar 4", relatedTo: "Rohan_Fitness", decisionRationale: "To establish a data-driven baseline for personalized exercise programming, optimizing for Rohan's time constraints and avoiding injury. This maximizes efficiency and adherence for long-term gains." },
            { type: "event", eventId: "records_requested", timestamp: "2025-08-08 14:00", description: "Comprehensive Medical Records Requested", details: "Critical for clinical strategy.", relatedToDecision: true },
            { type: "event", eventId: "movement_assessment_suggested", timestamp: "2025-08-08 14:10", description: "Initial Movement Assessment Suggested", details: "For personalized exercise plan.", relatedToDecision: true },
            { type: "message", sender: "Rachel", timestamp: "2025-08-15 09:00", content: "Hi Rohan, Rachel here. Given your frequent travel and desk work, let's try a simple 2-minute 'couch stretch' for your lower back pain. It targets hip flexor tightness. Try it and let me know if it helps. This is a quick, effective intervention.", pillar: "Pillar 4", relatedTo: "Rohan_Fitness", decisionRationale: "To address Rohan's reported lower back pain, a common issue from prolonged sitting during travel, with a time-efficient, non-invasive intervention that integrates into his daily routine for maximum relief." },
            { type: "message", sender: "Rohan", timestamp: "2025-08-15 09:10", content: "The couch stretch helped a bit! Also, for stress, any immediate dietary tips? I struggle with consistent energy.", pillar: null, relatedTo: "Rachel_Stretch" },
            { type: "message", sender: "Carla", timestamp: "2025-08-15 09:15", content: "Rohan, Carla here. Great to hear about the stretch! For immediate stress support, focus on consistent hydration and mindful eating during your meals, even small ones. Avoiding processed snacks can also help. These are simple, low-cost dietary adjustments that integrate easily.", pillar: "Pillar 3, Pillar 5", relatedTo: "Rohan_DietQuery" },
            { type: "event", eventId: "couch_stretch_introduced", timestamp: "2025-08-15 09:00", description: "Couch Stretch Introduced for Back Pain", details: "Targeting hip flexors.", relatedToDecision: true },
            { type: "message", sender: "Ruby", timestamp: "2025-08-22 11:00", content: "Rohan, it's time to schedule your Q1 diagnostic panel. This comprehensive test will give us a baseline for your metabolic and hormonal health. We can arrange a phlebotomist to come to your office. Does next Tuesday morning work? This maximizes your convenience.", pillar: "Pillar 1", relatedTo: null, decisionRationale: "Full diagnostic test panel every three months is a core program requirement to track progress on biomarkers and identify new areas for intervention. This maximizes long-term health output by providing critical data for personalized adjustments, minimizing future health costs." },
            { type: "message", sender: "Rohan", timestamp: "2025-08-22 11:05", content: "Yes, next Tuesday works. Confirmed. I'm keen to see the numbers, though I'm always a bit skeptical until I see tangible results.", pillar: null, relatedTo: "Ruby_DiagnosticSchedule" },
            { type: "event", eventId: "q1_diagnostic_scheduled", timestamp: "2025-08-22 11:00", description: "Q1 Diagnostic Panel Scheduled", details: "Comprehensive baseline tests.", relatedToDecision: true }
        ];

        // --- Main App Component ---
        function App() {
            const [activeSection, setActiveSection] = useState('dashboard');
            const [userId, setUserId] = useState('');
            const [isAuthReady, setIsAuthReady] = useState(false);
            const [decisionQuery, setDecisionQuery] = useState('');
            const [decisionResponse, setDecisionResponse] = useState('');
            const [isLoadingDecision, setIsLoadingDecision] = useState(false);
            const [journeyData, setJourneyData] = useState([]);
            const [isGeneratingConversation, setIsGeneratingConversation] = useState(true); // Initially true to show loading

            // Refs for Chart.js canvas elements
            const hrvChartRef = useRef(null);
            const apoBChartRef = useRef(null);
            const interactionChartRef = useRef(null);

            // IMPORTANT: Updated to your specific Render Backend URL
            const BACKEND_API_BASE_URL = "https://elyx-hackathon-3-2-bit.onrender.com"; 

            // Function to fetch the 8-month journey data from the backend
            const fetchJourneyData = useCallback(async () => {
                setIsGeneratingConversation(true);
                try {
                    const response = await fetch(`${BACKEND_API_BASE_URL}/api/generate-journey`, {
                        method: 'POST', // Use POST as the backend expects it
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({}) // Send empty body if no specific input is needed for generation
                    });
                    const data = await response.json();
                    if (response.ok) {
                        setJourneyData(data);
                    } else {
                        console.error("Error fetching journey data:", data.error || "Unknown error");
                        setJourneyData([]); // Clear data on error
                    }
                } catch (error) {
                    console.error("Network error fetching journey data:", error);
                    setJourneyData([]); // Clear data on error
                } finally {
                    setIsGeneratingConversation(false);
                }
            }, [BACKEND_API_BASE_URL]); // Depend on BACKEND_API_BASE_URL

            // Function to call the backend API for decision explanation
            const handleDecisionQuery = async () => {
                if (!decisionQuery.trim()) {
                    setDecisionResponse("Please enter a question about a decision.");
                    return;
                }

                setIsLoadingDecision(true);
                setDecisionResponse("Thinking...");

                try {
                    const response = await fetch(`${BACKEND_API_BASE_URL}/api/explain-decision`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ query: decisionQuery, journeyData: journeyData }),
                    });

                    const data = await response.json();

                    if (response.ok) {
                        setDecisionResponse(data.explanation);
                    } else {
                        setDecisionResponse(`Error from backend: ${data.error || 'Unknown error'}`);
                        console.error("Backend error response:", data);
                    }

                } catch (error) {
                    console.error("Error calling backend API:", error);
                    setDecisionResponse("An error occurred while connecting to the backend. Please ensure the backend is running and the URL is correct.");
                } finally {
                    setIsLoadingDecision(false);
                }
            };

            // Initial load and Firebase setup
            useEffect(() => {
                const firebaseConfig = typeof __firebase_config !== 'undefined' ? JSON.parse(__firebase_config) : null;
                const initialAuthToken = typeof __initial_auth_token !== 'undefined' ? __initial_auth_token : null; 

                if (firebaseConfig && window.firebase && window.firebase.auth) {
                    const { initializeApp } = window.firebase;
                    const { getAuth, signInAnonymously, signInWithCustomToken, onAuthStateChanged } = window.firebase.auth;
                    
                    const app = initializeApp(firebaseConfig);
                    const auth = getAuth(app);

                    onAuthStateChanged(auth, (user) => {
                        if (user) {
                            setUserId(user.uid);
                        } else {
                            if (initialAuthToken) {
                                signInWithCustomToken(auth, initialAuthToken)
                                    .then(() => console.log('Signed in with custom token'))
                                    .catch(error => console.error('Error signing in with custom token:', error));
                            } else {
                                signInAnonymously(auth)
                                    .then(() => console.log('Signed in anonymously'))
                                    .catch(error => console.error('Error signing in anonymously:', error));
                            }
                        }
                        setIsAuthReady(true);
                    });
                } else {
                    console.warn('Firebase global objects not found or config missing. Running without Firebase authentication.');
                    setUserId('mock-user-id-' + Math.random().toString(36).substring(2, 9));
                    setIsAuthReady(true);
                }

                // Fetch journey data when component mounts
                fetchJourneyData();
            }, [fetchJourneyData]); // Add fetchJourneyData to dependency array

            // --- Chart Rendering Logic ---
            useEffect(() => {
                if (activeSection === 'journey' && journeyData.length > 0) {
                    // Filter data for charts
                    const quarterlyData = journeyData.filter(item => 
                        item.type === 'event' && item.description && item.description.includes('Diagnostic Results Reviewed')
                    ).map(item => ({
                        date: item.timestamp.split(' ')[0],
                        hrv: item.healthMetricsSnapshot ? item.healthMetricsSnapshot.HRV : null,
                        apoB: item.healthMetricsSnapshot ? item.healthMetricsSnapshot.ApoB : null,
                    }));

                    const monthlyInteractionData = {};
                    // Collect interactions from messages
                    journeyData.filter(item => item.type === 'message' && item.specialistInvolved).forEach(item => {
                        const month = item.timestamp.substring(0, 7); // YYYY-MM
                        if (!monthlyInteractionData[month]) {
                            monthlyInteractionData[month] = {};
                        }
                        const specialist = item.specialistInvolved;
                        monthlyInteractionData[month][specialist] = (monthlyInteractionData[month][specialist] || 0) + 1;
                    });
                    // Collect interactions from events (e.g., onboarding, travel, illness)
                    journeyData.filter(item => item.type === 'event' && item.serviceInteractionType).forEach(item => {
                        const month = item.timestamp.substring(0, 7);
                        if (!monthlyInteractionData[month]) {
                            monthlyInteractionData[month] = {};
                        }
                        const specialist = item.specialistInvolved || 'Elyx Team'; // Default to 'Elyx Team' for events
                        monthlyInteractionData[month][specialist] = (monthlyInteractionData[month][specialist] || 0) + 1;
                    });


                    const allSpecialists = new Set();
                    Object.values(monthlyInteractionData).forEach(monthData => {
                        Object.keys(monthData).forEach(spec => allSpecialists.add(spec));
                    });
                    const sortedSpecialists = Array.from(allSpecialists).sort();


                    const interactionLabels = Object.keys(monthlyInteractionData).sort();
                    const specialistColors = {
                        "Dr. Warren": '#4c51bf', // Indigo
                        "Advik": '#6366f1', // Indigo-500
                        "Carla": '#8b5cf6', // Violet-500
                        "Rachel": '#ec4899', // Pink-500
                        "Neel": '#f97316', // Orange-500
                        "Ruby": '#06b6d4', // Cyan-500
                        "Elyx Team": '#10b981', // Emerald-500 (for general events)
                        "Rohan": '#a3a3a3' // Gray for Rohan's initiated queries
                    };
                    const interactionDatasets = sortedSpecialists.map(specialist => {
                        const data = interactionLabels.map(month => monthlyInteractionData[month][specialist] || 0);
                        return {
                            label: specialist,
                            data: data,
                            backgroundColor: specialistColors[specialist] || '#94a3b8', // Fallback color
                            borderColor: specialistColors[specialist] || '#94a3b8',
                            fill: false,
                            tension: 0.1
                        };
                    });


                    // Destroy existing charts if they exist
                    if (hrvChartRef.current && hrvChartRef.current.chart) {
                        hrvChartRef.current.chart.destroy();
                    }
                    if (apoBChartRef.current && apoBChartRef.current.chart) {
                        apoBChartRef.current.chart.destroy();
                    }
                    if (interactionChartRef.current && interactionChartRef.current.chart) {
                        interactionChartRef.current.chart.destroy();
                    }

                    // HRV Chart
                    if (hrvChartRef.current) {
                        hrvChartRef.current.chart = new Chart(hrvChartRef.current, {
                            type: 'line',
                            data: {
                                labels: quarterlyData.map(d => d.date),
                                datasets: [{
                                    label: 'HRV (ms)',
                                    data: quarterlyData.map(d => d.hrv),
                                    borderColor: '#4c51bf', // Indigo
                                    backgroundColor: 'rgba(76, 81, 191, 0.2)',
                                    tension: 0.1,
                                    fill: true
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {
                                    title: { display: true, text: 'HRV Trend Over Quarters' }
                                },
                                scales: { y: { beginAtZero: false } }
                            }
                        });
                    }

                    // ApoB Chart
                    if (apoBChartRef.current) {
                        apoBChartRef.current.chart = new Chart(apoBChartRef.current, {
                            type: 'line',
                            data: {
                                labels: quarterlyData.map(d => d.date),
                                datasets: [{
                                    label: 'ApoB (mg/dL)',
                                    data: quarterlyData.map(d => d.apoB),
                                    borderColor: '#f97316', // Orange
                                    backgroundColor: 'rgba(249, 115, 22, 0.2)',
                                    tension: 0.1,
                                    fill: true
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {
                                    title: { display: true, text: 'ApoB Trend Over Quarters' }
                                },
                                scales: { y: { beginAtZero: false } }
                            }
                        });
                    }

                    // Interaction Time Chart
                    if (interactionChartRef.current) {
                        interactionChartRef.current.chart = new Chart(interactionChartRef.current, {
                            type: 'bar',
                            data: {
                                labels: interactionLabels,
                                datasets: interactionDatasets
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {
                                    title: { display: true, text: 'Monthly Service Interactions by Specialist' },
                                    tooltip: { mode: 'index', intersect: false }
                                },
                                scales: {
                                    x: { stacked: true },
                                    y: { stacked: true, beginAtZero: true }
                                }
                            }
                        });
                    }
                }
            }, [activeSection, journeyData]); // Re-run when activeSection or journeyData changes

            const renderContent = () => {
                switch (activeSection) {
                    case 'dashboard':
                        const recentMessages = journeyData.filter(item => item.type === 'message').slice(-3).reverse();
                        // Ensure latestMetrics is always an object, even if journeyData is empty
                        const latestMetrics = journeyData.length > 0 && journeyData[journeyData.length - 1].healthMetricsSnapshot 
                                             ? journeyData[journeyData.length - 1].healthMetricsSnapshot 
                                             : { HRV: "N/A", RestingHR: "N/A", GlucoseAvg: "N/A" };
                        return (
                            React.createElement('div', { className: "p-6 text-gray-700" },
                                React.createElement('h2', { className: "text-3xl font-semibold mb-4" }, "Welcome, Rohan!"),
                                React.createElement('p', { className: "text-lg mb-4" }, "This is your personalized health dashboard. Here, you'll find an overview of your progress, key metrics, and upcoming activities."),
                                React.createElement('div', { className: "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" },
                                    React.createElement('div', { className: "bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow duration-300" },
                                        React.createElement('h3', { className: "text-xl font-medium mb-2 text-indigo-700" }, "Current Health Snapshot"),
                                        React.createElement('ul', { className: "list-disc list-inside space-y-1 text-gray-600" },
                                            React.createElement('li', null, "HRV: ", React.createElement('span', { className: "font-semibold text-green-600" }, latestMetrics.HRV, "ms")),
                                            React.createElement('li', null, "Resting HR: ", React.createElement('span', { className: "font-semibold text-green-600" }, latestMetrics.RestingHR, "bpm")),
                                            React.createElement('li', null, "Glucose Avg: ", React.createElement('span', { className: "font-semibold text-green-600" }, latestMetrics.GlucoseAvg, "mg/dL"))
                                        ),
                                        React.createElement('p', { className: "text-sm mt-3 text-gray-500" }, "Last updated: ", journeyData.length > 0 ? journeyData[journeyData.length - 1].timestamp.split(' ')[0] : 'N/A')
                                    ),
                                    React.createElement('div', { className: "bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow duration-300" },
                                        React.createElement('h3', { className: "text-xl font-medium mb-2 text-indigo-700" }, "Upcoming Activities"),
                                        React.createElement('ul', { className: "list-disc list-inside space-y-1 text-gray-600" },
                                            React.createElement('li', null, "Aug 22: Water Quality Test (Ruby)"),
                                            React.createElement('li', null, "Sept 5: VO2 Max Test (Advik)"),
                                            React.createElement('li', null, "Sept 28: Prenuvo MRI (Ruby)")
                                        ),
                                        React.createElement('p', { className: "text-sm mt-3 text-gray-500" }, "Stay on track with your personalized plan!")
                                    ),
                                    React.createElement('div', { className: "bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow duration-300" },
                                        React.createElement('h3', { className: "text-xl font-medium mb-2 text-indigo-700" }, "Recent Communications"),
                                        recentMessages.length > 0 ? (
                                            recentMessages.map((msg, index) => (
                                                React.createElement('p', { key: index, className: "text-gray-600 italic text-sm mb-1" },
                                                    `"${msg.content.length > 70 ? msg.content.substring(0, 70) + '...' : msg.content}" - ${msg.sender} (${msg.timestamp.split(' ')[0]})`
                                                )
                                            ))
                                        ) : (
                                            React.createElement('p', { className: "text-gray-500" }, "No recent messages yet.")
                                        ),
                                        React.createElement('p', { className: "text-sm mt-3 text-gray-500" }, "See full chat history for details.")
                                    )
                                )
                            )
                        );
                    case 'journey':
                        return (
                            React.createElement('div', { className: "p-6 text-gray-700" },
                                React.createElement('h2', { className: "text-3xl font-semibold mb-4" }, "Your Health Journey Timeline"),
                                React.createElement('p', { className: "text-lg mb-6" }, "Visualize your progress, key decisions, and interventions over time."),
                                isGeneratingConversation ? (
                                    React.createElement('div', { className: "text-center py-10 text-xl text-indigo-600" },
                                        React.createElement('p', null, "Generating 8-month journey data from backend..."),
                                        React.createElement('div', { className: "spinner mt-4" })
                                    )
                                ) : (
                                    React.createElement('div', { className: "bg-white p-8 rounded-lg shadow-md overflow-y-auto max-h-[600px] border border-gray-200" },
                                        React.createElement('button', { // Refresh Journey Button
                                            className: "mb-4 px-4 py-2 bg-indigo-500 text-white rounded-md hover:bg-indigo-600 transition-colors duration-300",
                                            onClick: fetchJourneyData,
                                            disabled: isGeneratingConversation
                                        }, "Refresh Journey"),
                                        journeyData.length > 0 ? (
                                            React.createElement('div', { className: "relative pl-6" },
                                                React.createElement('div', { className: "absolute left-0 top-0 bottom-0 w-1 bg-indigo-200 rounded-full" }),
                                                journeyData.map((item, index) => (
                                                    React.createElement('div', { key: index, className: "mb-8 relative" },
                                                        React.createElement('div', { className: "absolute -left-2 top-1 w-5 h-5 bg-indigo-600 rounded-full flex items-center justify-center text-white text-xs z-10" }, item.type === 'message' ? '💬' : '✨'),
                                                        React.createElement('div', { className: "ml-6 pb-4 border-b border-gray-100 last:border-b-0" },
                                                            React.createElement('p', { className: "text-sm text-gray-500 mb-1" }, item.timestamp),
                                                            React.createElement('h3', { className: "font-semibold text-lg text-gray-800" }, item.type === 'message' ? `${item.sender}:` : item.description),
                                                            React.createElement('p', { className: "text-gray-700" }, item.content || item.details),
                                                            item.decisionRationale && (
                                                                React.createElement('div', { className: "mt-2 p-3 bg-blue-50 rounded-md border border-blue-200 text-blue-700 text-sm" },
                                                                    React.createElement('p', { className: "font-medium" }, "Rationale:"),
                                                                    React.createElement('p', null, item.decisionRationale)
                                                                )
                                                            ),
                                                            item.interventionEffect && (
                                                                React.createElement('div', { className: "mt-1 text-xs text-gray-600" }, "Effect: ", item.interventionEffect)
                                                            ),
                                                            item.monetaryFactor && (
                                                                React.createElement('div', { className: "mt-1 text-xs text-gray-600" }, "Monetary: ", item.monetaryFactor)
                                                            ),
                                                            item.timeEfficiency && (
                                                                React.createElement('div', { className: "mt-1 text-xs text-gray-600" }, "Time: ", item.timeEfficiency)
                                                            ),
                                                            item.pillar && (
                                                                React.createElement('div', { className: "mt-1 text-xs text-gray-600" }, "Pillar: ", item.pillar)
                                                            )
                                                        )
                                                    )
                                                ))
                                            )
                                        ) : (
                                            React.createElement('div', { className: "text-center text-gray-400 text-xl py-20" }, "No journey data available yet.")
                                        )
                                    ),
                                    // Quarterly Quality Increase Graphs
                                    React.createElement('div', { className: "mt-12 grid grid-cols-1 lg:grid-cols-2 gap-8" },
                                        React.createElement('div', { className: "bg-white p-6 rounded-lg shadow-md" },
                                            React.createElement('canvas', { ref: hrvChartRef, id: "hrvChart" })
                                        ),
                                        React.createElement('div', { className: "bg-white p-6 rounded-lg shadow-md" },
                                            React.createElement('canvas', { ref: apoBChartRef, id: "apoBChart" })
                                        )
                                    ),
                                    // Interaction Time Graph
                                    React.createElement('div', { className: "mt-8 bg-white p-6 rounded-lg shadow-md" },
                                        React.createElement('canvas', { ref: interactionChartRef, id: "interactionChart" })
                                    )
                                )
                            )
                        );
                    case 'messages':
                        return (
                            React.createElement('div', { className: "p-6 text-gray-700" },
                                React.createElement('h2', { className: "text-3xl font-semibold mb-4" }, "Your Conversations"),
                                React.createElement('p', { className: "text-lg mb-6" }, "Here, you'll find all your WhatsApp-style communications with the Elyx team."),
                                isGeneratingConversation ? (
                                    React.createElement('div', { className: "text-center py-10 text-xl text-indigo-600" },
                                        React.createElement('p', null, "Generating messages..."),
                                        React.createElement('div', { className: "spinner mt-4" })
                                    )
                                ) : (
                                    React.createElement('div', { className: "bg-white p-6 rounded-lg shadow-md overflow-y-auto max-h-[600px] flex flex-col-reverse" },
                                        React.createElement('button', { // Refresh Journey Button
                                            className: "mb-4 px-4 py-2 bg-indigo-500 text-white rounded-md hover:bg-indigo-600 transition-colors duration-300",
                                            onClick: fetchJourneyData,
                                            disabled: isGeneratingConversation
                                        }, "Refresh Journey"),
                                        journeyData.filter(item => item.type === 'message').reverse().map((msg, index) => (
                                            React.createElement('div', { key: index, className: `mb-4 p-3 rounded-lg max-w-[80%] ${msg.sender === 'Rohan' ? 'bg-blue-100 self-end text-right' : 'bg-gray-100 self-start text-left'}` },
                                                React.createElement('p', { className: "font-semibold text-sm mb-1" }, msg.sender),
                                                React.createElement('p', { className: "text-gray-800" }, msg.content),
                                                React.createElement('p', { className: "text-xs text-gray-500 mt-1" }, msg.timestamp),
                                                msg.serviceInteractionType && (
                                                    React.createElement('div', { className: "mt-1 text-xs text-gray-500" }, "Type: ", msg.serviceInteractionType)
                                                ),
                                                msg.specialistInvolved && (
                                                    React.createElement('div', { className: "mt-1 text-xs text-gray-500" }, "Specialist: ", msg.specialistInvolved)
                                                )
                                            )
                                        ))
                                    )
                                )
                            )
                        );
                    case 'specialists':
                        return (
                            React.createElement('div', { className: "p-6 text-gray-700" },
                                React.createElement('h2', { className: "text-3xl font-semibold mb-4" }, "Elyx Health Specialists"),
                                React.createElement('p', { className: "text-lg mb-6" }, "Meet the team of experts guiding your health journey and review their direct communications."),
                                React.createElement('div', { className: "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" },
                                    React.createElement('div', { className: "bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow duration-300" },
                                        React.createElement('h3', { className: "text-xl font-medium mb-2 text-indigo-700" }, "Dr. Warren ", React.createElement('span', { className: "text-sm text-gray-500" }, "(Medical Strategist)")),
                                        React.createElement('p', { className: "text-gray-600 mb-3" }, "**Role:** Physician and final clinical authority, interprets lab results, approves diagnostic strategies.", React.createElement('br'), "**Voice:** Authoritative, precise, scientific."),
                                        React.createElement('p', { className: "text-sm text-gray-500" }, React.createElement('a', { href: "#", className: "text-indigo-600 hover:underline" }, "View Dr. Warren's Chats"))
                                    ),
                                    React.createElement('div', { className: "bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow duration-300" },
                                        React.createElement('h3', { className: "text-xl font-medium mb-2 text-indigo-700" }, "Advik ", React.createElement('span', { className: "text-sm text-gray-500" }, "(Performance Scientist)")),
                                        React.createElement('p', { className: "text-gray-600 mb-3" }, "**Role:** Data analysis expert (wearables data), focuses on nervous system, sleep, cardiovascular training.", React.createElement('br'), "**Voice:** Analytical, curious, pattern-oriented."),
                                        React.createElement('p', { className: "text-sm text-gray-500" }, React.createElement('a', { href: "#", className: "text-indigo-600 hover:underline" }, "View Advik's Chats"))
                                    ),
                                    React.createElement('div', { className: "bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow duration-300" },
                                        React.createElement('h3', { className: "text-xl font-medium mb-2 text-indigo-700" }, "Carla ", React.createElement('span', { className: "text-sm text-gray-500" }, "(Nutritionist)")),
                                        React.createElement('p', { className: "text-gray-600 mb-3" }, "**Role:** Designs nutrition plans, analyzes food logs and CGM data, supplement recommendations.", React.createElement('br'), "**Voice:** Practical, educational, focused on behavioral change."),
                                        React.createElement('p', { className: "text-sm text-gray-500" }, React.createElement('a', { href: "#", className: "text-indigo-600 hover:underline" }, "View Carla's Chats"))
                                    ),
                                    React.createElement('div', { className: "bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow duration-300" },
                                        React.createElement('h3', { className: "text-xl font-medium mb-2 text-indigo-700" }, "Rachel ", React.createElement('span', { className: "text-sm text-gray-500" }, "(PT / Physiotherapist)")),
                                        React.createElement('p', { className: "text-gray-600 mb-3" }, "**Role:** Manages physical movement: strength training, mobility, injury rehabilitation.", React.createElement('br'), "**Voice:** Direct, encouraging, focused on form and function."),
                                        React.createElement('p', { className: "text-sm text-gray-500" }, React.createElement('a', { href: "#", className: "text-indigo-600 hover:underline" }, "View Rachel's Chats"))
                                    ),
                                    React.createElement('div', { className: "bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow duration-300" },
                                        React.createElement('h3', { className: "text-xl font-medium mb-2 text-indigo-700" }, "Dr. Evans ", React.createElement('span', { className: "text-sm text-gray-500" }, "(Stress Management)")),
                                        React.createElement('p', { className: "text-gray-600 mb-3" }, "**Role:** Provides tools and strategies for stress resilience and cognitive load management.", React.createElement('br'), "**Voice:** Practical, insightful, calm (assumed based on context)."),
                                        React.createElement('p', { className: "text-sm mt-3 text-gray-500" }, React.createElement('a', { href: "#", className: "text-indigo-600 hover:underline" }, "View Dr. Evans' Chats"))
                                    ),
                                    React.createElement('div', { className: "bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow duration-300" },
                                        React.createElement('h3', { className: "text-xl font-medium mb-2 text-indigo-700" }, "Ruby ", React.createElement('span', { className: "text-sm text-gray-500" }, "(Concierge)")),
                                        React.createElement('p', { className: "text-gray-600 mb-3" }, "**Role:** Primary point of contact for logistics, scheduling, reminders, and follow-ups.", React.createElement('br'), "**Voice:** Empathetic, organized, proactive."),
                                        React.createElement('p', { className: "text-sm mt-3 text-gray-500" }, React.createElement('a', { href: "#", className: "text-indigo-600 hover:underline" }, "View Ruby's Chats"))
                                    ),
                                    React.createElement('div', { className: "bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow duration-300" },
                                        React.createElement('h3', { className: "text-xl font-medium mb-2 text-indigo-700" }, "Neel ", React.createElement('span', { className: "text-sm text-gray-500" }, "(Concierge Lead)")),
                                        React.createElement('p', { className: "text-gray-600 mb-3" }, "**Role:** Senior leader, major strategic reviews, de-escalates frustrations, connects work to goals.", React.createElement('br'), "**Voice:** Strategic, reassuring, focused on the big picture."),
                                        React.createElement('p', { className: "text-sm mt-3 text-gray-500" }, React.createElement('a', { href: "#", className: "text-indigo-600 hover:underline" }, "View Neel's Chats"))
                                    )
                                )
                            )
                        );
                    case 'decision-query':
                        return (
                            React.createElement('div', { className: "p-6 text-gray-700" },
                                React.createElement('h2', { className: "text-3xl font-semibold mb-4" }, "Ask About a Decision"),
                                React.createElement('p', { className: "text-lg mb-6" }, "Have a question about a specific recommendation, medication, or plan change? Type it below and our AI will provide the rationale."),
                                React.createElement('div', { className: "bg-white p-6 rounded-lg shadow-md" },
                                    React.createElement('textarea', {
                                        className: "w-full p-4 border border-gray-300 rounded-lg mb-4 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all duration-200",
                                        rows: "5",
                                        placeholder: "E.g., Why was the blue-light blocking glasses suggested?",
                                        value: decisionQuery,
                                        onChange: (e) => setDecisionQuery(e.target.value),
                                        disabled: isLoadingDecision
                                    }),
                                    React.createElement('button', {
                                        className: `w-full bg-indigo-600 text-white py-3 px-6 rounded-lg font-semibold text-lg shadow-md transition-all duration-300 ${isLoadingDecision ? 'opacity-70 cursor-not-allowed' : 'hover:bg-indigo-700 hover:shadow-lg'}`,
                                        onClick: handleDecisionQuery,
                                        disabled: isLoadingDecision
                                    }, isLoadingDecision ? 'Asking AI...' : 'Ask Elyx AI'),
                                    decisionResponse && (
                                        React.createElement('div', { className: "mt-6 p-4 bg-indigo-50 rounded-lg border border-indigo-200 text-indigo-800 break-words" },
                                            React.createElement('p', { className: "font-semibold" }, "Elyx AI's Explanation:"),
                                            React.createElement('p', null, decisionResponse)
                                        )
                                    )
                                )
                            )
                        );
                    case 'profile':
                        return (
                            React.createElement('div', { className: "p-6 text-gray-700" },
                                React.createElement('h2', { className: "text-3xl font-semibold mb-4" }, "Rohan's Profile"),
                                React.createElement('div', { className: "bg-white p-6 rounded-lg shadow-md" },
                                    React.createElement('p', { className: "text-lg font-medium text-indigo-700 mb-2" }, "Personal Details:"),
                                    React.createElement('ul', { className: "list-disc list-inside space-y-1 text-gray-600 mb-4" },
                                        React.createElement('li', null, "**Preferred Name:** Rohan Patel"),
                                        React.createElement('li', null, "**Age:** 46"),
                                        React.createElement('li', null, "**Gender:** Male"),
                                        React.createElement('li', null, "**Primary Residence:** Singapore"),
                                        React.createElement('li', null, "**Occupation:** Regional Head of Sales (FinTech)")
                                    ),
                                    React.createElement('p', { className: "text-lg font-medium text-indigo-700 mb-2" }, "Core Goals:"),
                                    React.createElement('ul', { className: "list-disc list-inside space-y-1 text-gray-600 mb-4" },
                                        React.createElement('li', null, "Reduce risk of heart disease (by Dec 2026)"),
                                        React.createElement('li', null, "Enhance cognitive function and focus (by June 2026)"),
                                        React.createElement('li', null, "Implement annual full-body health screenings (starting Nov 2025)")
                                    ),
                                    React.createElement('p', { className: "text-lg font-medium text-indigo-700 mb-2" }, "Behavioral Insights:"),
                                    React.createElement('ul', { className: "list-disc list-inside space-y-1 text-gray-600 mb-4" },
                                        React.createElement('li', null, "Analytical, driven, values efficiency and evidence-based approaches."),
                                        React.createElement('li', null, "Highly motivated but time-constrained. Needs clear, concise plans."),
                                        React.createElement('li', null, "Wife supportive, 2 young kids, employs a cook.")
                                    ),
                                    React.createElement('p', { className: "text-lg font-medium text-indigo-700 mb-2" }, "Tech Stack:"),
                                    React.createElement('ul', { className: "list-disc list-inside space-y-1 text-gray-600" },
                                        React.createElement('li', null, "Garmin watch (used for runs), considering Oura ring/Whoop."),
                                        React.createElement('li', null, "Willing to enable full data sharing.")
                                    )
                                ),
                                isAuthReady && userId && (
                                    React.createElement('div', { className: "mt-6 p-4 bg-blue-50 rounded-lg text-blue-800 break-words" },
                                        React.createElement('p', { className: "font-semibold" }, "Your User ID:"),
                                        React.createElement('p', { className: "text-sm" }, userId)
                                    )
                                )
                            )
                        );
                    default:
                        return null;
                }
            };

            return (
                React.createElement('div', { className: "min-h-screen bg-gray-100 font-sans text-gray-900 flex flex-col" },
                    React.createElement('nav', { className: "bg-indigo-800 p-4 shadow-md" },
                        React.createElement('div', { className: "container mx-auto flex justify-between items-center flex-wrap" },
                            React.createElement('div', { className: "text-white text-2xl font-bold rounded-md px-3 py-1 bg-indigo-600" }, "Elyx Life"),
                            React.createElement('div', { className: "flex space-x-4 mt-2 md:mt-0" },
                                React.createElement(NavItem, { label: "Dashboard", section: "dashboard", activeSection: activeSection, setActiveSection: setActiveSection }),
                                React.createElement(NavItem, { label: "Journey", section: "journey", activeSection: activeSection, setActiveSection: setActiveSection }),
                                React.createElement(NavItem, { label: "Messages", section: "messages", activeSection: activeSection, setActiveSection: setActiveSection }),
                                React.createElement(NavItem, { label: "Specialists", section: "specialists", activeSection: activeSection, setActiveSection: setActiveSection }),
                                React.createElement(NavItem, { label: "Decision Query", section: "decision-query", activeSection: activeSection, setActiveSection: setActiveSection }),
                                React.createElement(NavItem, { label: "Profile", section: "profile", activeSection: activeSection, setActiveSection: setActiveSection })
                            )
                        )
                    ),
                    React.createElement('main', { className: "flex-grow container mx-auto px-4 py-8" }, renderContent()),
                    React.createElement('footer', { className: "bg-indigo-800 p-4 text-white text-center text-sm mt-8" },
                        React.createElement('div', { className: "container mx-auto" }, "© ", new Date().getFullYear(), " Elyx Life. All rights reserved.")
                    )
                )
            );
        }

        // Render the App component into the root div
        const root = ReactDOM.createRoot(document.getElementById('root'));
        root.render(React.createElement(App, null));
    </script>
</body>
</html>
