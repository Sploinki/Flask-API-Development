"""
models.py

Defines SQLAlchemy models for the student management system:
- Subject: Represents academic subjects/courses
- Student: Represents students with encrypted personal information

The Student model uses RSA encryption for name storage to enhance privacy.
Relationships:
- One Subject can have many Students (one-to-many)
- Each Student must belong to one Subject
"""

from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy instance
db = SQLAlchemy()


class Subject(db.Model):
    """
    Subject/Course model.
    Attributes:
        id (int): Primary key
        name (str): Subject name, max length 100 chars
        students (relationship): One-to-many relationship with Student model
    """
    __tablename__ = 'subjects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    # Define relationship: one subject can have many students
    students = db.relationship('Student', backref='subject', lazy=True)

    def __repr__(self):
        """String representation of Subject."""
        return f"<Subject {self.name}>"


class Student(db.Model):
    """
    Student model with encrypted personal information.
    Attributes:
        id (int): Primary key
        name_encrypted (bytes): RSA encrypted student name
        age (int): Student age
        email (str): Student email, unique
        subject_id (int): Foreign key to subjects table
    """
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    # Stores RSA encrypted name
    name_encrypted = db.Column(db.LargeBinary, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    subject_id = db.Column(
        db.Integer,
        db.ForeignKey('subjects.id'),
        nullable=False,
        doc="References the subject this student is enrolled in"
    )

    def __repr__(self):
        """String representation of Student, excluding encrypted data."""
        return f"<Student ID={self.id}, Subject={self.subject_id}>"
