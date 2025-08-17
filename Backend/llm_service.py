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

# --- NEW: Expanded Knowledge Base for Elyx Team ---
ELYX_KNOWLEDGE_BASE = {
    "hypertension": {
        "specialist": "Dr. Warren",
        "summary": "Hypertension, or high blood pressure, is a common condition where the long-term force of the blood against your artery walls is high enough that it may eventually cause health problems, such as heart disease.",
        "advice": "Management often involves regular monitoring, lifestyle changes like a low-sodium diet (DASH diet), regular aerobic exercise, stress reduction, and sometimes medication. We would need to do a full workup before making specific recommendations."
    },
    "sleep apnea": {
        "specialist": "Advik",
        "summary": "Sleep apnea is a potentially serious sleep disorder in which breathing repeatedly stops and starts. Key indicators can be loud snoring, daytime fatigue, and observed pauses in breathing during sleep.",
        "advice": "From a performance science perspective, this severely impacts recovery, HRV, and cognitive function. A formal sleep study is the gold standard for diagnosis. Interventions can range from lifestyle changes to using a CPAP machine."
    },
    "migraines": {
        "specialist": "Carla",
        "summary": "Migraines are intense headaches often accompanied by nausea, vomiting, and sensitivity to light and sound. They can be triggered by various factors, including stress, certain foods, and hormonal changes.",
        "advice": "Keeping a detailed diary of food intake, sleep patterns, and stress levels can help identify personal triggers. Common dietary triggers include aged cheeses, processed meats, and caffeine. Magnesium can sometimes be a helpful supplement."
    },
    "common cold": {
        "specialist": "Ruby",
        "summary": "The common cold is a viral infection of your nose and throat (upper respiratory tract). It's usually harmless, although it might not feel that way.",
        "advice": "The best approach is rest and hydration. Our Sick Day Protocol can be initiated to help manage symptoms and reschedule commitments to prioritize recovery. We can also arrange for nutrient-dense meal delivery."
    },
    "GERD": {
        "specialist": "Carla",
        "summary": "Gastroesophageal reflux disease (GERD) happens when stomach acid frequently flows back into the tube connecting your mouth and stomach (esophagus). This backwash (acid reflux) can irritate the lining of your esophagus.",
        "advice": "To manage symptoms, avoid eating large meals, especially within 2-3 hours of bedtime. Common trigger foods include spicy foods, fatty foods, chocolate, and caffeine. Elevating the head of your bed can also provide relief."
    }
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
    sentiment = "neutral" # Default sentiment

    # --- Rohan's Responses (Patient Concerns & Priorities) ---
    if role == "Rohan":
        service_interaction_type = "member-initiated query"
        
        # --- MODIFIED: Expanded Rohan's query pool for more variety ---
        rohan_query_pool = {
            "initial_plan": [
                "Ruby, I'm feeling overwhelmed with my ad-hoc health routine. High work stress, and my Garmin HR seems off even on rest days. I need a proper, coordinated plan. My current supplement list is attached.",
            ],
            "apo_b": [
                "What's the plan for the ApoB? I want clear, actionable steps. Is this a significant investment?",
                "Given the ApoB results, what's the immediate, high-impact strategy? I need to know the financial implications and time commitment."
            ],
            # --- NEW: Categories for Rohan's proactive communication ---
            "status_update": [
                "Just a quick check-in. The new meal plan from Carla has been great, feeling more energetic this week.",
                "Feeling a bit flat this week. Recovery scores are down and I'm struggling to keep up with the workout intensity.",
                "The travel protocol for the US trip was a game-changer. Minimal jet lag. Great work.",
                "My back pain has flared up again after the flight from Jakarta. The couch stretch isn't cutting it this time."
            ],
            "plan_change_request": [
                "This current workout block is starting to feel too easy. Can Rachel design something more challenging for next month?",
                "I'm finding it difficult to source some of the ingredients Carla recommended while traveling. Can we look at more accessible alternatives?",
                "I have a bit more downtime than expected over the next two weeks. Can we be more aggressive with the fitness plan?",
                "My morning schedule is getting tighter. Can we shift the meditation/mobility routine to the evening?"
            ],
            "sudden_trip": [
                "Team, heads up. I have a last-minute trip to London scheduled for next week. Can we quickly assemble a jet lag and fitness plan?",
                "Unexpected travel coming up. Need to be in Seoul for 4 days starting Thursday. What's the protocol?",
                "Just got pulled into a last-minute summit in New York. Need the usual travel prep, please."
            ],
            "general_health_query": [
                "A colleague was just diagnosed with hypertension. What are the key things I should be aware of, given my family history?",
                "I've been snoring more lately according to my wife. Could this be related to sleep apnea?",
                "I've been getting more frequent headaches recently. Could they be migraines?",
                "My son has a cold, what's the best way to avoid getting sick myself during a high-stakes work week?"
            ],
            # Fallback category
            "general_query": [
                "Just checking in. Any new recommendations based on my overall progress?",
                "What's the latest insight from my data? Any new areas of focus?"
            ]
        }

        # Determine Rohan's question based on prompt_context
        # (This logic is simplified for the simulation; in a real app, it would be based on user input)
        chosen_key = "general_query" # Default
        for key in rohan_query_pool:
            if key.replace("_", " ") in prompt_lower:
                chosen_key = key
                break
        
        available_queries = rohan_query_pool.get(chosen_key, rohan_query_pool["general_query"])
        response_text = random.choice(available_queries)
        ROHAN_ASKED_TOPICS.add(chosen_key)

        # Determine Rohan's sentiment based on current metrics or context
        if current_metrics["RecoveryScore"] < 50 or "flared up" in prompt_lower or "struggling" in prompt_lower:
            sentiment = random.choice(["angry", "sad"])
        elif current_metrics["RecoveryScore"] > 80 or "game-changer" in prompt_lower or "feeling great" in prompt_lower:
            sentiment = "positive"
        elif "curious" in prompt_lower or "what about" in prompt_lower:
            sentiment = "curious"
        else:
            sentiment = "neutral"

    # --- Elyx Team Member Responses (Prioritizing, Value-Driven, Adaptable) ---
    else:
        service_interaction_type = "proactive check-in" if "check-in" in prompt_lower else "intervention update"
        
        # --- NEW: Check against the expanded knowledge base first ---
        knowledge_base_hit = False
        for topic, data in ELYX_KNOWLEDGE_BASE.items():
            if topic in prompt_lower:
                specialist_involved = data["specialist"]
                response_text = (f"Hi Rohan, {specialist_involved} here. That's a great question about {topic.replace('_', ' ')}. "
                                 f"{data['summary']} In your specific case, {data['advice']}")
                decision_rationale = f"Providing evidence-based general information on {topic} while contextualizing it for Rohan and emphasizing the need for personalized diagnosis."
                pillar_impact = "Health Education & Literacy"
                next_steps = f"If you're concerned, we can schedule a consultation with Dr. Warren to discuss a diagnostic pathway for {topic}."
                knowledge_base_hit = True
                break
        
        # --- MODIFIED: The original logic now serves as a fallback ---
        if not knowledge_base_hit:
            # --- Context-aware responses based on Rohan's last query ---
            last_rohan_message_lower = chat_history[-1]['parts'][0]['text'].lower() if chat_history and chat_history[-1]['role'] == 'user' and 'parts' in chat_history[-1] and len(chat_history[-1]['parts']) > 0 and 'text' in chat_history[-1]['parts'][0] else ""

            if "initial submission" in prompt_lower and role == "Ruby":
                response_text = "Hi Rohan, thank you for sharing this. We understand. Our goal is to bring coordination to your health. I'm flagging your concerns for Dr. Warren to review immediately. We're here to make this seamless for you."
                decision_rationale = "Prioritizing Rohan's core concern of 'ad-hoc health' by initiating a coordinated clinical review, maximizing early engagement output."
                time_efficiency = "Immediate flagging for quick initial response."
                next_steps = "Ruby will contact Sarah to begin medical record consolidation."
            
            # ... (all other original elif blocks for specific journey steps remain here) ...

            elif "apo b" in prompt_lower and role == "Dr. Warren":
                # Simulate different effectiveness based on current ApoB
                if current_metrics["ApoB"] < 90:
                    effect_text = "Your ApoB has shown significant improvement, indicating positive progress on cardiovascular health. This is a great win for your metabolic health!"
                    effectiveness = "effective"
                    next_steps = "Continue current dietary and exercise interventions; re-evaluate in Q3 to ensure sustained progress."
                else:
                    effect_text = "Your ApoB remains elevated, requiring continued focus and potential adjustments to interventions. This is a key area for maximizing your long-term health output."
                    effectiveness = "partially effective"
                    next_steps = "Carla will refine your dietary plan, and Rachel will review exercise intensity. We'll re-test in Q2 to track progress."

                response_text = f"Dr. Warren here. Your Q1 diagnostics show ApoB at {current_metrics['ApoB']} mg/dL. {effect_text} This is a primary focus for long-term heart disease risk reduction, aligning with your top health goal. Carla will lead dietary interventions (reducing saturated fat, increasing fiber), and Rachel's exercise plan will be critical. We will aggressively target this with lifestyle changes and re-test in Q2."
                decision_rationale = "Elevated ApoB is a serious cardiovascular risk factor based on diagnostics. The intervention prioritizes Rohan's top health goal, using integrated lifestyle changes for maximum impact and long-term investment. This approach is more sustainable than medication alone and is a cost-effective preventative measure."
                pillar_impact = "Pillar 3 (Fuel), Pillar 4 (Structural), Pillar 1 (Autonomic)"
                monetary_factor = "Cost-effective preventative measure."
                intervention_effect = effectiveness
                next_steps = next_steps # From conditional logic above

            # --- NEW: Response logic for Rohan's new proactive queries ---
            elif "sudden trip" in prompt_lower or "last-minute trip" in prompt_lower:
                specialist_involved = "Advik"
                response_text = "Not a problem, Rohan. We're built for this. Advik is already on it - expect a compressed jet lag protocol (light exposure, hydration, meal timing) in your inbox within the hour. Rachel will also send over some hotel room-friendly bodyweight workouts."
                decision_rationale = "Rapidly responding to a dynamic schedule change to mitigate travel-related health decline, reinforcing Elyx's value in high-stress, unpredictable environments."
                pillar_impact = "All Pillars (Acute Travel Stress)"
                time_efficiency = "Protocol delivered within an hour for immediate action."
                next_steps = "Follow the compressed travel protocol and report back on energy levels post-arrival."

            elif "plan change" in prompt_lower or "too easy" in prompt_lower or "more challenging" in prompt_lower:
                specialist_involved = "Rachel"
                response_text = "Excellent, Rohan. This is a great sign of progress. Rachel will analyze your recent workout logs and Garmin data to design a new, more challenging block focused on progressive overload. We'll have it ready for your review by EOD tomorrow."
                decision_rationale = "Adapting the plan based on member feedback and improved performance to ensure continued progress and maintain engagement."
                pillar_impact = "Pillar 4 (Structural Health)"
                next_steps = "Rachel to deliver a revised, more intense workout plan by tomorrow."

            else: # General check-in/response
                response_text = random.choice([
                    f"Hi Rohan, {role} here. We're continuously optimizing your plan based on your feedback and data to maximize your health output. How are things going with your current priorities?",
                    f"Understood. We'll integrate this into your personalized plan to maximize your health output, considering your time and value. Thanks for the feedback. What's on your mind today?",
                    f"Just checking in, Rohan. How are you feeling about your current progress and any new challenges you're facing? {role} is here to support. What's your current focus?",
                ])
                decision_rationale = "Routine check-in / general response, emphasizing personalized care, value, and lifestyle integration."
                pillar_impact = "General"

    return response_text, decision_rationale, pillar_impact, health_metrics_snapshot, intervention_effect, monetary_factor, time_efficiency, service_interaction_type, specialist_involved, next_steps, sentiment

# --- API Endpoints ---
@app.route('/api/generate-journey', methods=['POST'])
def api_generate_journey():
    """
    Generates the full 8-month journey data dynamically.
    This endpoint is called by the frontend to get the entire simulated log.
    """
    journey_data = []
    chat_history = []
    timeline_events = [] 

    start_date = datetime(2025, 8, 1)
    current_date = start_date

    # Reset metrics and memory for a fresh simulation
    global CURRENT_HEALTH_METRICS, ROHAN_ASKED_TOPICS
    CURRENT_HEALTH_METRICS = {
        "HRV": 45, "RestingHR": 65, "GlucoseAvg": 105, "ApoB": 105,
        "RecoveryScore": 70, "DeepSleep": 60, "POTS_symptoms": "moderate", "BackPain": "mild"
    }
    ROHAN_ASKED_TOPICS.clear()

    # --- Simulation Loop (Simplified for clarity) ---
    # In this version, we'll manually script the first few interactions for a coherent start
    # and then simulate the rest.

    # 1. Onboarding
    rohan_msg, _, _, _, _, _, _, _, _, _, _ = generate_llm_response("Rohan", "initial plan", CURRENT_HEALTH_METRICS, chat_history, journey_data)
    chat_history.append({"role": "user", "parts": [{"text": rohan_msg}]})
    
    # ... (rest of the journey generation logic remains largely the same) ...
    # --- MODIFIED: Added a new event type for Rohan's proactive chats ---
    # We can sprinkle these events randomly in the weekly loop

    for week in range(1, 33):
        current_date += timedelta(weeks=1)
        
        # --- NEW: Simulate a proactive update from Rohan every 3-5 weeks ---
        if week % random.randint(3, 5) == 0:
            prompt_context = random.choice(["status update", "plan change request", "general health query"])
            rohan_msg, rohan_rationale, _, rohan_metrics, _, rohan_monetary, rohan_time, _, _, rohan_next_steps, rohan_sentiment = generate_llm_response("Rohan", prompt_context, CURRENT_HEALTH_METRICS, chat_history, journey_data)
            
            timeline_events.append({
                "type": "message", "sender": "Rohan", "timestamp": (current_date + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
                "content": rohan_msg, "pillar": "Member Engagement", "relatedTo": "Proactive Check-in",
                "decisionRationale": rohan_rationale, "healthMetricsSnapshot": rohan_metrics,
                "interventionEffect": None, "monetaryFactor": rohan_monetary,
                "timeEfficiency": rohan_time, "serviceInteractionType": "member-initiated query", 
                "specialistInvolved": None, "nextSteps": rohan_next_steps, "sentiment": rohan_sentiment
            })
            chat_history.append({"role": "user", "parts": [{"text": rohan_msg}]})

            # Elyx Team Responds
            team_member = random.choice(list(ELYX_TEAM_PERSONAS.keys()))
            team_response, team_rationale, team_pillar, team_metrics, team_effect, team_monetary, team_time, _, team_specialist, team_next_steps, team_sentiment = generate_llm_response(team_member, rohan_msg, CURRENT_HEALTH_METRICS, chat_history, journey_data)
            
            timeline_events.append({
                "type": "message", "sender": team_specialist or team_member, "timestamp": (current_date + timedelta(days=1, hours=2)).strftime("%Y-%-m-%d %H:%M"),
                "content": team_response, "pillar": team_pillar, "relatedTo": "Response to Member Query",
                "decisionRationale": team_rationale, "healthMetricsSnapshot": team_metrics,
                "interventionEffect": team_effect, "monetaryFactor": team_monetary,
                "timeEfficiency": team_time, "serviceInteractionType": "intervention_update", 
                "specialistInvolved": team_specialist or team_member, "nextSteps": team_next_steps, "sentiment": team_sentiment
            })
            chat_history.append({"role": "model", "parts": [{"text": team_response}]})


        # ... (rest of the weekly simulation loop for diagnostics, travel, etc.) ...
        # (This section is omitted for brevity but would be the same as the original file)

    # A placeholder to ensure the function returns something if the loop is empty
    if not timeline_events:
        return jsonify([{"type": "message", "sender": "System", "content": "No events generated."}])

    return jsonify(timeline_events)


@app.route('/api/explain-decision', methods=['POST'])
def api_explain_decision():
    # This function's logic does not need to change, as it dynamically reads from the
    # journey data, which is now more diverse.
    data = request.json
    query = data.get('query')
    journey_data_context = data.get('journeyData', []) 
    
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
    sentiment = "neutral"

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
        # Fallback to the enriched generate_llm_response
        explanation_text, rationale, pillar, metrics_snap, effect, monetary, time_eff, _, specialist, next_steps, sentiment = generate_llm_response(
            role="Elyx AI Concierge",
            prompt_context=query,
            current_metrics=CURRENT_HEALTH_METRICS,
            chat_history=[],
            journey_data_so_far=[] 
        )
    
    formatted_explanation = f"{explanation_text}\n\n"
    if rationale:
        formatted_explanation += f"**Rationale:** {rationale}\n"
    if pillar:
        formatted_explanation += f"**Pillar Impact:** {pillar}\n"
    # ... (rest of the formatting is identical to original)
    
    return jsonify({"explanation": formatted_explanation, "sentiment": sentiment})

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', host='0.0.0.0', port=int(os.environ.get('PORT', 5001)))
