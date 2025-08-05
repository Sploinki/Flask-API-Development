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
