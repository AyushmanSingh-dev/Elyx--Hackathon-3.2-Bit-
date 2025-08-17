import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, time

# Initialize Flask App
app = Flask(__name__)

# Configure CORS
frontend_url = os.getenv("FRONTEND_URL", "*") 
CORS(app, resources={r"/api/*": {"origins": frontend_url}})

# --- Data Loading ---
# Use a robust path to find the JSON file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE_PATH = os.path.join(BASE_DIR, 'Elyx_Sarah_Tan_Conversation_Log_8_Months.json')

try:
    with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
        conversation_log = json.load(f)
except FileNotFoundError:
    print(f"FATAL ERROR: The data file {JSON_FILE_PATH} was not found.")
    conversation_log = []

# --- Specialist Data (for the new section) ---
specialists = [
    {
        "id": "dr_chen",
        "name": "Dr. Evelyn Chen",
        "role": "Primary Physician",
        "specialty": "Internal Medicine, Longevity",
        "bio": "Dr. Chen is a board-certified internist with a focus on preventative medicine and healthspan optimization.",
        "image_url": "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=500"
    },
    {
        "id": "coach_david",
        "name": "David Lee",
        "role": "Health & Performance Coach",
        "specialty": "Exercise Physiology, Nutrition",
        "bio": "David holds a M.S. in Exercise Physiology and specializes in creating sustainable fitness and nutrition plans for busy professionals.",
        "image_url": "https://images.unsplash.com/photo-1531384441138-2736e62e0919?w=500"
    },
    {
        "id": "care_coordinator_maria",
        "name": "Maria Garcia",
        "role": "Care Coordinator",
        "specialty": "Member Logistics & Support",
        "bio": "Maria is the organizational backbone of your Elyx journey, coordinating schedules, tests, and communication.",
        "image_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=500"
    }
]

# --- API Endpoints ---

@app.route('/')
def index():
    return jsonify({"status": "ok", "message": "Welcome to the Elyx Backend API!"})

@app.route('/api/profile')
def get_profile():
    return jsonify({
        "name": "Sarah Tan",
        "age": 42,
        "occupation": "Investment Banker",
        "chronic_condition": "High Cholesterol",
    })

@app.route('/api/journey')
def get_journey():
    journey_events = [
        {
            "date": msg["timestamp"], "title": msg["content"],
            "type": next((t.replace('event_', '') for t in msg["tags"] if t.startswith('event_')), 'general'),
            "decision_id": msg["linked_decision_id"]
        }
        for msg in conversation_log if "journey_event" in msg["tags"]
    ]
    return jsonify(sorted(journey_events, key=lambda x: x['date'], reverse=True))

# NEW: Endpoint for the full message history
@app.route('/api/messages')
def get_messages():
    return jsonify(sorted(conversation_log, key=lambda x: x['timestamp']))

# NEW: Endpoint for the specialists list
@app.route('/api/specialists')
def get_specialists():
    return jsonify(specialists)

@app.route('/api/snapshot')
def get_snapshot():
    date_str = request.args.get('date')
    if not date_str: return jsonify({"error": "date is required"}), 400
    snapshot_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
    relevant_logs = [msg for msg in conversation_log if datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00')).date() <= snapshot_date]
    
    def find_last(tag):
        return next((msg["content"] for msg in reversed(relevant_logs) if tag in msg["tags"]), "No data.")

    communications = [msg for msg in conversation_log if datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00')).date() == snapshot_date]
    return jsonify({
        "activePlan": find_last('plan_update'),
        "activeMedications": find_last('medication_start') or "No active medications.",
        "keyMetrics": {"ldl": find_last('biomarker_ldl')},
        "communications": communications
    })

@app.route('/api/decision/<decision_id>')
def get_decision(decision_id):
    rationales = {
        'decision_rosuvastatin_01': "Baseline LDL was high. Diet/exercise alone showed insufficient improvement. A low-dose statin was recommended to reduce long-term cardiovascular risk.",
        'decision_stress_plan_01': "Wearable data showed declining sleep quality. An intervention focusing on stress management was prioritized over increasing physical intensity."
    }
    evidence = [msg for msg in conversation_log if msg.get("linked_decision_id") == decision_id]
    title = next((msg["content"] for msg in evidence if "journey_event" in msg["tags"]), "Decision Details")
    return jsonify({
        "decisionTitle": title, "rationale": rationales.get(decision_id, "No rationale."),
        "linkedEvidence": sorted(evidence, key=lambda x: x['timestamp'])
    })

if __name__ == '__main__':
    app.run(port=3001, debug=True)
