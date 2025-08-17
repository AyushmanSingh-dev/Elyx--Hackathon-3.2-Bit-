import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, time

# Initialize Flask App and enable Cross-Origin Resource Sharing (CORS)
app = Flask(__name__)

# In a production environment like Render, you'll set the FRONTEND_URL.
# For local testing, it might fall back to a default localhost port.
frontend_url = os.getenv("FRONTEND_URL", "*") # Use "*" for simplicity or specify a default

CORS(app, resources={r"/api/*": {"origins": frontend_url}})


# Load the entire conversation log into memory on startup
with open('Elyx_Sarah_Tan_Conversation_Log.json', 'r', encoding='utf-8') as f:
    conversation_log = json.load(f)

# --- API Endpoints ---

@app.route('/api/member/sarah_tan/profile')
def get_profile():
    """Serves the static member profile."""
    return jsonify({
        "name": "Sarah Tan",
        "age": 42,
        "occupation": "Investment Banker",
        "chronic_condition": "High Cholesterol",
    })

@app.route('/api/member/sarah_tan/journey')
def get_journey():
    """Extracts and serves major timeline events from the log."""
    journey_events = [
        {
            "date": msg["timestamp"],
            "title": msg["content"],
            "type": next((t.replace('event_', '') for t in msg["tags"] if t.startswith('event_')), 'general'),
            "decision_id": msg["linked_decision_id"]
        }
        for msg in conversation_log if "journey_event" in msg["tags"]
    ]
    # Sort events descending by date (most recent first)
    sorted_journey = sorted(journey_events, key=lambda x: x['date'], reverse=True)
    return jsonify(sorted_journey)

@app.route('/api/member/sarah_tan/snapshot')
def get_snapshot():
    """Provides a detailed snapshot of the member's status on a given day."""
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({"error": "date parameter is required"}), 400

    snapshot_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
    
    # Get all logs on or before the snapshot date
    relevant_logs = [msg for msg in conversation_log if datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00')).date() <= snapshot_date]

    def find_last_event(tag):
        for msg in reversed(relevant_logs):
            if tag in msg["tags"]:
                return msg["content"]
        return "No data available."

    # Communications for the specific day
    start_of_day = datetime.combine(snapshot_date, time.min)
    end_of_day = datetime.combine(snapshot_date, time.max)
    
    communications_on_day = [
        msg for msg in conversation_log 
        if start_of_day <= datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00')) <= end_of_day
    ]

    snapshot = {
        "activePlan": find_last_event('plan_update'),
        "activeMedications": find_last_event('medication_start') or "No active medications.",
        "keyMetrics": {"ldl": find_last_event('biomarker_ldl')},
        "communications": communications_on_day
    }
    return jsonify(snapshot)

@app.route('/api/decision/<decision_id>')
def get_decision(decision_id):
    """Retrieves the rationale and evidence for a specific decision."""
    rationales = {
        'decision_rosuvastatin_01': "Baseline LDL was high. Diet/exercise alone showed insufficient improvement. A low-dose statin was recommended to reduce long-term cardiovascular risk after discussing benefits and risks.",
        'decision_stress_plan_01': "Wearable data showed declining sleep quality and HRV. An intervention focusing on stress management was prioritized over increasing physical intensity."
    }
    
    linked_evidence = [msg for msg in conversation_log if msg.get("linked_decision_id") == decision_id]
    
    title = next((msg["content"] for msg in linked_evidence if "journey_event" in msg["tags"]), "Decision Details")

    return jsonify({
        "decisionTitle": title,
        "rationale": rationales.get(decision_id, "No rationale available."),
        "linkedEvidence": sorted(linked_evidence, key=lambda x: x['timestamp'])
    })

@app.route('/api/internal/metrics')
def get_metrics():
    """Calculates and serves internal resource allocation metrics."""
    doctor_consults = sum(1 for msg in conversation_log if "consultation" in msg["tags"])
    coaching_calls = sum(1 for msg in conversation_log if "coaching_call" in msg["tags"])
    plan_updates = sum(1 for msg in conversation_log if "plan_update" in msg["tags"])
    
    doctor_hours = doctor_consults * 0.5
    coach_hours = (coaching_calls * 0.5) + (plan_updates * 0.25)
    
    return jsonify({
        "doctor_consult_hours": doctor_hours,
        "health_coach_hours": coach_hours,
    })

# This part is for local execution. Render will use the Gunicorn start command.
if __name__ == '__main__':
    # For local testing, you can run `python backend.py`
    app.run(port=3001, debug=True)
