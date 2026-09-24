from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "ultron.db"

app = Flask(__name__)
CORS(app)

ADMIN_PASSWORD = os.environ.get("ULTRON_ADMIN_PASSWORD")


def initialize_database():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute("""
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


@app.get("/")
def home():
    return jsonify({
        "system": "ULTRON",
        "status": "ONLINE",
        "service": "Security Registration API"
    })


@app.post("/api/register")
def register():

    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip()
    country = str(data.get("country", "")).strip()
    purpose = str(data.get("purpose", "")).strip()
    message = str(data.get("message", "")).strip()

    if not name or not email or not country or not purpose:
        return jsonify({
            "success": False,
            "error": "Required fields are missing."
        }), 400

    if (
        len(name) > 80
        or len(email) > 120
        or len(country) > 60
        or len(message) > 500
    ):
        return jsonify({
            "success": False,
            "error": "One or more fields are too long."
        }), 400

    created_at = datetime.now(
        timezone(timedelta(hours=5, minutes=30))
    ).isoformat()

    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO security_registrations
        (name, email, country, purpose, message, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        name,
        email,
        country,
        purpose,
        message,
        created_at
    ))

    connection.commit()
    connection.close()

    return jsonify({
        "success": True,
        "message": "Registration saved successfully."
    })


@app.get("/admin")
def admin():

    password = request.args.get("password", "")

    if not ADMIN_PASSWORD:
        return "Admin password is not configured.", 500

    if password != ADMIN_PASSWORD:
        return """
        <h2>ULTRON ADMIN</h2>
        <p>Unauthorized.</p>
        """, 401

    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, name, email, country, purpose, message, created_at
        FROM security_registrations
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    connection.close()

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>ULTRON Admin</title>

        <style>
            body {
                background: #05080d;
                color: #eaffff;
                font-family: Arial, sans-serif;
                padding: 30px;
            }

            h1 {
                color: #63eaff;
            }

            .count {
                color: #7f969d;
                margin-bottom: 20px;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                background: #080e14;
            }

            th, td {
                padding: 12px;
                border: 1px solid #18313a;
                text-align: left;
                font-size: 13px;
            }

            th {
                color: #63eaff;
                background: #0b151c;
            }

            td {
                color: #b8cbd0;
            }

            .empty {
                padding: 30px;
                color: #789099;
            }
        </style>
    </head>

    <body>

        <h1>ULTRON — Security Registrations</h1>

        <div class="count">
            Total registrations: {{ rows|length }}
        </div>

        {% if rows %}

        <table>

            <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Email</th>
                <th>Country</th>
                <th>Purpose</th>
                <th>Message</th>
                <th>Created</th>
            </tr>

            {% for row in rows %}

            <tr>
                <td>{{ row[0] }}</td>
                <td>{{ row[1] }}</td>
                <td>{{ row[2] }}</td>
                <td>{{ row[3] }}</td>
                <td>{{ row[4] }}</td>
                <td>{{ row[5] }}</td>
                <td>{{ row[6] }}</td>
            </tr>

            {% endfor %}

        </table>

        {% else %}

        <div class="empty">
            No registrations yet.
        </div>

        {% endif %}

    </body>
    </html>
    """

    return render_template_string(html, rows=rows)


if __name__ == "__main__":

    initialize_database()

    print()
    print("ULTRON SECURITY API")
    print("Database :", DB_PATH)
    print("Status   : ONLINE")
    print("API      : http://127.0.0.1:5000")
    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
