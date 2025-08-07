"""
helpers.py

Utility functions for managing user sessions using a JSON file.
"""

import json
import uuid
import os
from config import SESSION_FILE, API_KEY
from typing import Dict, List
from flask import current_app, request, jsonify


def validate_api_key():
    api_key = request.headers.get("x-api-key")
    if not api_key:
        return jsonify({"error": "API key required"}), 401
    if api_key != API_KEY:
        return jsonify({"error": "Unauthorized access"}), 403
    return None  # Means valid


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


def load_subjects(file_path: str) -> List[Dict]:
    """Load subjects from JSON file or return empty list."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as e:
        current_app.logger.error(f"Corrupted subjects file: {str(e)}")
        raise


def is_duplicate_subject(subjects: List[Dict], name: str) -> bool:
    """Check if subject name already exists (case insensitive)."""
    return any(
        subject.get("subject_name", "").lower() == name.lower()
        for subject in subjects
    )


def save_subjects_atomic(subjects: List[Dict], file_path: str) -> bool:
    """Save subjects to file atomically using a temporary file."""
    temp_path = f"{file_path}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(subjects, f, indent=4)
        os.replace(temp_path, file_path)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to save subjects: {str(e)}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False


def load_students(file_path: str) -> List[Dict]:
    """Load students from JSON file or return empty list."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as e:
        current_app.logger.error(f"Corrupted students file: {str(e)}")
        raise


def is_duplicate_student(students: List[Dict], email: str) -> bool:
    """Check if student email already exists (case insensitive)."""
    return any(
        student.get("email", "").lower() == email.lower()
        for student in students
    )


def save_students_atomic(students: List[Dict], file_path: str) -> bool:
    """Save students to file atomically using a temporary file."""
    temp_path = f"{file_path}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(students, f, indent=4)
        os.replace(temp_path, file_path)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to save students: {str(e)}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False
