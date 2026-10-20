#!/usr/bin/env python3
"""Campus registration site: static files plus a small JSON API.

Standard library only. Run:  python3 server.py  (then open http://127.0.0.1:8000)

Environment variables:
  REG_DB     path to the SQLite file (default: registrations.db next to this file)
  ADMIN_KEY  if set, GET /api/registrations needs the header X-Admin-Key: <value>.
             If not set, that endpoint only answers requests from this machine.
"""
import argparse
import json
import os
import re
import secrets
import sqlite3
import unicodedata
from datetime import date, datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ROOT, "public")
DEFAULT_DB = os.path.join(ROOT, "registrations.db")
MAX_BODY = 64 * 1024

COURSES = {"B.Tech / B.E.", "B.Sc", "B.A.", "B.Com", "BBA / BMS", "BCA",
           "LL.B.", "MBBS", "M.Tech", "M.Sc", "MBA", "Other"}
YEARS = {"1st year", "2nd year", "3rd year", "4th year", "5th year"}
GENDERS = {"Female", "Male", "Non-binary", "Prefer not to say"}
STAYS = {"Hostel", "Day scholar"}
INTERESTS = {"Coding", "Design", "Sports", "Music", "Drama",
             "Entrepreneurship", "Photography", "Volunteering"}
ID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


# ---------------------------------------------------------------- validation
def validate(data):
    """Return (clean, errors). `errors` maps a field name to a message."""
    errors, clean = {}, {}
    if not isinstance(data, dict):
        return {}, {"_": "Send a JSON object."}

    def text(key):
        value = data.get(key)
        return value.strip() if isinstance(value, str) else ""

    name = text("fullName")
    if len(name) < 2:
        errors["fullName"] = "Enter your full name as it appears on your college ID."
    elif not all(unicodedata.category(ch)[0] in "LM" or ch in " .'-" for ch in name):
        errors["fullName"] = "Use letters only, with no numbers or symbols."
    clean["fullName"] = name

    dob = text("dob")
    try:
        born = date.fromisoformat(dob)
        today = date.today()
        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        if not 16 <= age <= 45:
            errors["dob"] = "Enter a valid date of birth. Students must be 16 or older."
    except ValueError:
        errors["dob"] = "Select your date of birth."
    clean["dob"] = dob

    enrollment = text("enrollment").upper()
    if not re.fullmatch(r"[A-Z0-9/\-]{5,20}", enrollment):
        errors["enrollment"] = "Enter 5 to 20 letters or digits, as printed on your ID card."
    clean["enrollment"] = enrollment

    college = text("college")
    if len(college) < 3:
        errors["college"] = "Enter your college or university name."
    clean["college"] = college

    course = text("course")
    if course not in COURSES:
        errors["course"] = "Choose your course."
    clean["course"] = course

    branch = text("branch")
    if len(branch) < 2:
        errors["branch"] = "Enter your branch or department."
    clean["branch"] = branch

    year = text("year")
    if year not in YEARS:
        errors["year"] = "Select your year of study."
    clean["year"] = year

    email = text("email").lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]{2,}", email):
        errors["email"] = "Enter a valid email address, like you@college.edu.in."
    clean["email"] = email

    phone = re.sub(r"\s+", "", text("phone"))
    if not re.fullmatch(r"[6-9]\d{9}", phone):
        errors["phone"] = "Enter a 10-digit Indian mobile number starting with 6, 7, 8 or 9."
    clean["phone"] = phone

    city = text("city")
    if len(city) < 2:
        errors["city"] = "Enter your city."
    clean["city"] = city

    if data.get("consent") is not True:
        errors["consent"] = "Tick this box to confirm and continue."

    gender = text("gender")
    if gender and gender not in GENDERS:
        errors["gender"] = "Choose one of the listed options."
    clean["gender"] = gender

    stay = text("stay")
    if stay and stay not in STAYS:
        errors["stay"] = "Choose one of the listed options."
    clean["stay"] = stay

    interests = data.get("interests", [])
    if not isinstance(interests, list) or not all(i in INTERESTS for i in interests):
        errors["interests"] = "Choose interests from the list."
        interests = []
    clean["interests"] = sorted(set(interests))

    notes = text("notes")
    if len(notes) > 1000:
        errors["notes"] = "Keep notes under 1000 characters."
    clean["notes"] = notes
    return clean, errors


# ------------------------------------------------------------------ database
class Duplicate(Exception):
    def __init__(self, field):
        super().__init__(field)
        self.field = field


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    with connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                id          TEXT PRIMARY KEY,
                created_at  TEXT NOT NULL,
                full_name   TEXT NOT NULL,
                dob         TEXT NOT NULL,
                gender      TEXT NOT NULL,
                enrollment  TEXT NOT NULL UNIQUE COLLATE NOCASE,
                college     TEXT NOT NULL,
                course      TEXT NOT NULL,
                branch      TEXT NOT NULL,
                year        TEXT NOT NULL,
                stay        TEXT NOT NULL,
                email       TEXT NOT NULL UNIQUE COLLATE NOCASE,
                phone       TEXT NOT NULL,
                city        TEXT NOT NULL,
                interests   TEXT NOT NULL,
                notes       TEXT NOT NULL
            )""")
    conn.close()


def insert_registration(db_path, clean):
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = connect(db_path)
    try:
        for _ in range(10):
            reg_id = "CC26-" + "".join(secrets.choice(ID_ALPHABET) for _ in range(5))
            try:
                with conn:
                    conn.execute(
                        "INSERT INTO registrations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (reg_id, created, clean["fullName"], clean["dob"], clean["gender"],
                         clean["enrollment"], clean["college"], clean["course"], clean["branch"],
                         clean["year"], clean["stay"], clean["email"], clean["phone"],
                         clean["city"], json.dumps(clean["interests"]), clean["notes"]))
                return reg_id, created
            except sqlite3.IntegrityError as exc:
                message = str(exc)
                if "enrollment" in message:
                    raise Duplicate("enrollment")
                if "email" in message:
                    raise Duplicate("email")
                # id collision: try another id
        raise RuntimeError("could not allocate a registration id")
    finally:
        conn.close()


def list_registrations(db_path):
    conn = connect(db_path)
    try:
        rows = conn.execute("SELECT * FROM registrations ORDER BY created_at DESC, id").fetchall()
    finally:
        conn.close()
    out = []
    for row in rows:
        item = dict(row)
        item["interests"] = json.loads(item["interests"])
        out.append(item)
    return out


# -------------------------------------------------------------------- server
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC, **kwargs)

    def log_message(self, fmt, *args):
        if not getattr(self.server, "quiet", False):
            super().log_message(fmt, *args)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def is_admin(self):
        key = os.environ.get("ADMIN_KEY", "")
        if key:
            return secrets.compare_digest(self.headers.get("X-Admin-Key", ""), key)
        return self.client_address[0] in ("127.0.0.1", "::1")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            return self.send_json(200, {"ok": True})
        if path == "/api/registrations":
            if not self.is_admin():
                return self.send_json(401, {"error": "Admin access required."})
            return self.send_json(200, {"registrations": list_registrations(self.server.db_path)})
        if path.startswith("/api/"):
            return self.send_json(404, {"error": "Not found."})
        if path == "/registrations":
            self.path = "/registrations.html"
        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/register":
            return self.send_json(404, {"error": "Not found."})
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return self.send_json(400, {"error": "Content-Length is required."})
        if length > MAX_BODY:
            self.close_connection = True
            return self.send_json(413, {"error": "Request is too large."})
        try:
            data = json.loads(self.rfile.read(length) or b"null")
        except (ValueError, UnicodeDecodeError):
            return self.send_json(400, {"error": "Body must be valid JSON."})

        clean, errors = validate(data)
        if errors:
            return self.send_json(422, {"errors": errors})
        try:
            reg_id, created = insert_registration(self.server.db_path, clean)
        except Duplicate as dup:
            label = "enrollment number" if dup.field == "enrollment" else "email address"
            return self.send_json(409, {"errors": {dup.field: f"This {label} is already registered."}})
        self.send_json(201, {"id": reg_id, "createdAt": created, "name": clean["fullName"]})


def make_server(host="127.0.0.1", port=8000, db_path=DEFAULT_DB, quiet=False):
    init_db(db_path)
    server = ThreadingHTTPServer((host, port), Handler)
    server.db_path = db_path
    server.quiet = quiet
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = make_server(args.host, args.port, os.environ.get("REG_DB", DEFAULT_DB))
    print(f"Serving on http://{args.host}:{server.server_address[1]}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
