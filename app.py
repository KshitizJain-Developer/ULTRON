from flask import Flask, request, jsonify, render_template_string, session, redirect
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "ultron.db"

app = Flask(__name__)
CORS(app)

# Secret used for the admin login session.
# Set this in Render Environment Variables.
app.secret_key = os.environ.get(
    "ULTRON_SESSION_SECRET",
    "change-this-session-secret"
)

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


# IMPORTANT:
# Gunicorn imports app.py instead of running it as __main__.
# Therefore the database must be initialized here.
initialize_database()


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


LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>ULTRON Admin Login</title>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #05080d;
            color: #eaffff;
            font-family: Arial, sans-serif;
        }

        .box {
            width: 100%;
            max-width: 400px;
            padding: 35px;
            background: #080e14;
            border: 1px solid rgba(0, 220, 255, .25);
            border-radius: 16px;
            box-shadow: 0 30px 100px rgba(0, 0, 0, .6);
        }

        h1 {
            margin-top: 0;
            color: #63eaff;
            letter-spacing: 2px;
        }

        p {
            color: #789099;
            font-size: 13px;
        }

        input {
            width: 100%;
            padding: 13px;
            margin: 18px 0 12px;
            background: #050a0f;
            color: #eaffff;
            border: 1px solid rgba(0, 220, 255, .2);
            border-radius: 8px;
            outline: none;
        }

        button {
            width: 100%;
            padding: 13px;
            border: 0;
            border-radius: 8px;
            background: #63eaff;
            color: #031016;
            font-weight: 700;
            cursor: pointer;
        }

        .error {
            color: #ff7d7d;
            font-size: 12px;
        }
    </style>
</head>

<body>

<div class="box">

    <h1>ULTRON ADMIN</h1>

    <p>
        Authorized access only.
    </p>

    {% if error %}
        <div class="error">Invalid password.</div>
    {% endif %}

    <form method="POST">

        <input
            type="password"
            name="password"
            placeholder="Admin password"
            required
            autocomplete="current-password"
        >

        <button type="submit">
            LOGIN
        </button>

    </form>

</div>

</body>
</html>
"""


@app.route("/admin", methods=["GET", "POST"])
def admin():

    if not ADMIN_PASSWORD:
        return """
        <h2>ULTRON ADMIN</h2>
        <p>Admin password is not configured on the server.</p>
        """, 500

    if request.method == "POST":

        password = request.form.get("password", "")

        if password == ADMIN_PASSWORD:
            session["ultron_admin"] = True
            return redirect("/admin")

        return render_template_string(
            LOGIN_PAGE,
            error=True
        ), 401

    if not session.get("ultron_admin"):
        return render_template_string(
            LOGIN_PAGE,
            error=False
        )

    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            email,
            country,
            purpose,
            message,
            created_at
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
        <meta name="viewport" content="width=device-width, initial-scale=1.0">

        <title>ULTRON Registrations</title>

        <style>

            * {
                box-sizing: border-box;
            }

            body {
                margin: 0;
                background: #05080d;
                color: #eaffff;
                font-family: Arial, sans-serif;
                padding: 30px;
            }

            .top {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 20px;
                margin-bottom: 25px;
            }

            h1 {
                color: #63eaff;
                margin: 0;
            }

            .count {
                color: #7f969d;
                margin-top: 8px;
                font-size: 13px;
            }

            .logout {
                color: #63eaff;
                text-decoration: none;
                border: 1px solid rgba(0,220,255,.25);
                padding: 10px 14px;
                border-radius: 8px;
            }

            .table-wrap {
                overflow-x: auto;
                border: 1px solid #18313a;
                border-radius: 12px;
            }

            table {
                width: 100%;
                min-width: 900px;
                border-collapse: collapse;
                background: #080e14;
            }

            th,
            td {
                padding: 12px;
                border-bottom: 1px solid #18313a;
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

        <div class="top">

            <div>
                <h1>ULTRON — Security Registrations</h1>

                <div class="count">
                    Total registrations: {{ rows|length }}
                </div>
            </div>

            <a class="logout" href="/admin/logout">
                LOGOUT
            </a>

        </div>

        {% if rows %}

        <div class="table-wrap">

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

        </div>

        {% else %}

        <div class="empty">
            No registrations yet.
        </div>

        {% endif %}

    </body>

    </html>
    """

    return render_template_string(
        html,
        rows=rows
    )


@app.get("/admin/logout")
def admin_logout():

    session.pop("ultron_admin", None)

    return redirect("/admin")


if __name__ == "__main__":

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
