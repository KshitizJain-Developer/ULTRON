from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

# Allow the website to communicate with this API
CORS(app)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "ultron.db"


def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():

    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS security_registrations (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT NOT NULL,

            country TEXT NOT NULL,

            purpose TEXT NOT NULL,

            message TEXT,

            created_at TEXT NOT NULL

        )
    """)

    connection.commit()
    connection.close()


@app.route("/")
def home():

    return jsonify({
        "system": "ULTRON",
        "status": "ONLINE",
        "service": "Security Registration API"
    })


@app.route("/api/register", methods=["POST"])
def register():

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "success": False,
            "error": "Invalid request."
        }), 400


    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip()
    country = str(data.get("country", "")).strip()
    purpose = str(data.get("purpose", "")).strip()
    message = str(data.get("message", "")).strip()


    # Basic validation

    if not name:
        return jsonify({
            "success": False,
            "error": "Name is required."
        }), 400


    if not email or "@" not in email:
        return jsonify({
            "success": False,
            "error": "Valid email is required."
        }), 400


    if not country:
        return jsonify({
            "success": False,
            "error": "Country is required."
        }), 400


    allowed_purposes = {
        "personal",
        "education",
        "development",
        "research",
        "other"
    }

    if purpose not in allowed_purposes:
        return jsonify({
            "success": False,
            "error": "Invalid purpose."
        }), 400


    # Prevent unnecessarily large input

    if len(name) > 80:
        return jsonify({
            "success": False,
            "error": "Name is too long."
        }), 400


    if len(email) > 120:
        return jsonify({
            "success": False,
            "error": "Email is too long."
        }), 400


    if len(country) > 60:
        return jsonify({
            "success": False,
            "error": "Country name is too long."
        }), 400


    if len(message) > 500:
        return jsonify({
            "success": False,
            "error": "Message is too long."
        }), 400


    created_at = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )


    connection = get_db()

    cursor = connection.execute("""
        INSERT INTO security_registrations
        (
            name,
            email,
            country,
            purpose,
            message,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        name,
        email,
        country,
        purpose,
        message,
        created_at
    ))


    registration_id = cursor.lastrowid

    connection.commit()
    connection.close()


    return jsonify({

        "success": True,

        "message":
            "ULTRON security registration completed.",

        "registration_id":
            registration_id

    })


if __name__ == "__main__":

    initialize_database()

    print()
    print("=" * 55)
    print("             ULTRON SECURITY API")
    print("=" * 55)
    print()
    print("Database :", DB_PATH)
    print("Status   : ONLINE")
    print("API      : http://127.0.0.1:5000")
    print()
    print("Press CTRL+C to stop the server.")
    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )