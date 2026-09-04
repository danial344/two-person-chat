from flask import Flask, render_template, request, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

DB = "chat.db"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            receiver TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def index():
    if "username" not in session:
        return redirect("/login")

    return render_template("index.html", username=session["username"])


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        if not username or not password:
            return "لطفاً همه قسمت‌ها را پر کنید."

        conn = get_db()

        try:
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, generate_password_hash(password))
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "این ID قبلاً استفاده شده است."

        conn.close()
        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["username"] = username
            return redirect("/")

        return "ID یا رمز عبور اشتباه است."

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/send", methods=["POST"])
def send():
    if "username" not in session:
        return {"error": "unauthorized"}, 401

    data = request.get_json()
    receiver = data.get("receiver", "").strip()
    message = data.get("message", "").strip()

    if not receiver or not message:
        return {"error": "اطلاعات ناقص است"}, 400

    conn = get_db()

    user = conn.execute(
        "SELECT id FROM users WHERE username = ?",
        (receiver,)
    ).fetchone()

    if not user:
        conn.close()
        return {"error": "کاربر پیدا نشد"}, 404

    conn.execute(
        """
        INSERT INTO messages (sender, receiver, message)
        VALUES (?, ?, ?)
        """,
        (session["username"], receiver, message)
    )

    conn.commit()
    conn.close()

    return {"success": True}


@app.route("/messages/<receiver>")
def messages(receiver):
    if "username" not in session:
        return {"error": "unauthorized"}, 401

    username = session["username"]

    conn = get_db()

    rows = conn.execute(
        """
        SELECT sender, receiver, message, created_at
        FROM messages
        WHERE
            (sender = ? AND receiver = ?)
            OR
            (sender = ? AND receiver = ?)
        ORDER BY id ASC
        """,
        (username, receiver, receiver, username)
    ).fetchall()

    conn.close()

    return {
        "messages": [
            {
                "sender": row["sender"],
                "receiver": row["receiver"],
                "message": row["message"],
                "created_at": row["created_at"]
            }
            for row in rows
        ]
    }


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
