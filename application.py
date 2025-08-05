import json
from flask import Flask, jsonify, request, session
from flask_cors import CORS
from config import API_KEY, SECRET_KEY
from helpers import add_user_to_session, load_sessions
from datetime import timedelta

APP_VERSION = "1.0.0"

# Flask app; AWS expects the variable to be named 'application'
application = Flask(__name__)
CORS(
    application,
    supports_credentials=True
)

# Secret key for Flask sessions
application.secret_key = SECRET_KEY
application.permanent_session_lifetime = timedelta(hours=1)


@application.route("/", methods=["GET"])
def home():
    """Return a simple home message with app version."""
    return f"Home Route - Version {APP_VERSION}"


@application.route("/version", methods=["GET"])
def version():
    """Return the current app version and running status."""
    return jsonify({
        "version": APP_VERSION,
        "status": "running"
    })


@application.route("/users", methods=["GET"])
def get_users():
    """Return list of users from data/users.json."""
    try:
        with open("data/users.json", "r", encoding="utf-8") as file:
            users = json.load(file)
        return jsonify(users), 200
    except FileNotFoundError:
        return jsonify({"error": "users.json file not found"}), 404
    except json.JSONDecodeError:
        return jsonify({"error": "Error decoding JSON file"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@application.route('/add_user_session', methods=['POST'])
def add_user_session():
    """Add a user to Flask session and return session ID."""
    try:
        # --- 1. Validate API key ---
        api_key = request.headers.get('x-api-key')
        if not api_key:
            return jsonify({"error": "API key required"}), 401
        if api_key != API_KEY:
            return jsonify({"error": "Unauthorized access"}), 403

        # --- 2. Parse and validate input JSON ---
        data = request.get_json()
        required_fields = ["name", "age", "gender", "email"]

        if not data or not all(
            field in data and data[field] for field in required_fields
        ):
            return jsonify({
                "error": "Invalid input, require name, age, gender, and email"
            }), 400

        # --- 3. Check duplicate in users.json ---
        try:
            with open("data/users.json", "r", encoding="utf-8") as file:
                users = json.load(file)
        except FileNotFoundError:
            users = []

        if any(user.get("email") == data["email"] for user in users):
            return jsonify({
                "error": "Email already exists in users database"
            }), 409

        # --- 4. Check duplicate in session storage (sessions.json) ---
        sessions = load_sessions()
        if any(user.get("email")
               == data["email"] for user in sessions.values()):
            return jsonify({
                "error": "Email already exists in another session"
            }), 409

        # --- 5. Add user to session (sessions.json) ---
        session_id = add_user_to_session(data)
        application.permanent_session_lifetime = timedelta(hours=1)
        session["session_id"] = session_id  # Save in Flask session

        return jsonify({
            "message": "User added to session",
            "session_id": session_id,
            "flask_session": session.get("session_id")
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@application.route('/get_user_info', methods=['POST'])
def get_user_info():
    try:
        # Validate API key
        api_key = request.headers.get('x-api-key')
        if not api_key:
            return jsonify({"error": "API key required"}), 401
        if api_key != API_KEY:
            return jsonify({"error": "Unauthorized access"}), 403

        # Try Flask session first
        session_id = session.get("session_id")

        # Fallback to JSON body
        if not session_id:
            data = request.get_json(silent=True) or {}
            session_id = data.get("session_id")

        if not session_id:
            return jsonify({"error": "Session ID required"}), 400

        # Load sessions from file
        sessions = load_sessions()
        user_info = sessions.get(session_id)
        if not user_info:
            return jsonify({"error": "Session ID does not exist"}), 404

        return jsonify({
            "session_id": session_id,
            "user_info": user_info
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    application.run(debug=True)
