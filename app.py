import json
import os
import sqlite3
import uuid
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from flask import Flask, jsonify, make_response, render_template, request
from services.llm import generate_clarifying_questions, generate_final_plan, llm_configured

DB_PATH = BASE_DIR / "promptforge.db"
COOKIE_NAME = "promptforge_user"
app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_or_create_user_id():
    user_id = request.cookies.get(COOKIE_NAME)
    if user_id:
        return user_id
    return str(uuid.uuid4())


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            original_prompt TEXT NOT NULL,
            questions_json TEXT,
            answers_json TEXT,
            final_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Small migration for databases created by the previous MVP.
    columns = {row[1] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()}
    if "user_id" not in columns:
        conn.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT")

    conn.commit()
    conn.close()


def ensure_user():
    user_id = get_or_create_user_id()
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
    # Give records from the previous single-user MVP to the first local visitor.
    conn.execute("UPDATE sessions SET user_id = ? WHERE user_id IS NULL", (user_id,))
    conn.commit()
    conn.close()
    return user_id


def response_with_user_cookie(payload):
    response = make_response(jsonify(payload))
    user_id = get_or_create_user_id()
    response.set_cookie(COOKIE_NAME, user_id, max_age=60 * 60 * 24 * 365 * 5, httponly=True, samesite="Lax")
    return response


def get_session(session_id, user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    ).fetchone()
    conn.close()
    return row


@app.route("/")
def index():
    user_id = ensure_user()
    response = make_response(render_template("index.html"))
    response.set_cookie(COOKIE_NAME, user_id, max_age=60 * 60 * 24 * 365 * 5, httponly=True, samesite="Lax")
    return response


@app.get("/api/history")
def history():
    user_id = ensure_user()
    conn = get_db()
    rows = conn.execute(
        """
        SELECT id, original_prompt, created_at, final_json
        FROM sessions
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 50
        """,
        (user_id,),
    ).fetchall()
    conn.close()

    items = []
    for row in rows:
        completed = bool(row["final_json"])
        items.append({
            "id": row["id"],
            "prompt": row["original_prompt"],
            "created_at": row["created_at"],
            "status": "completed" if completed else "in progress",
        })

    response = response_with_user_cookie({"history": items})
    return response


@app.post("/api/session")
def create_session():
    user_id = ensure_user()
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()

    if len(prompt) < 5:
        return jsonify({"error": "Please enter a useful starting prompt."}), 400

    question_result = generate_clarifying_questions(prompt)
    questions = question_result.get("questions", [])

    conn = get_db()
    cursor = conn.execute(
        """
        INSERT INTO sessions (user_id, original_prompt, questions_json)
        VALUES (?, ?, ?)
        """,
        (user_id, prompt, json.dumps(questions)),
    )
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return response_with_user_cookie({
        "session_id": session_id,
        "questions": questions,
        "available": question_result.get("available", False),
        "message": question_result.get("message"),
    })


@app.post("/api/session/<int:session_id>/finalize")
def finalize_session(session_id):
    user_id = ensure_user()
    row = get_session(session_id, user_id)
    if row is None:
        return jsonify({"error": "Session not found."}), 404

    data = request.get_json(silent=True) or {}
    answers = data.get("answers") or []
    if not isinstance(answers, list):
        return jsonify({"error": "Answers must be a list."}), 400

    result = generate_final_plan(row["original_prompt"], row["questions_json"], answers)

    conn = get_db()
    conn.execute(
        """
        UPDATE sessions
        SET answers_json = ?, final_json = ?
        WHERE id = ? AND user_id = ?
        """,
        (json.dumps(answers), json.dumps(result), session_id, user_id),
    )
    conn.commit()
    conn.close()

    return response_with_user_cookie({"result": result})


@app.get("/api/session/<int:session_id>")
def read_session(session_id):
    user_id = ensure_user()
    row = get_session(session_id, user_id)
    if row is None:
        return jsonify({"error": "Session not found."}), 404

    result = json.loads(row["final_json"]) if row["final_json"] else None
    return response_with_user_cookie({
        "id": row["id"],
        "original_prompt": row["original_prompt"],
        "questions": json.loads(row["questions_json"] or "[]"),
        "answers": json.loads(row["answers_json"] or "[]"),
        "result": result,
        "created_at": row["created_at"],
    })


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "llm_configured": llm_configured()})


init_db()

if __name__ == "__main__":
    app.run(debug=True)
