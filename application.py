import json
import os
from flask import Flask, jsonify, request, session
import uuid
from flask_cors import CORS
from config import API_KEY, SECRET_KEY  # RSA_PASSPHRASE
from helpers import validate_api_key
from helpers import add_user_to_session, load_sessions
from helpers import load_subjects, is_duplicate_subject, save_subjects_atomic
from helpers import load_students, is_duplicate_student, save_students_atomic
from datetime import timedelta
from models import db
from rsa_utils import generate_or_load_keys
from datetime import datetime
from filelock import FileLock
from typing import Dict, Union

APP_VERSION = "1.0.0"

# Flask app; AWS expects the variable to be named 'application'
application = Flask(__name__)
CORS(
    application,
    supports_credentials=True,
    origins=["*"]
)

# Configure SQLAlchemy
application.config.from_object('config')

# Initialize DB
db.init_app(application)

# Generate or load RSA keys (persisted in root/keys)
private_key, public_key = generate_or_load_keys()

# Secret key for Flask sessions
application.secret_key = SECRET_KEY
application.permanent_session_lifetime = timedelta(hours=1)


@application.route("/", methods=["GET"])
def home():
    """Return a simple home message with app version."""
    return f"Home Route - Version {APP_VERSION} | Database Setup Complete"


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


@application.route("/add_subject", methods=["POST"])
def add_subject() -> tuple[Dict[str, Union[str, bool]], int]:
    """
    Add a new subject to subjects.json with thread-safe file operations.

    Expected JSON input:
        {
            "subject_name": "<string>"
        }

    Returns:
        tuple: (JSON response, HTTP status code)
            Success (201): {
                "message": "Subject added successfully",
                "subject_id": "<uuid>",
                "subject_name": "<string>"
            }
            Error (400/409/500): {
                "error": "<error message>"
            }
    """
    # Validate API key
    validation_response = validate_api_key()
    if validation_response:
        return validation_response

    subjects_path = "data/subjects.json"
    lock_path = f"{subjects_path}.lock"

    try:
        # Validate and sanitize input
        data = request.get_json()
        if not data or "subject_name" not in data:
            return jsonify({"error": "Subject name is required"}), 400

        subject_name = str(data["subject_name"]).strip()
        if not subject_name:
            return jsonify({"error": "Subject name cannot be empty"}), 400
        if len(subject_name) > 100:
            return jsonify(
                {"error": "Subject name too long (max 100 chars)"}
            ), 400

        # Ensure data directory exists
        os.makedirs(os.path.dirname(subjects_path), exist_ok=True)

        # Thread-safe file operations
        with FileLock(lock_path):
            subjects = load_subjects(subjects_path)
            # Check for duplicate subject name (case insensitive)
            if is_duplicate_subject(subjects, subject_name):
                return jsonify({"error": "Subject name already exists"}), 409

            # Create and add new subject
            subject_id = str(uuid.uuid4())
            subject_entry = {
                "subject_id": subject_id,
                "subject_name": subject_name,
                "created_at": datetime.utcnow().isoformat()
            }
            subjects.append(subject_entry)

            # Save changes atomically
            if not save_subjects_atomic(subjects, subjects_path):
                return jsonify({"error": "Failed to save subject"}), 500

            return jsonify({
                "message": "Subject added successfully",
                "subject_id": subject_id,
                "subject_name": subject_name
            }), 201

    except Exception as e:
        application.logger.error(f"Error in add_subject: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@application.route("/add_student", methods=["POST"])
def add_student() -> tuple[Dict[str, Union[str, bool]], int]:
    """
    Add a new student to students.json and associate with a subject.

    Expected JSON input:
        {
            "name": "<string>",
            "age": <int>,
            "email": "<string>",
            "subject_id": "<uuid>"
        }

    Returns:
        tuple: (JSON response, HTTP status code)
            Success (201): {
                "message": "Student added successfully",
                "student_id": "<uuid>"
            }
            Error (400/403/404/409/500): {
                "error": "<error message>"
            }
    """
    students_path = "data/students.json"
    subjects_path = "data/subjects.json"
    lock_path = f"{students_path}.lock"

    try:
        # --- 1. API Key Validation ---
        validation_response = validate_api_key()
        if validation_response:
            return validation_response

        # --- 2. Input Validation ---
        data = request.get_json()
        required_fields = ["name", "age", "email", "subject_id"]
        if not data or not all(
            field in data and data[field] for field in required_fields
        ):
            return jsonify(
                {"error": "All fields are required and must be non-empty"}
            ), 400

        name = str(data["name"]).strip()
        email = str(data["email"]).strip().lower()
        subject_id = str(data["subject_id"]).strip()

        # Robust age validation
        age_raw = data.get("age")
        try:
            age = int(age_raw)
        except (TypeError, ValueError):
            return jsonify({"error": "Age must be a positive integer"}), 400

        if not name or not email or not subject_id or age <= 0:
            return jsonify({"error": "Invalid field values"}), 400
        if len(name) > 100 or len(email) > 100:
            return jsonify({"error": "Name/email too long"}), 400

        # --- 3. Validate Subject ID Existence ---
        subjects = load_subjects(subjects_path)
        if not any(s.get("subject_id") == subject_id for s in subjects):
            return jsonify({"error": "Invalid subject_id"}), 404

        # --- 4. Thread-safe File Lock & Load Students ---
        os.makedirs(os.path.dirname(students_path), exist_ok=True)

        with FileLock(lock_path):
            students = load_students(students_path)

            # Ensure all stored emails are compared in lowercase
            students_lower = [
                {**student, "email": student.get("email", "").lower()}
                for student in students
            ]
            if is_duplicate_student(students_lower, email):
                return jsonify({"error": "Email already exists"}), 409

            # --- 5. RSA Encrypt Name ---
            from rsa_utils import generate_or_load_keys, encrypt_name
            _, public_key = generate_or_load_keys()
            encrypted_name_bytes = encrypt_name(name, public_key)
            # Store as hex for JSON compatibility
            encrypted_name_b64 = encrypted_name_bytes.hex()

            # --- 6. Create Student Entry ---
            student_id = str(uuid.uuid4())
            student_entry = {
                "student_id": student_id,
                "name_encrypted": encrypted_name_b64,
                "age": age,
                "email": email,
                "subject_id": subject_id,
                "created_at": datetime.utcnow().isoformat()
            }

            students.append(student_entry)

            if not save_students_atomic(students, students_path):
                return jsonify({"error": "Failed to save student"}), 500
            return jsonify({
                "message": "Student added successfully",
                "student_id": student_id
            }), 201

    except Exception as e:
        application.logger.error(
            f"Error in add_student: {str(e)}", exc_info=True
        )
        return jsonify({"error": "Internal server error"}), 500


@application.route("/students_by_subject", methods=["POST"])
def get_students_by_subject() -> tuple[Dict[str, Union[str, list]], int]:
    """
    Retrieve all students enrolled in a particular subject.

    Expected JSON input:
        {
            "subject_id": "<uuid>"
        }

    Returns:
        Success (200):
        {
            "subject_id": "<uuid>",
            "students": [
                {
                    "student_id": "<uuid>",
                    "name": "<decrypted string>",
                    "age": <int>,
                    "email": "<string>",
                    "created_at": "<timestamp>"
                },
                ...
            ]
        }

        Error (400/404/500):
        {
            "error": "<error message>"
        }
    """
    subjects_path = "data/subjects.json"
    students_path = "data/students.json"

    try:
        # --- 1. API Key Validation ---
        validation_response = validate_api_key()
        if validation_response:
            return validation_response

        # --- 2. Validate Input ---
        data = request.get_json()
        subject_id = str(data.get("subject_id", "")).strip()

        if not subject_id:
            return jsonify({"error": "subject_id is required"}), 400

        # --- 3. Validate Subject Exists ---
        subjects = load_subjects(subjects_path)
        if not any(s.get("subject_id") == subject_id for s in subjects):
            return jsonify({"error": "Subject not found"}), 404

        # --- 4. Load and Filter Students ---
        students = load_students(students_path)
        filtered_students = [
            s for s in students if s.get("subject_id") == subject_id
        ]

        # --- 5. Decrypt Names ---
        from rsa_utils import generate_or_load_keys, decrypt_name
        private_key, _ = generate_or_load_keys()

        students_output = []
        for s in filtered_students:
            try:
                decrypted_name = decrypt_name(
                                bytes.fromhex(s["name_encrypted"]), private_key
                                )
            except Exception:
                decrypted_name = "<decryption error>"

            students_output.append({
                "student_id": s["student_id"],
                "name": decrypted_name,
                "age": s["age"],
                "email": s["email"],
                "created_at": s.get("created_at", "N/A")
            })

        return jsonify({
            "subject_id": subject_id,
            "students": students_output
        }), 200

    except Exception as e:
        application.logger.error(
            f"Error in get_students_by_subject: {str(e)}", exc_info=True
        )
        return jsonify({"error": "Internal server error"}), 500


@application.route("/update_student", methods=["PUT"])
def update_student() -> tuple[Dict[str, Union[str, bool]], int]:
    """
    Update an existing student's information in students.json.

    Expected JSON input:
        {
            "student_id": "<uuid>",  # required
            "name": "<string>",      # optional
            "age": <int>,            # optional
            "email": "<string>",     # optional
            "subject_id": "<uuid>"   # optional
        }

    Returns:
        tuple: (JSON response, HTTP status code)
            Success (200): {
                "message": "Student updated successfully",
                "student_id": "<uuid>"
            }
            Error (400/401/403/404/409/500): {
                "error": "<error message>"
            }
    """
    students_path = "data/students.json"
    subjects_path = "data/subjects.json"
    lock_path = f"{students_path}.lock"

    try:
        # --- 1. API Key Validation ---
        validation_response = validate_api_key()
        if validation_response:
            return validation_response

        # --- 2. Parse and validate input ---
        data = request.get_json()
        student_id = str(data.get("student_id", "")).strip()

        if not student_id:
            return jsonify({"error": "student_id is required"}), 400

        name = data.get("name")
        age = data.get("age")
        email = data.get("email")
        subject_id = data.get("subject_id")

        if name is not None:
            if not isinstance(name, str) or len(name.strip()) > 100:
                return jsonify({"error": "Invalid name"}), 400

        if email is not None:
            if not isinstance(email, str) or len(email.strip()) > 100:
                return jsonify({"error": "Invalid email"}), 400

        if age is not None:
            try:
                age = int(age)
                if age <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid age"}), 400

        if subject_id is not None:
            subject_id = str(subject_id).strip()
            subjects = load_subjects(subjects_path)
            if not any(s.get("subject_id") == subject_id for s in subjects):
                return jsonify({"error": "Subject ID does not exist"}), 404

        # --- 3. Load and update student record ---
        os.makedirs(os.path.dirname(students_path), exist_ok=True)

        with FileLock(lock_path):
            students = load_students(students_path)
            student_found = False

            for student in students:
                if student.get("student_id") == student_id:
                    student_found = True

                    if name:
                        from rsa_utils import (
                            generate_or_load_keys,
                            encrypt_name
                        )
                        _, public_key = generate_or_load_keys()
                        encrypted = encrypt_name(name.strip(), public_key)
                        student["name_encrypted"] = encrypted.hex()

                    if age:
                        student["age"] = age

                    if email:
                        lower_email = email.strip().lower()
                        for other in students:
                            if (other.get("student_id") != student_id and
                                    other.get("email", "").lower()
                                    == lower_email):
                                return jsonify(
                                    {"error": "Email already exists"}
                                ), 409
                        student["email"] = lower_email

                    if subject_id:
                        student["subject_id"] = subject_id

                    student["updated_at"] = datetime.utcnow().isoformat()
                    break

            if not student_found:
                return jsonify({"error": "Student not found"}), 404

            if not save_students_atomic(students, students_path):
                return jsonify(
                    {"error": "Failed to save student updates"}
                ), 500

            return jsonify({
                "message": "Student updated successfully",
                "student_id": student_id
            }), 200

    except Exception as e:
        application.logger.error(
            f"Error in update_student: {str(e)}",
            exc_info=True
        )
        return jsonify({"error": "Internal server error"}), 500


@application.route("/student/<student_id>", methods=["GET"])
def get_student(student_id: str) -> tuple[Dict[str, Union[str, bool]], int]:
    """
    Retrieve a specific student's data by ID.

    URL Parameter:
        student_id (str): UUID of the student

    Headers:
        x-api-key: API key for authentication

    Returns:
        tuple: (JSON response, HTTP status code)
            Success (200): {
                "student_id": "<uuid>",
                "name": "<decrypted name>",
                "age": <int>,
                "email": "<string>",
                "subject_id": "<uuid>",
                ...
            }
            Error (400/401/403/404/500): {
                "error": "<error message>"
            }
    """
    students_path = "data/students.json"

    try:
        # --- 1. API Key Validation ---
        validation_response = validate_api_key()
        if validation_response:
            return validation_response

        # --- 2. Load Students File ---
        students = load_students(students_path)
        if not students:
            return jsonify({"error": "No students found"}), 404

        # --- 3. Find Matching Student ---
        student = next(
            (s for s in students if s.get("student_id") == student_id), None
        )
        if not student:
            return jsonify({"error": "Student not found"}), 404

        # --- 4. Decrypt Name ---
        from rsa_utils import generate_or_load_keys, decrypt_name
        private_key, _ = generate_or_load_keys()

        try:
            encrypted_name_hex = student.get("name_encrypted", "")
            encrypted_name_bytes = bytes.fromhex(encrypted_name_hex)
            decrypted_name = decrypt_name(encrypted_name_bytes, private_key)
        except Exception:
            decrypted_name = "Decryption failed"

        # --- 5. Build Response ---
        student_response = {
            "student_id": student.get("student_id"),
            "name": decrypted_name,
            "age": student.get("age"),
            "email": student.get("email"),
            "subject_id": student.get("subject_id"),
            "created_at": student.get("created_at"),
            "updated_at": student.get("updated_at")
        }

        return jsonify(student_response), 200

    except Exception as e:
        application.logger.error(
            f"Error in get_student: {str(e)}", exc_info=True
        )
        return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    with application.app_context():
        os.makedirs("root/database", exist_ok=True)
        db.create_all()
    application.run(debug=True)
