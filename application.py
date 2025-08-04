from flask import Flask
from flask_cors import CORS
from flask import jsonify

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


# Run the app in debug mode if executed directly
if __name__ == "__main__":
    application.run(debug=True)
