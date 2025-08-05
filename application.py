import json
import uuid
from flask import Flask, jsonify, request
from flask_cors import CORS
from config import API_KEY
from helpers import load_sessions, save_sessions

APP_VERSION = "1.0.0"

# Flask app; AWS expects the variable to be named 'application'
application = Flask(__name__)
CORS(application)


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
    """Add a user to session storage and return session ID."""
    try:
        api_key = request.headers.get('x-api-key')
        if not api_key:
            return jsonify({"error": "API key required"}), 401
        if api_key != API_KEY:
            return jsonify({"error": "Unauthorized access"}), 403

        data = request.get_json()
        required_fields = ["name", "age", "gender", "email"]

        # Validate required fields are present and non-empty
        if not data or not all(
            field in data and data[field] for field in required_fields
        ):
            return jsonify({
                "error": "Invalid input, require name, age, gender, and email"
            }), 400

        sessions = load_sessions()

        # Load users.json to check for duplicate emails
        try:
            with open("data/users.json", "r", encoding="utf-8") as file:
                users = json.load(file)
        except FileNotFoundError:
            users = []

        # Check for duplicate email in sessions
        if any(
            session.get("email") == data["email"]
            for session in sessions.values()
        ):
            return jsonify({
                "error": "Email already exists in another session"
            }), 409

        # Check for duplicate email in users.json
        if any(user.get("email") == data["email"] for user in users):
            return jsonify({
                "error": "Email already exists in users database"
            }), 409

        # Create new session
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "name": data["name"],
            "age": data["age"],
            "gender": data["gender"],
            "email": data["email"]
        }

        save_sessions(sessions)

        return jsonify({
            "message": "User added to session",
            "session_id": session_id
        }), 201

    except Exception as e:
        # Do not expose internal errors to the client
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    application.run(debug=True)
