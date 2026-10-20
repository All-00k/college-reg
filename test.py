#!/usr/bin/env python3
"""Tests for the registration site. Standard library only.

Run:  python3 test.py          (or: python3 -m unittest test -v)

Starts the real server on a free port with a temporary database, so nothing
you have registered in registrations.db is touched.
"""
import http.client
import itertools
import json
import os
import tempfile
import threading
import unittest
from datetime import date

import server

_counter = itertools.count(1)


def sample(**overrides):
    """A valid registration with a unique enrollment number and email."""
    n = next(_counter)
    today = date.today()
    data = {
        "fullName": "Aarav Sharma",
        "dob": today.replace(year=today.year - 20, day=1).isoformat(),
        "gender": "Male",
        "enrollment": f"21cs{1000 + n}",
        "college": "Delhi Technological University",
        "course": "B.Tech / B.E.",
        "branch": "Computer Science",
        "year": "3rd year",
        "stay": "Hostel",
        "email": f"Student{n}@College.edu.in",
        "phone": "98765 43210",
        "city": "New Delhi",
        "interests": ["Coding", "Music"],
        "notes": "",
        "consent": True,
    }
    data.update(overrides)
    return data


class ValidateTests(unittest.TestCase):
    def test_valid_data_is_cleaned(self):
        clean, errors = server.validate(sample(enrollment="21cs1042", email="A@B.IN", phone="98765 43210"))
        self.assertEqual(errors, {})
        self.assertEqual(clean["enrollment"], "21CS1042")
        self.assertEqual(clean["email"], "a@b.in")
        self.assertEqual(clean["phone"], "9876543210")

    def test_empty_object_reports_every_required_field(self):
        _, errors = server.validate({})
        for field in ("fullName", "dob", "enrollment", "college", "course", "branch",
                      "year", "email", "phone", "city", "consent"):
            self.assertIn(field, errors)

    def test_not_an_object(self):
        _, errors = server.validate([1, 2, 3])
        self.assertIn("_", errors)

    def test_name_rules(self):
        self.assertIn("fullName", server.validate(sample(fullName="A"))[1])
        self.assertIn("fullName", server.validate(sample(fullName="R2D2"))[1])
        self.assertEqual(server.validate(sample(fullName="Anne-Marie O'Neil Jr."))[1], {})
        self.assertEqual(server.validate(sample(fullName="प्रिया शर्मा"))[1], {})

    def test_phone_rules(self):
        for bad in ("12345 67890", "98765", "98765432101", "abcdefghij"):
            self.assertIn("phone", server.validate(sample(phone=bad))[1], bad)

    def test_email_rules(self):
        for bad in ("nope", "a@b", "a b@c.com", "@c.com"):
            self.assertIn("email", server.validate(sample(email=bad))[1], bad)

    def test_age_limits(self):
        today = date.today()
        too_young = today.replace(year=today.year - 10).isoformat()
        too_old = today.replace(year=today.year - 60).isoformat()
        self.assertIn("dob", server.validate(sample(dob=too_young))[1])
        self.assertIn("dob", server.validate(sample(dob=too_old))[1])
        self.assertIn("dob", server.validate(sample(dob="not-a-date"))[1])

    def test_choice_fields(self):
        self.assertIn("course", server.validate(sample(course="Astrology"))[1])
        self.assertIn("year", server.validate(sample(year="9th year"))[1])
        self.assertIn("gender", server.validate(sample(gender="Robot"))[1])
        self.assertIn("stay", server.validate(sample(stay="Car"))[1])
        self.assertIn("interests", server.validate(sample(interests=["Hacking"]))[1])
        self.assertIn("interests", server.validate(sample(interests="Coding"))[1])

    def test_optional_fields_may_be_blank(self):
        self.assertEqual(server.validate(sample(gender="", stay="", interests=[], notes=""))[1], {})

    def test_consent_must_be_true(self):
        self.assertIn("consent", server.validate(sample(consent=False))[1])
        self.assertIn("consent", server.validate(sample(consent="yes"))[1])

    def test_notes_length(self):
        self.assertIn("notes", server.validate(sample(notes="x" * 1001))[1])


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "test.db")
        cls.httpd = server.make_server("127.0.0.1", 0, cls.db, quiet=True)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def setUp(self):
        self._old_key = os.environ.pop("ADMIN_KEY", None)

    def tearDown(self):
        os.environ.pop("ADMIN_KEY", None)
        if self._old_key is not None:
            os.environ["ADMIN_KEY"] = self._old_key

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            payload = None
            headers = dict(headers or {})
            if body is not None:
                payload = body if isinstance(body, bytes) else json.dumps(body).encode()
                headers.setdefault("Content-Type", "application/json")
            conn.request(method, path, body=payload, headers=headers)
            res = conn.getresponse()
            raw = res.read()
            return res.status, res.getheader("Content-Type", ""), raw
        finally:
            conn.close()

    def api(self, method, path, body=None, headers=None):
        status, _, raw = self.request(method, path, body, headers)
        return status, json.loads(raw)

    # ------------------------------------------------------------ static files
    def test_home_page(self):
        status, ctype, raw = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        self.assertIn(b"Student registration", raw)
        self.assertIn(b'id="reg"', raw)

    def test_assets_are_served(self):
        for path, needle in (("/style.css", b"--red"), ("/script.js", b"/api/register"),
                             ("/registrations.js", b"/api/registrations")):
            status, _, raw = self.request("GET", path)
            self.assertEqual(status, 200, path)
            self.assertIn(needle, raw, path)

    def test_registrations_page(self):
        status, _, raw = self.request("GET", "/registrations")
        self.assertEqual(status, 200)
        self.assertIn(b"<title>Registrations</title>", raw)

    def test_unknown_page_is_404(self):
        self.assertEqual(self.request("GET", "/nope.html")[0], 404)

    def test_database_and_source_are_not_served(self):
        self.assertEqual(self.request("GET", "/test.db")[0], 404)
        self.assertEqual(self.request("GET", "/registrations.db")[0], 404)
        self.assertEqual(self.request("GET", "/../server.py")[0], 404)
        self.assertEqual(self.request("GET", "/%2e%2e/server.py")[0], 404)

    # --------------------------------------------------------------------- API
    def test_health(self):
        self.assertEqual(self.api("GET", "/api/health"), (200, {"ok": True}))

    def test_unknown_api_route(self):
        self.assertEqual(self.api("GET", "/api/nothing")[0], 404)
        self.assertEqual(self.api("POST", "/api/nothing", {})[0], 404)

    def test_register_success_and_listing(self):
        data = sample(fullName="Priya Verma", enrollment="21ee7777", email="priya@college.edu.in")
        status, body = self.api("POST", "/api/register", data)
        self.assertEqual(status, 201)
        self.assertRegex(body["id"], r"^CC26-[A-Z2-9]{5}$")
        self.assertEqual(body["name"], "Priya Verma")

        status, listing = self.api("GET", "/api/registrations")
        self.assertEqual(status, 200)
        row = next(r for r in listing["registrations"] if r["id"] == body["id"])
        self.assertEqual(row["full_name"], "Priya Verma")
        self.assertEqual(row["enrollment"], "21EE7777")
        self.assertEqual(row["phone"], "9876543210")
        self.assertEqual(row["interests"], ["Coding", "Music"])

    def test_validation_errors_return_422(self):
        status, body = self.api("POST", "/api/register", sample(phone="123", year="", consent=False))
        self.assertEqual(status, 422)
        self.assertEqual(set(body["errors"]), {"phone", "year", "consent"})

    def test_rejected_registration_is_not_stored(self):
        data = sample(enrollment="21XX0001", email="rejected@college.edu.in", phone="1")
        self.assertEqual(self.api("POST", "/api/register", data)[0], 422)
        listing = self.api("GET", "/api/registrations")[1]["registrations"]
        self.assertFalse(any(r["enrollment"] == "21XX0001" for r in listing))

    def test_duplicate_enrollment_is_rejected_case_insensitively(self):
        first = sample(enrollment="DUP12345")
        self.assertEqual(self.api("POST", "/api/register", first)[0], 201)
        status, body = self.api("POST", "/api/register", sample(enrollment="dup12345"))
        self.assertEqual(status, 409)
        self.assertIn("enrollment", body["errors"])

    def test_duplicate_email_is_rejected_case_insensitively(self):
        first = sample(email="same@college.edu.in")
        self.assertEqual(self.api("POST", "/api/register", first)[0], 201)
        status, body = self.api("POST", "/api/register", sample(email="SAME@college.edu.in"))
        self.assertEqual(status, 409)
        self.assertIn("email", body["errors"])

    def test_invalid_json_is_400(self):
        status, body = self.api("POST", "/api/register", b"{not json")
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_json_that_is_not_an_object_is_422(self):
        self.assertEqual(self.api("POST", "/api/register", b"[1,2]")[0], 422)
        self.assertEqual(self.api("POST", "/api/register", b"null")[0], 422)

    def test_oversized_body_is_413(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.putrequest("POST", "/api/register")
            conn.putheader("Content-Type", "application/json")
            conn.putheader("Content-Length", str(server.MAX_BODY + 1))
            conn.endheaders()
            self.assertEqual(conn.getresponse().status, 413)
        finally:
            conn.close()

    def test_html_in_fields_is_stored_as_text(self):
        data = sample(college="<script>alert(1)</script> College", enrollment="XSS00001",
                      email="xss@college.edu.in")
        status, body = self.api("POST", "/api/register", data)
        self.assertEqual(status, 201)
        rows = self.api("GET", "/api/registrations")[1]["registrations"]
        row = next(r for r in rows if r["id"] == body["id"])
        self.assertEqual(row["college"], "<script>alert(1)</script> College")

    def test_sql_injection_text_is_harmless(self):
        data = sample(city="x'); DROP TABLE registrations;--", enrollment="SQLI0001",
                      email="sqli@college.edu.in")
        self.assertEqual(self.api("POST", "/api/register", data)[0], 201)
        self.assertEqual(self.api("GET", "/api/registrations")[0], 200)

    # ------------------------------------------------------------ admin access
    def test_listing_needs_the_admin_key_when_one_is_set(self):
        os.environ["ADMIN_KEY"] = "s3cret"
        self.assertEqual(self.api("GET", "/api/registrations")[0], 401)
        self.assertEqual(self.api("GET", "/api/registrations", headers={"X-Admin-Key": "wrong"})[0], 401)
        status, body = self.api("GET", "/api/registrations", headers={"X-Admin-Key": "s3cret"})
        self.assertEqual(status, 200)
        self.assertIn("registrations", body)

    def test_registering_never_needs_the_admin_key(self):
        os.environ["ADMIN_KEY"] = "s3cret"
        self.assertEqual(self.api("POST", "/api/register", sample())[0], 201)


if __name__ == "__main__":
    unittest.main(verbosity=2)
