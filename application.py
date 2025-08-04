import json
from flask import Flask, jsonify
from flask_cors import CORS

# App version for deployment tracking
APP_VERSION = "1.0.0"

# Create Flask app instance; AWS expects the variable to be named 'application'
application = Flask(__name__)
# Enable Cross-Origin Resource Sharing (CORS) for the application
CORS(application)


# Home Route
@application.route("/", methods=["GET"])
def home():
    return f"Home Route - Version {APP_VERSION}"


# Version Route
@application.route("/version", methods=["GET"])
def version():
    return jsonify({
        "version": APP_VERSION,
        "status": "running"
    })


# Users Route (Get User Information)
@application.route("/users", methods=["GET"])
def get_users():
    """Return list of users from data/users.json"""
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


# Run the app in debug mode if executed directly
if __name__ == "__main__":
    application.run(debug=True)
