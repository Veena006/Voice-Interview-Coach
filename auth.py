"""Accounts (email + password) and saved interview history, stored in a local
SQLite file. Passwords are never stored: only a salted PBKDF2 hash.

Limits to be honest about: there is no email verification and no password reset,
and the database is a plain file on the computer that runs the app."""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time

import config

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PBKDF2_ROUNDS = 200_000
MAX_FAILS, LOCK_SECONDS = 5, 300
_fails = {}  # email -> (number of failures, time of first failure)


def _conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        salt TEXT NOT NULL,
        pw_hash TEXT NOT NULL,
        created TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS interviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        record_json TEXT NOT NULL)""")
    return conn


def _hash(password, salt_hex):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                               bytes.fromhex(salt_hex), PBKDF2_ROUNDS).hex()


def clean_email(email):
    return (email or "").strip().lower()


def validate_signup(name, email, password, confirm):
    """Return an error message, or None if everything is fine."""
    if not (name or "").strip():
        return "Please enter your name."
    if len(name.strip()) > 40:
        return "Your name is too long (40 characters at most)."
    email = clean_email(email)
    if not EMAIL_RE.match(email) or len(email) > 254:
        return "Please enter a valid email address."
    if len(password or "") < 8:
        return "Your password must be at least 8 characters."
    if len(password) > 200:
        return "Your password is too long."
    if password != confirm:
        return "The two passwords do not match."
    return None


def create_user(name, email, password):
    """Create an account. Raises ValueError with a friendly message on problems."""
    problem = validate_signup(name, email, password, password)
    if problem:
        raise ValueError(problem)
    email = clean_email(email)
    salt = secrets.token_hex(16)
    try:
        with _conn() as conn:
            cur = conn.execute(
                "INSERT INTO users (name, email, salt, pw_hash, created) VALUES (?,?,?,?,?)",
                (name.strip(), email, salt, _hash(password, salt),
                 time.strftime("%Y-%m-%d %H:%M:%S")))
            return {"id": cur.lastrowid, "name": name.strip(), "email": email}
    except sqlite3.IntegrityError:
        raise ValueError("An account with this email already exists. Please sign in.")


def verify_user(email, password):
    """Return the user, or raise ValueError. Locks an email after too many failures."""
    email = clean_email(email)
    count, first = _fails.get(email, (0, 0))
    if count >= MAX_FAILS and time.time() - first < LOCK_SECONDS:
        raise ValueError("Too many failed attempts. Please wait a few minutes and try again.")
    if count and time.time() - first >= LOCK_SECONDS:
        count, first = 0, 0

    with _conn() as conn:
        row = conn.execute("SELECT id, name, email, salt, pw_hash FROM users WHERE email = ?",
                           (email,)).fetchone()
    # hash even when the user does not exist, so timing does not reveal accounts
    salt = row[3] if row else "00" * 16
    ok = hmac.compare_digest(_hash(password or "", salt), row[4] if row else "0" * 64)
    if not (row and ok):
        _fails[email] = (count + 1, first or time.time())
        raise ValueError("Incorrect email or password.")
    _fails.pop(email, None)
    return {"id": row[0], "name": row[1], "email": row[2]}


def delete_user(user_id):
    with _conn() as conn:
        conn.execute("DELETE FROM interviews WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


# ---------------------------------------------------------------- history
def add_record(user_id, record):
    with _conn() as conn:
        conn.execute("INSERT INTO interviews (user_id, record_json) VALUES (?, ?)",
                     (user_id, json.dumps(record, ensure_ascii=False)))


def load_history(user_id):
    with _conn() as conn:
        rows = conn.execute("SELECT record_json FROM interviews WHERE user_id = ? ORDER BY id",
                            (user_id,)).fetchall()
    history = []
    for i, (text,) in enumerate(rows, 1):
        try:
            record = json.loads(text)
            record["id"] = i
            history.append(record)
        except ValueError:
            continue  # skip a damaged row instead of crashing
    return history


def clear_history(user_id):
    with _conn() as conn:
        conn.execute("DELETE FROM interviews WHERE user_id = ?", (user_id,))