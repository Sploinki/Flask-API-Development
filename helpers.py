"""
helpers.py

Utility functions for managing user sessions using a JSON file.
"""

import json
import uuid
import os
from config import SESSION_FILE


# Load sessions from JSON
def load_sessions():
    """Load session dictionary from file or return empty dict if not found."""
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


# Save sessions to JSON
def save_sessions(session_data):
    """Ensure the directory exists before saving"""
    os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=4)


# Add user to session and return session ID
def add_user_to_session(user_data):
    """
    Args:
        user_data (dict): Data for the user to store in the session.

    Returns:
        str: The generated session ID.
    """
    sessions = load_sessions()
    session_id = str(uuid.uuid4())  # Generate a unique session ID
    sessions[session_id] = user_data
    save_sessions(sessions)
    return session_id
