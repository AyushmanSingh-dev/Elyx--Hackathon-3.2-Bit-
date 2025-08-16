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

# --- Global variable to track Rohan's recently asked topics for memory ---
ROHAN_ASKED_TOPICS = set()

# --- LLM Response Function (Simulated & Enriched) ---
def generate_llm_response(role, prompt_context, current_metrics, chat_history, journey_data_so_far):
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

    # --- Rohan's Responses (Patient Concerns & Priorities) ---
    if role == "Rohan":
        service_interaction_type = "member-initiated query"
        
        # Define a pool of Rohan's questions, categorized by topic
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
            chosen_key = "general_query"
        
        # Select a response from the pool, ensuring it's not a recent duplicate
        available_queries = [q for q in rohan_query_pool[chosen_key] if q not in ROHAN_ASKED_TOPICS]
        if not available_queries: # If all queries for this topic have been used recently, clear memory and try again
            ROHAN_ASKED_TOPICS.clear() 
            available_queries = rohan_query_pool[chosen_key] # Reset to all queries for this topic
            if not available_queries: # Fallback if specific pool is empty
                available_queries = rohan_query_pool["general_query"]
        
        response_text = random.choice(available_queries)
        # Add the chosen query's *topic* to memory, not the exact text, for better control
        ROHAN_ASKED_TOPICS.add(chosen_key) 

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
            next_steps = "Ruby will contact Sarah to begin medical record consolidation."
        elif "medical records" in prompt_lower and role == "Dr. Warren":
            response_text = random.choice([
                "Rohan, Dr. Warren here. I've reviewed your initial submission. The symptoms and data strongly suggest autonomic dysfunction (Pillar 1). To proceed, we must consolidate your complete medical records. This is non-negotiable for safety. Ruby will manage the process.",
                "Dr. Warren. Your initial data points towards autonomic imbalance. Full medical records are vital for a safe, effective strategy. Ruby will handle the logistics.",
                "This is Dr. Warren. To build a robust plan for your autonomic health, complete medical records are essential. Ruby will streamline this process for you.",
                "For precise clinical strategy, Rohan, comprehensive medical records are a foundational requirement. This ensures we maximize safety and avoid redundant efforts. Ruby will manage the collection."
            ])
            decision_rationale = "To establish a clinical-grade strategy, ensure safety, and avoid redundant testing by consolidating complete medical history. This is a foundational step for maximizing long-term health output and preventing future costly errors."
            pillar_impact = "Pillar 1 (Autonomic Health)"
            next_steps = "Complete medical record consolidation via Ruby."
        elif "medical records" in prompt_lower and role == "Ruby":
            response_text = random.choice([
                "The timeline can vary depending on clinics' response speed, but we will manage the entire process. We typically aim for records within 2-3 weeks. We'll provide daily updates to keep you in the loop, ensuring minimal disruption to your schedule.", # Adjusted phrasing
                "We're on it! Consolidating your records is our priority. We'll handle all communication with clinics and keep you updated every step of the way, minimizing your effort.",
                "Don't worry about the record collection. We'll streamline the process, aiming for completion within 2-3 weeks, and notify you as soon as they're ready. Your time is valuable.",
                "Sarah has been briefed on the medical record collection. We anticipate completion within 2-3 weeks, and you'll receive real-time updates, ensuring minimal disruption to your schedule."
            ])
            time_efficiency = "Elyx team handles logistics to save Rohan's time."
            next_steps = "Ruby will send daily updates on record collection progress."
        elif "fitness goals" in prompt_lower and role == "Advik":
            response_text = random.choice([
                "Rohan, Advik here. A good first step is a comprehensive movement assessment to understand your baseline and identify any imbalances. Ruby can help schedule this with Rachel. This will inform your personalized exercise plan, maximizing your workout output.",
                "Advik. To optimize your workouts and prevent injury, a baseline movement assessment is key. Ruby can coordinate with Rachel for this. It's a data-driven approach to maximize your fitness investment.",
                "For your fitness goals, Advik recommends a detailed movement assessment. This will ensure your personalized plan is efficient and effective, fitting your demanding schedule. Ruby will assist with scheduling.",
                "To truly elevate your fitness, Rohan, Advik advises a foundational movement assessment. This data will allow Rachel to craft a highly efficient, personalized exercise program. Ruby will manage the scheduling."
            ])
            decision_rationale = "To establish a data-driven baseline for personalized exercise programming, optimizing for Rohan's time constraints and avoiding injury. This maximizes efficiency and adherence for long-term gains."
            pillar_impact = "Pillar 4 (Structural Health)"
            next_steps = "Schedule movement assessment with Rachel via Ruby."
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
            next_steps = "Focus on consistent hydration and mindful eating practices daily."
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
            next_steps = "Perform couch stretch daily and report back on effectiveness."
            intervention_effect = "Initial relief, focus on long-term mobility." # Default for this intervention
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
            next_steps = "Confirm availability for phlebotomist visit next Tuesday."
        elif "apo b" in prompt_lower and role == "Dr. Warren":
            # Simulate different effectiveness based on current ApoB
            if current_metrics["ApoB"] < 90:
                effect_text = "Your ApoB has shown significant improvement, indicating positive progress on cardiovascular health. This is a great win for your metabolic health!"
                effectiveness = "effective"
                next_steps = "Continue current dietary and exercise interventions; we'll re-evaluate in Q3 to ensure sustained progress."
            else:
                effect_text = "Your ApoB remains elevated, requiring continued focus and potential adjustments to interventions. This is a key area for maximizing your long-term health output."
                effectiveness = "partially effective"
                next_steps = "Carla will refine your dietary plan, and Rachel will review exercise intensity. We'll re-test in Q2 to track progress."

            response_text = random.choice([
                f"Dr. Warren here. Your Q1 diagnostics show ApoB at {current_metrics['ApoB']} mg/dL. {effect_text} Our strategy involves aggressive, integrated lifestyle changes via Carla and Rachel, aiming for significant reduction by Q2. This is a high-ROI health investment.",
                f"Rohan, your ApoB is {current_metrics['ApoB']} mg/dL. {effect_text} This is a primary focus for long-term heart disease risk reduction, aligning with your top health goal. Carla will lead dietary interventions (reducing saturated fat, increasing fiber), and Rachel's exercise plan will be critical. We will aggressively target this with lifestyle changes and re-test in Q2.",
                f"Your Q1 diagnostics show elevated ApoB. This is a serious indicator for heart health, directly impacting your primary goal. Our strategy involves aggressive, integrated lifestyle changes via Carla and Rachel, aiming for significant reduction by Q2. This is a high-ROI health investment."
            ])
            decision_rationale = "Elevated ApoB is a serious cardiovascular risk factor based on Q1 diagnostics. The intervention prioritizes Rohan's top health goal, using integrated lifestyle changes for maximum impact and long-term investment. This approach is more sustainable than medication alone and is a cost-effective preventative measure."
            pillar_impact = "Pillar 3 (Fuel), Pillar 4 (Structural), Pillar 1 (Autonomic)"
            monetary_factor = "Cost-effective preventative measure."
            intervention_effect = effectiveness
            next_steps = next_steps # From conditional logic above
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
            next_steps = "Follow personalized light exposure schedule and utilize identified local gyms during travel."
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
            next_steps = "Engage Elyx Sick Day Protocol: rest, hydration, Ruby will reschedule meetings."
            intervention_effect = "Severe fatigue, recovery score dropped significantly." # Default for this intervention
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
            next_steps = "Begin weekly piano practice; track subjective focus and HRV."
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
            next_steps = "Implement flexible exercise routines; report on adherence."
            intervention_effect = "Plan adapted to improve adherence; metrics may stabilize or improve."
        elif "monetary concern" in prompt_lower:
            response_text = random.choice([
                "We hear your concern about monetary factors. We always strive to provide cost-effective alternatives and ensure every recommendation is a justified investment in your long-term health. For example, simple dietary changes can have a huge impact on ApoB without high cost.",
                "Elyx is about maximizing health ROI. We'll always present cost-effective alternatives and clearly articulate the long-term value of any investment, ensuring your plan is sustainable and delivers maximum output within your budget.",
                "Your financial considerations are important. We focus on high-impact, low-cost interventions where possible, and for any investment, we'll outline the long-term health benefits and how it prevents future, higher costs.",
                "We prioritize value, Rohan. For every recommendation, we consider cost-effectiveness and demonstrate its long-term health ROI, ensuring your investments are prudent and maximize your healthy years."
            ])
            decision_rationale = "Prioritizing Rohan's financial considerations by offering cost-effective alternatives and justifying investments as long-term health benefits, ensuring the plan is sustainable and maximizes value."
            monetary_factor = "Emphasizes cost-effectiveness and justified investment."
            next_steps = "Review proposed cost-effective alternatives with relevant specialist."
        elif "time" in prompt_lower or "busy" in prompt_lower or "quick" in prompt_lower:
            response_text = random.choice([
                "We understand your time constraints. Our goal is to seamlessly integrate health into your busy life. We can focus on micro-interventions, like 5-minute mobility breaks or strategic meal prepping with Javier, to maximize health output with minimal time investment.",
                "Your time is precious. We design interventions for maximum impact in minimal time. Think strategic 10-minute bursts, or leveraging your cook for efficient meal prep, turning health into an integrated lifestyle, not a chore.",
                "We specialize in optimizing for busy schedules. We'll streamline your health activities, focusing on high-leverage actions that fit into your existing routine, ensuring consistent progress without adding burden.",
                "Elyx excels at time-optimization. We'll identify high-impact, low-time interventions and integrate them seamlessly into your demanding schedule, maximizing your health benefits without friction."
            ])
            decision_rationale = "Adapting the plan to Rohan's severe time constraints by focusing on micro-interventions and efficient strategies, ensuring health activities are integrated seamlessly and maximize output per minute invested."
            time_efficiency = "Focus on micro-interventions and strategic planning."
            next_steps = "Implement time-efficient strategies; track impact on schedule and health."
        else:
            response_text = random.choice([
                f"Hi Rohan, {role} here. We're continuously optimizing your plan based on your feedback and data to maximize your health output. How are things going with your current priorities?",
                f"Understood. We'll integrate this into your personalized plan to maximize your health output, considering your time and value. Thanks for the feedback.", # Adjusted phrasing
                f"That's a great point, {ELYX_TEAM_PERSONAS[role]['role']} will look into that for you, ensuring it aligns with your priorities and lifestyle.",
                f"We're always looking for ways to make your health journey more seamless and impactful, turning medical procedures into lifestyle habits. What's on your mind?",
                f"Just checking in, Rohan. How are you feeling about your current progress and any new challenges you're facing? {role} is here to support.",
                f"We've noted your recent activity. {role} is reviewing your latest data for potential optimizations. Anything specific you'd like to discuss?"
            ])
            decision_rationale = "Routine check-in / general response, emphasizing personalized care, value, and lifestyle integration."
            pillar_impact = "General"
            monetary_factor = "General emphasis on value." # Still set for data, but less explicit in text
            time_efficiency = "General emphasis on efficiency." # Still set for data, but less explicit in text
            next_steps = "Continue with current plan; Elyx team will review for further optimizations."

    return response_text, decision_rationale, pillar_impact, health_metrics_snapshot, intervention_effect, monetary_factor, time_efficiency, service_interaction_type, specialist_involved, next_steps

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
    # Clear Rohan's memory for a fresh simulation
    global ROHAN_ASKED_TOPICS
    ROHAN_ASKED_TOPICS.clear()

    # Initial onboarding
    rohan_msg, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist, rohan_next_steps = generate_llm_response("Rohan", "Initial onboarding: I need a proper, coordinated plan. My Garmin HR seems off.", CURRENT_HEALTH_METRICS, chat_history, journey_data)
    journey_data.append({
        "type": "message", "sender": "Rohan", "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
        "content": rohan_msg, "pillar": rohan_pillar, "relatedTo": "Initial onboarding",
        "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
        "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
        "timeEfficiency": rohan_time, "serviceInteractionType": rohan_interaction_type,
        "specialistInvolved": rohan_specialist, "nextSteps": rohan_next_steps
    })
    chat_history.append({"role": "user", "parts": [{"text": rohan_msg}]})

    ruby_msg, ruby_rationale, ruby_pillar, ruby_metrics, ruby_effect, ruby_monetary, ruby_time, ruby_interaction_type, ruby_specialist, ruby_next_steps = generate_llm_response("Ruby", "welcome Rohan and acknowledge concerns", CURRENT_HEALTH_METRICS, chat_history, journey_data)
    journey_data.append({
        "type": "message", "sender": "Ruby", "timestamp": (current_date + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M"),
        "content": ruby_msg, "pillar": ruby_pillar, "relatedTo": "Rohan_Initial",
        "decisionRationale": ruby_rationale, "healthMetricsSnapshot": ruby_metrics,
        "interventionEffect": ruby_effect, "monetaryFactor": ruby_monetary,
        "timeEfficiency": ruby_time, "serviceInteractionType": ruby_interaction_type,
        "specialistInvolved": ruby_specialist, "nextSteps": ruby_next_steps
    })
    chat_history.append({"role": "model", "parts": [{"text": ruby_msg}]})
    
    journey_data.append({
        "type": "event", "eventId": "onboarding_start", "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
        "description": "Member Onboarding Initiated", "details": "Rohan shares medical history and goals.",
        "decisionRationale": "Standard Elyx onboarding process to establish baseline and goals for a personalized plan.",
        "healthMetricsSnapshot": CURRENT_HEALTH_METRICS.copy(), "interventionEffect": None,
        "monetaryFactor": None, "timeEfficiency": None, "serviceInteractionType": "onboarding",
        "specialistInvolved": "Elyx Team", "nextSteps": "Complete medical record consolidation and initial assessments."
    })

    # Simulate 8 months (approx 32 weeks)
    for week in range(1, 33):
        current_date += timedelta(weeks=1)
        
        # --- Weekly Check-in (Ruby/Neel) ---
        if week % 4 == 0: # Monthly review
            team_member = random.choice(["Neel", "Ruby"])
            msg_context = f"weekly/monthly check-in for progress review and alignment with goals. Current metrics: {CURRENT_HEALTH_METRICS}. Rohan's adherence is ~50%."
            msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team = generate_llm_response(team_member, msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": team_member, "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "content": msg, "pillar": pillar, "relatedTo": "Previous interactions",
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                "specialistInvolved": specialist, "nextSteps": next_steps_team
            })
            chat_history.append({"role": "model", "parts": [{"text": msg}]})
            
            rohan_response, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist, rohan_next_steps = generate_llm_response("Rohan", f"response to monthly check-in. Current state: {CURRENT_HEALTH_METRICS}", CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": "Rohan", "timestamp": (current_date + timedelta(minutes=random.randint(5, 15))).strftime("%Y-%m-%d %H:%M"),
                "content": rohan_response, "pillar": rohan_pillar, "relatedTo": "Monthly check-in",
                "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                "timeEfficiency": rohan_time, "serviceInteractionType": rohan_interaction_type,
                "specialistInvolved": rohan_specialist, "nextSteps": rohan_next_steps
            })
            chat_history.append({"role": "user", "parts": [{"text": rohan_response}]})


        # --- Diagnostic Tests (Every 3 months) ---
        if week % 12 == 0: # Roughly every 3 months
            msg_context = "schedule Q1/Q2/Q3 diagnostic panel"
            msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team = generate_llm_response("Ruby", msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": "Ruby", "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "content": msg, "pillar": pillar, "relatedTo": "Program requirement",
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                "specialistInvolved": specialist, "nextSteps": next_steps_team
            })
            chat_history.append({"role": "model", "parts": [{"text": msg}]})
            
            rohan_response, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist, rohan_next_steps = generate_llm_response("Rohan", f"response to diagnostic scheduling. Current state: {CURRENT_HEALTH_METRICS}", CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": "Rohan", "timestamp": (current_date + timedelta(minutes=random.randint(5, 15))).strftime("%Y-%m-%d %H:%M"),
                "content": rohan_response, "pillar": rohan_pillar, "relatedTo": "Diagnostic scheduling",
                "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                "timeEfficiency": rohan_time, "serviceInteractionType": rohan_interaction_type,
                "specialistInvolved": rohan_specialist, "nextSteps": rohan_next_steps
            })
            chat_history.append({"role": "user", "parts": [{"text": rohan_response}]})

            # Simulate event for diagnostic scheduled
            journey_data.append({
                "type": "event", "eventId": f"diagnostic_scheduled_week_{week}", "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "description": f"Quarterly Diagnostic Panel Scheduled (Week {week})",
                "details": "Comprehensive baseline tests for metabolic and hormonal health.",
                "decisionRationale": rationale, "healthMetricsSnapshot": CURRENT_HEALTH_METRICS.copy(),
                "interventionEffect": None, "monetaryFactor": None, "timeEfficiency": None,
                "serviceInteractionType": "diagnostic_scheduling", "specialistInvolved": "Ruby",
                "nextSteps": "Complete diagnostic tests."
            })

            # Simulate results discussion a week later
            results_date = current_date + timedelta(days=7)
            if week == 12: # Q1 results
                # Simulate elevated ApoB and initial metrics
                CURRENT_HEALTH_METRICS["ApoB"] = 105
                CURRENT_HEALTH_METRICS["HRV"] = 48 # Slight increase
                CURRENT_HEALTH_METRICS["POTS_symptoms"] = "moderate"
                msg_context = f"discuss Q1 diagnostic results, elevated ApoB: {CURRENT_HEALTH_METRICS['ApoB']}"
                msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team = generate_llm_response("Dr. Warren", msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
                journey_data.append({
                    "type": "message", "sender": "Dr. Warren", "timestamp": results_date.strftime("%Y-%m-%d %H:%M"),
                    "content": msg, "pillar": pillar, "relatedTo": "Q1 Diagnostics",
                    "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                    "interventionEffect": effect, "monetaryFactor": monetary,
                    "timeEfficiency": time_eff, "serviceInteractionType": "diagnostic_results",
                    "specialistInvolved": specialist, "nextSteps": next_steps_team
                })
                chat_history.append({"role": "model", "parts": [{"text": msg}]})
                
                rohan_response, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist, rohan_next_steps = generate_llm_response("Rohan", f"response to ApoB results. Current state: {CURRENT_HEALTH_METRICS}", CURRENT_HEALTH_METRICS, chat_history, journey_data)
                journey_data.append({
                    "type": "message", "sender": "Rohan", "timestamp": (results_date + timedelta(minutes=random.randint(5, 15))).strftime("%Y-%m-%d %H:%M"),
                    "content": rohan_response, "pillar": rohan_pillar, "relatedTo": "ApoB discussion",
                    "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                    "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                    "timeEfficiency": rohan_time, "serviceInteractionType": rohan_interaction_type,
                    "specialistInvolved": rohan_specialist, "nextSteps": rohan_next_steps
                })
                chat_history.append({"role": "user", "parts": [{"text": rohan_response}]})

                journey_data.append({
                    "type": "event", "eventId": f"q1_results_week_{week}", "timestamp": results_date.strftime("%Y-%m-%d %H:%M"),
                    "description": "Q1 Diagnostic Results Reviewed", "details": f"Elevated ApoB ({CURRENT_HEALTH_METRICS['ApoB']} mg/dL) identified as primary focus.",
                    "decisionRationale": rationale, "healthMetricsSnapshot": CURRENT_HEALTH_METRICS.copy(),
                    "interventionEffect": "ApoB elevated, focus shifted to metabolic health.",
                    "monetaryFactor": "Preventative measures to avoid future high costs.", "timeEfficiency": "Efficient diagnosis.",
                    "serviceInteractionType": "diagnostic_review", "specialistInvolved": "Dr. Warren",
                    "nextSteps": "Implement dietary changes via Carla and exercise adjustments via Rachel; re-test in Q2."
                })

            elif week == 24: # Q2 results
                # Simulate improvement due to interventions
                CURRENT_HEALTH_METRICS["ApoB"] = random.randint(70, 85) # Improved
                CURRENT_HEALTH_METRICS["HRV"] = random.randint(55, 70) # Improved
                CURRENT_HEALTH_METRICS["POTS_symptoms"] = "mild"
                CURRENT_HEALTH_METRICS["BackPain"] = "none"
                msg_context = f"discuss Q2 diagnostic results, improved ApoB: {CURRENT_HEALTH_METRICS['ApoB']}"
                msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team = generate_llm_response("Dr. Warren", msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
                journey_data.append({
                    "type": "message", "sender": "Dr. Warren", "timestamp": results_date.strftime("%Y-%m-%d %H:%M"),
                    "content": msg, "pillar": pillar, "relatedTo": "Q2 Diagnostics",
                    "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                    "interventionEffect": effect, "monetaryFactor": monetary,
                    "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                    "specialistInvolved": specialist, "nextSteps": next_steps_team
                })
                chat_history.append({"role": "model", "parts": [{"text": msg}]})
                
                rohan_response, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist, rohan_next_steps = generate_llm_response("Rohan", f"response to improved ApoB results. Current state: {CURRENT_HEALTH_METRICS}", CURRENT_HEALTH_METRICS, chat_history, journey_data)
                journey_data.append({
                    "type": "message", "sender": "Rohan", "timestamp": (results_date + timedelta(minutes=random.randint(5, 15))).strftime("%Y-%m-%d %H:%M"),
                    "content": rohan_response, "pillar": rohan_pillar, "relatedTo": "ApoB discussion",
                    "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                    "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                    "timeEfficiency": rohan_time, "serviceInteractionType": rohan_interaction_type,
                    "specialistInvolved": rohan_specialist, "nextSteps": rohan_next_steps
                })
                chat_history.append({"role": "user", "parts": [{"text": rohan_response}]})

                journey_data.append({
                    "type": "event", "eventId": f"q2_results_week_{week}", "timestamp": results_date.strftime("%Y-%m-%d %H:%M"),
                    "description": "Q2 Diagnostic Results Reviewed", "details": f"Improved ApoB ({CURRENT_HEALTH_METRICS['ApoB']} mg/dL) due to interventions.",
                    "decisionRationale": rationale, "healthMetricsSnapshot": CURRENT_HEALTH_METRICS.copy(),
                    "interventionEffect": "ApoB significantly improved, HRV increased, POTS symptoms mild.",
                    "monetaryFactor": "Positive ROI on health investment.", "timeEfficiency": "Efficient progress.",
                    "serviceInteractionType": "diagnostic_review", "specialistInvolved": "Dr. Warren",
                    "nextSteps": "Continue current plan; focus on maintenance and further optimization."
                })

        # --- Exercise Updates (Every 2 weeks) ---
        if week % 2 == 0:
            team_member = "Rachel"
            msg_context = f"update exercise plan based on progress. Current metrics: {CURRENT_HEALTH_METRICS}. Rohan's adherence is ~50%."
            msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team = generate_llm_response(team_member, msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": team_member, "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "content": msg, "pillar": pillar, "relatedTo": "Exercise progress",
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                "specialistInvolved": specialist, "nextSteps": next_steps_team
            })
            chat_history.append({"role": "model", "parts": [{"text": msg}]})
            
            # Simulate Rohan's adherence (50% adherence)
            if random.random() < 0.5: # Rohan deviates
                rohan_deviation, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist, rohan_next_steps = generate_llm_response("Rohan", f"deviate from exercise plan due to travel/time/soreness. Current state: {CURRENT_HEALTH_METRICS}", CURRENT_HEALTH_METRICS, chat_history, journey_data)
                journey_data.append({
                    "type": "message", "sender": "Rohan", "timestamp": (current_date + timedelta(minutes=random.randint(30, 60))).strftime("%Y-%m-%d %H:%M"),
                    "content": rohan_deviation, "pillar": rohan_pillar, "relatedTo": "Exercise deviation",
                    "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                    "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                    "timeEfficiency": rohan_time, "serviceInteractionType": rohan_interaction_type,
                    "specialistInvolved": rohan_specialist, "nextSteps": rohan_next_steps
                })
                chat_history.append({"role": "user", "parts": [{"text": rohan_deviation}]})
                
                # Elyx team adapts
                adapt_msg, adapt_rationale, adapt_pillar, adapt_metrics, adapt_effect, adapt_monetary, adapt_time, adapt_interaction_type, adapt_specialist, adapt_next_steps = generate_llm_response(random.choice(["Rachel", "Advik"]), f"adapt to Rohan's exercise deviation. Current state: {CURRENT_HEALTH_METRICS}", CURRENT_HEALTH_METRICS, chat_history, journey_data)
                journey_data.append({
                    "type": "message", "sender": random.choice(["Rachel", "Advik"]), "timestamp": (current_date + timedelta(minutes=random.randint(90, 120))).strftime("%Y-%m-%d %H:%M"),
                    "content": adapt_msg, "pillar": adapt_pillar, "relatedTo": "Adaptation",
                    "decisionRationale": adapt_rationale, "healthMetricsSnapshot": adapt_metrics,
                    "interventionEffect": adapt_effect, "monetaryFactor": adapt_monetary,
                    "timeEfficiency": adapt_time, "serviceInteractionType": adapt_interaction_type,
                    "specialistInvolved": adapt_specialist, "nextSteps": adapt_next_steps
                })
                chat_history.append({"role": "model", "parts": [{"text": adapt_msg}]})

            else: # Rohan adheres
                rohan_adherence, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist, rohan_next_steps = generate_llm_response("Rohan", f"adhere to exercise plan. Current state: {CURRENT_HEALTH_METRICS}", CURRENT_HEALTH_METRICS, chat_history, journey_data)
                journey_data.append({
                    "type": "message", "sender": "Rohan", "timestamp": (current_date + timedelta(minutes=random.randint(30, 60))).strftime("%Y-%m-%d %H:%M"),
                    "content": rohan_adherence, "pillar": rohan_pillar, "relatedTo": "Exercise adherence",
                    "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                    "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                    "timeEfficiency": rohan_time, "serviceInteractionType": rohan_interaction_type,
                    "specialistInvolved": rohan_specialist, "nextSteps": rohan_next_steps
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
            msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team = generate_llm_response("Advik", msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": "Advik", "timestamp": travel_start_date.strftime("%Y-%m-%d %H:%M"),
                "content": msg, "pillar": pillar, "relatedTo": "Travel",
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                "specialistInvolved": specialist, "nextSteps": next_steps_team
            })
            chat_history.append({"role": "model", "parts": [{"text": msg}]})

            msg_context = f"confirm travel logistics for upcoming trip. Current state: {CURRENT_HEALTH_METRICS}"
            msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team = generate_llm_response("Ruby", msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": "Ruby", "timestamp": (travel_start_date + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M"),
                "content": msg, "pillar": pillar, "relatedTo": "Travel",
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                "specialistInvolved": specialist, "nextSteps": next_steps_team
            })
            chat_history.append({"role": "model", "parts": [{"text": msg}]})
            
            journey_data.append({
                "type": "event", "eventId": f"travel_start_week_{week}", "timestamp": travel_start_date.strftime("%Y-%m-%d %H:%M"),
                "description": f"Rohan travels for business (Week {week})", "details": "Jet lag protocol, in-flight mobility, nutrition adjustments.",
                "decisionRationale": "Proactive mitigation of travel stress on health goals, maximizing performance during demanding trips.",
                "healthMetricsSnapshot": CURRENT_HEALTH_METRICS.copy(), "interventionEffect": "Potential for jet lag/fatigue.",
                "monetaryFactor": "Business travel cost, focus on health investment ROI.", "timeEfficiency": "Optimized for busy travel schedule.",
                "serviceInteractionType": "travel_event", "specialistInvolved": "Advik, Ruby",
                "nextSteps": "Follow travel protocol; Advik to monitor recovery post-trip."
            })
            
            # Simulate post-travel check-in
            post_travel_date = travel_start_date + timedelta(days=7) # Fixed: Used travel_start_date
            msg_context = f"post-travel recovery check-in. Current state: {CURRENT_HEALTH_METRICS}"
            msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team = generate_llm_response("Advik", msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": "Advik", "timestamp": post_travel_date.strftime("%Y-%m-%d %H:%M"),
                "content": msg, "pillar": pillar, "relatedTo": "Post-travel recovery",
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                "specialistInvolved": specialist, "nextSteps": next_steps_team
            })
            chat_history.append({"role": "model", "parts": [{"text": msg}]})
            
            # Simulate negative metric impact from travel
            CURRENT_HEALTH_METRICS["HRV"] -= random.randint(0, 5)
            CURRENT_HEALTH_METRICS["RecoveryScore"] -= random.randint(0, 10)
            CURRENT_HEALTH_METRICS["DeepSleep"] -= random.randint(0, 15)

        # --- Member-Initiated Queries (Up to 5 per week on average) ---
        # This section now uses the ROHAN_ASKED_TOPICS set for memory
        if random.random() < 0.7: # Simulate Rohan asking questions
            num_questions = random.randint(1, 3) # Simulate 1-3 questions per week
            for _ in range(num_questions):
                # Define a pool of Rohan's questions, categorized by topic
                query_pool = {
                    "poor digestion": ["I'm experiencing poor digestion. Any suggestions that are easy to integrate into my busy schedule?", "What are some practical dietary adjustments for improving digestion, considering my travel and time constraints?", "My digestion feels off. Are there any simple, effective strategies I can implement immediately?", "Can you provide quick, actionable tips for better digestion that won't disrupt my routine?"],
                    "stress": ["I'm feeling stressed. Any immediate tips for managing cognitive load?", "What are some quick stress relief techniques I can use on the go?", "How can I better manage my work-related stress without impacting my schedule?", "Are there any low-cost strategies for reducing daily stress?"],
                    "sleep": ["My sleep quality has been poor. Any immediate suggestions?", "What are some practical tips for improving deep sleep, even with a busy schedule?", "I'm struggling to fall asleep. Any quick bedtime routines?", "Are there any products or alternatives for better sleep that are cost-effective?"],
                    "hrv": ["How can I improve my HRV? What factors influence it most?", "My HRV seems low. What are the most impactful interventions to raise it?", "What does my current HRV data indicate about my recovery?", "Can you explain the correlation between HRV and stress management?"],
                    "cognitive function": ["How can I enhance my cognitive function and focus?", "Are there any brain-boosting foods or supplements you recommend?", "What exercises can improve mental clarity?", "What's the best way to maintain peak cognitive performance under pressure?"],
                    "new product": ["Have you come across any new health products that might benefit me?", "Can you recommend a new wearable or health tech that aligns with my goals?", "Are there any cost-effective health products worth exploring?", "What are some innovative products for sleep or recovery?"],
                    "alternative exercise": ["I need alternative exercises for when I'm traveling or short on time. Any suggestions?", "What are some effective bodyweight exercises I can do anywhere?", "Can you suggest alternatives to gym workouts that are time-efficient?", "Are there any low-impact exercise alternatives for recovery days?"],
                    "monetary_concern": ["I'm concerned about the cost of some recommendations. Can you suggest more budget-friendly alternatives?", "How can we optimize for value without compromising results? Are there more economical options?", "What's the return on investment for this, and are there less expensive but still effective options?", "I need to balance health investments with financial prudence. What are some high-impact, low-cost recommendations?"],
                    "time_constraint": ["I have very limited time. What's the most time-efficient way to achieve Y?", "My schedule is packed. Can we focus on high-impact, low-time-commitment interventions?", "What are some quick wins for health that fit into a demanding schedule?", "I need strategies that deliver maximum health output for minimal time investment. Any suggestions?"],
                    "general_query": ["Just checking in. Any new recommendations based on my overall progress?", "What's the overarching strategy for the next phase of my health journey?", "I'm curious about optimizing my current routine. Any thoughts on that?", "What's the latest insight from my data? Any new areas of focus?"]
                }
                
                # Select a topic, prioritizing those not recently asked
                available_topics = [t for t in query_pool.keys() if t not in ROHAN_ASKED_TOPICS]
                if not available_topics:
                    ROHAN_ASKED_TOPICS.clear() # Clear memory if all topics exhausted
                    available_topics = list(query_pool.keys()) # Reset to all topics
                
                chosen_topic = random.choice(available_topics)
                ROHAN_ASKED_TOPICS.add(chosen_topic) # Add chosen topic to memory

                # Select a specific question for that topic, avoiding recent exact duplicates
                # FIXED: Ensure msg['parts'][0]['text'] is used for content check in chat_history
                recent_user_messages_content = [msg['parts'][0]['text'] for msg in chat_history[-5:] if msg['role'] == 'user' and 'parts' in msg and len(msg['parts']) > 0 and 'text' in msg['parts'][0]]
                available_questions_for_topic = [q for q in query_pool[chosen_topic] if q not in recent_user_messages_content]
                if not available_questions_for_topic:
                    available_questions_for_topic = query_pool[chosen_topic] # Reset if all questions for topic are recent
                
                rohan_query = random.choice(available_questions_for_topic)
                
                rohan_response, rohan_rationale, rohan_pillar, rohan_metrics, rohan_effect, rohan_monetary, rohan_time, rohan_interaction_type, rohan_specialist, rohan_next_steps = generate_llm_response("Rohan", rohan_query, CURRENT_HEALTH_METRICS, chat_history, journey_data)
                journey_data.append({
                    "type": "message", "sender": "Rohan", "timestamp": (current_date + timedelta(hours=random.randint(1, 24))).strftime("%Y-%m-%d %H:%M"),
                    "content": rohan_query, "pillar": rohan_pillar, "relatedTo": chosen_topic,
                    "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                    "interventionEffect": rohan_effect, "monetaryFactor": rohan_monetary,
                    "timeEfficiency": rohan_time, "serviceInteractionType": rohan_interaction_type,
                    "specialistInvolved": rohan_specialist, "nextSteps": rohan_next_steps
                })
                chat_history.append({"role": "user", "parts": [{"text": rohan_query}]})
                
                # Elyx team responds to query
                team_member = random.choice(list(ELYX_TEAM_PERSONAS.keys()))
                response_to_query, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team = generate_llm_response(team_member, f"respond to Rohan's query about {chosen_topic}. Current state: {CURRENT_HEALTH_METRICS}", CURRENT_HEALTH_METRICS, chat_history, journey_data)
                journey_data.append({
                    "type": "message", "sender": team_member, "timestamp": (current_date + timedelta(hours=random.randint(2, 48))).strftime("%Y-%m-%d %H:%M"),
                    "content": response_to_query, "pillar": pillar, "relatedTo": chosen_topic,
                    "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                    "interventionEffect": effect, "monetaryFactor": monetary,
                    "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                    "specialistInvolved": specialist, "nextSteps": next_steps_team
                })
                chat_history.append({"role": "model", "parts": [{"text": response_to_query}]})
                
                # Simulate metric changes based on interventions/deviations (simplified)
                if "stress" in chosen_topic:
                    CURRENT_HEALTH_METRICS["HRV"] += random.randint(-5, 5) # Larger range for noticeable change
                if "sleep" in chosen_topic:
                    CURRENT_HEALTH_METRICS["DeepSleep"] += random.randint(-15, 15) # Larger range
                if "exercise" in chosen_topic:
                    CURRENT_HEALTH_METRICS["RecoveryScore"] += random.randint(-5, 8) # Larger range

        # --- Simulate specific events/concerns over time ---
        if week == 5: # Simulate initial back pain flare-up
            msg_context = "suggest couch stretch for back pain"
            msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team = generate_llm_response("Rachel", msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": "Rachel", "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "content": msg, "pillar": pillar, "relatedTo": "Back pain",
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                "specialistInvolved": specialist, "nextSteps": next_steps_team
            })
            chat_history.append({"role": "model", "parts": [{"text": msg}]})
            journey_data.append({
                "type": "event", "eventId": "back_pain_intervention", "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "description": "Back pain intervention (couch stretch)", "details": "Addressing Rohan's reported lower back pain with targeted mobility.",
                "decisionRationale": rationale, "healthMetricsSnapshot": CURRENT_HEALTH_METRICS.copy(),
                "interventionEffect": "Initial relief, focus on long-term mobility.",
                "monetaryFactor": "No direct cost, time-efficient.", "timeEfficiency": "2-minute routine.",
                "serviceInteractionType": "intervention_event", "specialistInvolved": "Rachel",
                "nextSteps": "Perform couch stretch daily and report back on effectiveness."
            })
            CURRENT_HEALTH_METRICS["BackPain"] = "mild" # Simulate slight improvement

        if week == 10: # Simulate a major illness setback
            msg_context = "initiate sick day protocol due to viral infection"
            msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team = generate_llm_response("Dr. Warren", msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": "Dr. Warren", "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "content": msg, "pillar": pillar, "relatedTo": "Illness",
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                "specialistInvolved": specialist, "nextSteps": next_steps_team
            })
            chat_history.append({"role": "model", "parts": [{"text": msg}]})
            journey_data.append({
                "type": "event", "eventId": "illness_setback", "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "description": "Major Illness Setback (Viral Infection)", "details": "Elyx Sick Day Protocol initiated, board meeting postponed.",
                "decisionRationale": rationale, "healthMetricsSnapshot": CURRENT_HEALTH_METRICS.copy(),
                "interventionEffect": "Severe fatigue, recovery score dropped significantly.",
                "monetaryFactor": "Potential business cost due to postponed meeting, but avoids higher future medical costs.",
                "timeEfficiency": "Focus on radical rest, minimal time for other activities.",
                "serviceInteractionType": "health_crisis_event", "specialistInvolved": "Dr. Warren, Ruby",
                "nextSteps": "Engage Elyx Sick Day Protocol: rest, hydration, Ruby will reschedule meetings."
            })
            CURRENT_HEALTH_METRICS["RecoveryScore"] = 10 # Simulate very low recovery
            CURRENT_HEALTH_METRICS["POTS_symptoms"] = "severe" # Worsen POTS

        if week == 15: # Simulate a new health investment (piano)
            msg_context = "add weekly piano practice as trackable goal"
            msg, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps_team = generate_llm_response("Neel", msg_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
            journey_data.append({
                "type": "message", "sender": "Neel", "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "content": msg, "pillar": pillar, "relatedTo": "New Goal",
                "decisionRationale": rationale, "healthMetricsSnapshot": metrics_snap,
                "interventionEffect": effect, "monetaryFactor": monetary,
                "timeEfficiency": time_eff, "serviceInteractionType": interaction_type,
                "specialistInvolved": specialist, "nextSteps": next_steps_team
            })
            chat_history.append({"role": "model", "parts": [{"text": msg}]})
            journey_data.append({
                "type": "event", "eventId": "piano_goal_added", "timestamp": current_date.strftime("%Y-%m-%d %H:%M"),
                "description": "Weekly Piano Practice Added to Plan", "details": "Cognitive longevity and stress management investment.",
                "decisionRationale": rationale, "healthMetricsSnapshot": CURRENT_HEALTH_METRICS.copy(),
                "interventionEffect": "Expected long-term cognitive and stress resilience benefits.",
                "monetaryFactor": "Initial cost of piano/lessons, long-term non-monetary benefit.",
                "timeEfficiency": "Integrated into weekly routine, flexible scheduling.",
                "serviceInteractionType": "goal_setting_event", "specialistInvolved": "Neel",
                "nextSteps": "Begin weekly piano practice; track subjective focus and HRV."
            })
        
        # Simulate general metric fluctuations
        CURRENT_HEALTH_METRICS["HRV"] = max(30, CURRENT_HEALTH_METRICS["HRV"] + random.randint(-5, 7)) # Increased range for more variability
        CURRENT_HEALTH_METRICS["RestingHR"] = max(50, CURRENT_HEALTH_METRICS["RestingHR"] + random.randint(-2, 2))
        CURRENT_HEALTH_METRICS["GlucoseAvg"] = random.randint(90, 105) # Increased range
        CURRENT_HEALTH_METRICS["RecoveryScore"] = max(20, min(95, CURRENT_HEALTH_METRICS["RecoveryScore"] + random.randint(-8, 10))) # Increased range
        CURRENT_HEALTH_METRICS["DeepSleep"] = max(30, min(120, CURRENT_HEALTH_METRICS["DeepSleep"] + random.randint(-15, 20))) # Increased range
        
        # More dynamic POTS/BackPain status changes
        if CURRENT_HEALTH_METRICS["POTS_symptoms"] == "severe" and random.random() < 0.4: # Higher chance to improve
            CURRENT_HEALTH_METRICS["POTS_symptoms"] = "moderate"
        elif CURRENT_HEALTH_METRICS["POTS_symptoms"] == "moderate" and random.random() < 0.4:
            CURRENT_HEALTH_METRICS["POTS_symptoms"] = "mild"
        elif CURRENT_HEALTH_METRICS["POTS_symptoms"] == "mild" and random.random() < 0.1: # Small chance to worsen
             CURRENT_HEALTH_METRICS["POTS_symptoms"] = random.choice(["moderate", "severe"])
        
        if CURRENT_HEALTH_METRICS["BackPain"] == "severe" and random.random() < 0.4: # Higher chance to improve
            CURRENT_HEALTH_METRICS["BackPain"] = "moderate"
        elif CURRENT_HEALTH_METRICS["BackPain"] == "moderate" and random.random() < 0.4:
            CURRENT_HEALTH_METRICS["BackPain"] = "mild"
        elif CURRENT_HEALTH_METRICS["BackPain"] == "mild" and random.random() < 0.1: # Small chance to worsen
            CURRENT_HEALTH_METRICS["BackPain"] = random.choice(["moderate", "severe"])

    return jsonify(journey_data) # Return as JSON response

@app.route('/api/explain-decision', methods=['POST'])
def api_explain_decision():
    data = request.json
    query = data.get('query')
    journey_data_context = data.get('journeyData', []) # Get the full journey data as context
    
    if not query:
        return jsonify({"error": "Query is required."}), 400
    
    # Search for the most relevant item in journey_data_context
    relevant_item = None
    query_lower = query.lower()
    
    # Prioritize events/messages with decisionRationales
    searchable_items = [item for item in journey_data_context if 'decisionRationale' in item and item['decisionRationale']]
    
    # Simple keyword matching for relevance
    for item in reversed(searchable_items): # Search recent history first
        content_to_search = item.get('content', '') + ' ' + item.get('description', '') + ' ' + item.get('details', '') + ' ' + item.get('decisionRationale', '')
        if query_lower in content_to_search.lower():
            relevant_item = item
            break # Found the most recent relevant item

    explanation_text = "I'm sorry, I couldn't find a specific decision matching your query in your journey history. Please try rephrasing or asking about a specific intervention."
    rationale = None
    pillar = None
    metrics_snap = None
    effect = None
    monetary = None
    time_eff = None
    specialist = None
    next_steps = None # Initialize next_steps

    if relevant_item:
        explanation_text = relevant_item.get('content') or relevant_item.get('description') or relevant_item.get('details')
        rationale = relevant_item.get('decisionRationale')
        pillar = relevant_item.get('pillar')
        metrics_snap = relevant_item.get('healthMetricsSnapshot')
        effect = relevant_item.get('interventionEffect')
        monetary = relevant_item.get('monetaryFactor')
        time_eff = relevant_item.get('timeEfficiency')
        specialist = relevant_item.get('specialistInvolved')
        next_steps = relevant_item.get('nextSteps') # Get next_steps from the found item
    else:
        # Fallback to general keyword responses if no specific journey item is found
        explanation_text, rationale, pillar, metrics_snap, effect, monetary, time_eff, interaction_type, specialist, next_steps = generate_llm_response(
            role="Elyx AI Concierge",
            prompt_context=query,
            current_metrics=CURRENT_HEALTH_METRICS,
            chat_history=[],
            journey_data_so_far=[] # Don't pass full context again to avoid recursive search
        )
    
    # Format the explanation to include the new fields
    formatted_explanation = f"{explanation_text}\n\n"
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
    if next_steps: # Include next_steps in the formatted explanation
        formatted_explanation += f"**Following Steps:** {next_steps}\n"
    if metrics_snap:
        formatted_explanation += f"**Metrics at Time:** {json.dumps(metrics_snap, indent=2)}\n"

    return jsonify({"explanation": formatted_explanation})

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
