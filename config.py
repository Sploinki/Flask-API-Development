"""
config.py

Loads environment variables and sets configuration constants
for the application.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# API key for authentication, loaded from .env file
API_KEY = os.getenv("API_KEY")

# Path to the session data JSON file
SESSION_FILE = "root/database/session/session.json"

# Required for Flask's session
SECRET_KEY = os.getenv("SECRET_SESSION_KEY")

# Database
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = f"sqlite:///{
    os.path.join(BASE_DIR, 'root/database/application.db')
}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

# RSA configuration
RSA_PASSPHRASE = os.getenv("RSA_PASSPHRASE", "defaultpass")
