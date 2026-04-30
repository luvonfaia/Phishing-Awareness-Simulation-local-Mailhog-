#!/usr/bin/env python3
"""
Phishing Awareness Simulation (local, Mailhog)
- Flask app that sends templated test emails to recipients.csv
- Tracks opens (pixel), clicks (redirect -> training), reports, training completion, quiz score
- Stores events in sqlite and exports weekly CSV metrics
Ethics: Use only with authorization. Do not impersonate real brands or execs.
"""

import csv
import os
import sqlite3
import secrets
import smtplib
import time
from datetime import datetime, timedelta
from email.message import EmailMessage
from flask import Flask, request, send_file, redirect, render_template_string, jsonify, abort

# Configuration
SMTP_HOST = "localhost"
SMTP_PORT = 1025  # Mailhog default
FROM_ADDR = "security-sim@example.local"
BASE_URL = "http://127.0.0.1:5000"  # used to build tracking URLs
DB_PATH = "sim.db"
RECIPIENTS_CSV = "recipients.csv"
EXPORT_DIR = "exports"
CAMPAIGN_DEFAULT_NAME = "campaign-" + datetime.utcnow().strftime("%Y%m%d%H%M%S")

# Ensure export dir
os.makedirs(EXPORT_DIR, exist_ok=True)

app = Flask(__name__)

# --- Safe templates (no real brands) ---
TEMPLATES = [
    {
        "id": "it_ticket",
        "subject": "Action required: IT ticket update",
        "body": """Hello {{name}},

Our IT team has created a ticket for your recent request. Please review the ticket details here: {{click_url}}

If you did not request this, please report it using the 'Report Phish' link in the message.

Thanks,
IT Support"""
    },
    {
        "id": "hr_policy",
        "subject": "Updated HR policy: Please review",
        "body": """Hi {{name}},

We have updated a company policy that may affect your benefits. Review the summary here: {{click_url}}

If this looks suspicious, please report it.
HR Team"""
    },
    {
        "id": "package",
        "subject": "Delivery attempt: package awaiting pickup",
        "body": """Hello {{name}},

A delivery service attempted to deliver a package to you. Track and schedule redelivery here: {{click_url}}

If you weren't expecting a package, report it.
Logistics"""
    },
    {
        "id": "invoice",
        "subject": "Invoice attached for recent order",
        "body": """Hi {{name}},

Please view the invoice for your recent order: {{click_url}}

If you did not place this order, report it immediately.
Billing"""
    },
    {
        "id": "calendar",
        "subject": "Calendar invite: Team sync tomorrow",
        "body": """Hello {{name}},

You have been invited to a team sync. View details and RSVP here: {{click_url}}

If this is unexpected, report it.
Scheduling"""
    }
]

# --- Database helpers ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS recipients (
        id INTEGER PRIMARY KEY,
        email TEXT UNIQUE,
        cohort TEXT,
        employee_id TEXT,
        token TEXT,
        campaign_id TEXT,
        template_id TEXT,
        sent_at TEXT
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY,
        token TEXT,
        event_type TEXT, -- open, click, report, training_completed, quiz
        details TEXT,
        timestamp TEXT
    )""")
    conn.commit()
    conn.close()

def db_execute(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

def db_query(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows

# --- Token generation ---
def make_token():
    return secrets.token_urlsafe(24)

# --- Email sending (Mailhog for dev) ---
def send_email(to_addr, subject, body):
    msg = EmailMessage()
    msg["From"] = FROM_ADDR
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.send_message(msg)

# --- Event logging ---
def log_event(token, event_type, details=""):
    ts = datetime.utcnow().isoformat()
    db_execute("INSERT INTO events (token, event_type, details, timestamp) VALUES (?, ?, ?, ?)",
               (token, event_type, details, ts))

# --- Load recipients CSV and create tokens ---
def load_recipients(campaign_id, template_id):
    created = 0
    with open(RECIPIENTS_CSV, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            email = row.get("email")
            cohort = row.get("cohort", "default")
            employee_id = row.get("employee_id", "")
            token = make_token()
            sent_at = datetime.utcnow().isoformat()
            try:
                db_execute("""INSERT OR REPLACE INTO recipients
                    (email, cohort, employee_id, token, campaign_id, template_id, sent_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (email, cohort, employee_id, token, campaign_id, template_id, sent_at))
                created += 1
            except Exception:
                pass
    return created

# --- Build tracking URLs ---
def build_open_url(token):
    return f"{BASE_URL}/track/open/{token}.png"

def build_click_url(token):
    return f"{BASE_URL}/track/click/{token}"

def build_report_url(token):
    return f"{BASE_URL}/report/{token}"

# --- Flask endpoints ---
@app.route("/")
def index():
    return ("Phishing Simulation running. Use /send_campaign to start a campaign, "
            "/export_weekly to export CSVs. This service is for authorized testing only.")

@app.route("/send_campaign", methods=["POST"])
def send_campaign():
    """
    Start a campaign.
    Accepts form or JSON:
    - campaign_id (optional)
    - template_id (optional, defaults to random)
    """
    data = request.get_json(silent=True) or request.form
    campaign_id = data.get("campaign_id") or CAMPAIGN_DEFAULT_NAME
    template_id = data.get("template_id") or secrets.choice([t["id"] for t in TEMPLATES])
    # Load recipients and create tokens
    count = load_recipients(campaign_id, template_id)
    # Send emails
    rows = db_query("SELECT email, token FROM recipients WHERE campaign_id = ? AND template_id = ?", (campaign_id, template_id))
    template = next((t for t in TEMPLATES if t["id"] == template_id), TEMPLATES[0])
    for email, token in rows:
        # personalize
        name = email.split("@")[0]
        click_url = build_click_url(token)
        open_pixel = build_open_url(token)
        report_url = build_report_url(token)
        body = template["body"].replace("{{name}}", name).replace("{{click_url}}", click_url)
        # Append pixel and report link (plain text)
        body += f"\n\n--\nIf this looks suspicious, report it: {report_url}\n\n"
        # Add open pixel as an HTML image in a multipart message: for simplicity, include the URL in body and also send as plain text
        # For Mailhog testing, plain text with the click URL is sufficient.
        send_email(email, template["subject"], body + f"\n\n[open_pixel:{open_pixel}]")
        # log send time already stored in recipients table
    return jsonify({"status": "sent", "campaign_id": campaign_id, "template_id": template_id, "target_count": count})

@app.route("/track/open/<token>.png")
def track_open(token):
    # Log open event (note: image blocking may affect this)
    log_event(token, "open", "")
    # Return a 1x1 transparent PNG
    # Minimal PNG bytes for 1x1 transparent
    png_bytes = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                 b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                 b"\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01"
                 b"\xe2!\xbc\x33\x00\x00\x00\x00IEND\xaeB`\x82")
    return send_file(
        io.BytesIO(png_bytes),
        mimetype="image/png",
        as_attachment=False,
        download_name="pixel.png"
    )

import io

@app.route("/track/click/<token>")
def track_click(token):
    # Log click
    log_event(token, "click", "")
    # Redirect to training page
    return redirect(f"/training/{token}")

@app.route("/report/<token>", methods=["GET", "POST"])
def report_phish(token):
    # Log report event and optionally accept a reason
    reason = request.values.get("reason", "")
    log_event(token, "report", reason)
    # Provide a simple acknowledgement page
    return render_template_string("""
    <h3>Thank you — report received</h3>
    <p>We logged your report. If this was a simulated test, no further action is required.</p>
    """), 200

# Training page with micro-lesson and quiz
TRAINING_TEMPLATE = """
<!doctype html>
<title>Security Awareness Training</title>
<h2>Quick lesson: Spotting suspicious emails</h2>
<p>This short lesson highlights common red flags: unexpected urgency, mismatched sender addresses, suspicious links, and requests for credentials.</p>
<ul>
  <li><b>Check the sender address</b> — it may not match the display name.</li>
  <li><b>Hover links</b> to see the real destination before clicking.</li>
  <li><b>Unexpected attachments or invoices</b> are suspicious.</li>
</ul>
<hr>
<h3>Quick quiz (3 questions)</h3>
<form method="post">
  <label>1) If an email asks you to confirm your password via a link, you should:</label><br>
  <input type="radio" name="q1" value="a" required> Click the link and enter password<br>
  <input type="radio" name="q1" value="b"> Report the email and verify via official channels<br>
  <input type="radio" name="q1" value="c"> Forward to colleagues<br><br>

  <label>2) A link that shows one domain but points to another is:</label><br>
  <input type="radio" name="q2" value="a" required> Normal<br>
  <input type="radio" name="q2" value="b"> A red flag<br>
  <input type="radio" name="q2" value="c"> Always safe<br><br>

  <label>3) If you are unsure about an invoice email, you should:</label><br>
  <input type="radio" name="q3" value="a" required> Pay immediately<br>
  <input type="radio" name="q3" value="b"> Verify with the sender via a known contact method<br>
  <input type="radio" name="q3" value="c"> Reply with your bank details<br><br>

  <button type="submit">Submit quiz</button>
</form>
"""

@app.route("/training/<token>", methods=["GET", "POST"])
def training(token):
    if request.method == "GET":
        return render_template_string(TRAINING_TEMPLATE)
    # POST: grade quiz
    q1 = request.form.get("q1")
    q2 = request.form.get("q2")
    q3 = request.form.get("q3")
    score = 0
    if q1 == "b": score += 1
    if q2 == "b": score += 1
    if q3 == "b": score += 1
    log_event(token, "training_completed", f"score={score}")
    log_event(token, "quiz", f"score={score}")
    return render_template_string(f"""
    <h3>Thanks — your score: {score}/3</h3>
    <p>Recommended next steps: review the lesson and contact security if you clicked on a suspicious link.</p>
    """)

# --- Exports and metrics ---
def export_weekly():
    # Exports two CSVs: per-user and campaign summary for the last 7 days
    cutoff = datetime.utcnow() - timedelta(days=7)
    cutoff_iso = cutoff.isoformat()
    # Gather recipients and events
    recipients = db_query("SELECT email, cohort, employee_id, token, campaign_id, template_id, sent_at FROM recipients")
    # Build per-user summary
    per_user_path = os.path.join(EXPORT_DIR, f"per_user_{datetime.utcnow().strftime('%Y%m%d')}.csv")
    with open(per_user_path, "w", newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["user_email","cohort","campaign_id","template_id","opened","clicked","reported","training_completed","quiz_score","time_to_report_min"])
        for email, cohort, employee_id, token, campaign_id, template_id, sent_at in recipients:
            events = db_query("SELECT event_type, details, timestamp FROM events WHERE token = ?", (token,))
            opened = any(e[0]=="open" for e in events)
            clicked = any(e[0]=="click" for e in events)
            reported = any(e[0]=="report" for e in events)
            training_completed = any(e[0]=="training_completed" for e in events)
            quiz_scores = [int(e[1].split("score=")[1]) for e in events if e[0]=="quiz" and "score=" in (e[1] or "")]
            quiz_score = quiz_scores[-1] if quiz_scores else ""
            # time to report
            send_time = datetime.fromisoformat(sent_at)
            report_times = [datetime.fromisoformat(e[2]) for e in events if e[0]=="report"]
            ttr = ""
            if report_times:
                delta = (report_times[0] - send_time).total_seconds() / 60.0
                ttr = round(delta, 2)
            writer.writerow([email, cohort, campaign_id, template_id, opened, clicked, reported, training_completed, quiz_score, ttr])
    # Campaign summary
    campaign_rows = db_query("SELECT DISTINCT campaign_id FROM recipients")
    campaign_path = os.path.join(EXPORT_DIR, f"campaign_summary_{datetime.utcnow().strftime('%Y%m%d')}.csv")
    with open(campaign_path, "w", newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["campaign_id","target_count","click_rate_pct","report_rate_pct","median_time_to_report_min"])
        for (campaign_id,) in campaign_rows:
            recs = db_query("SELECT email, token, sent_at FROM recipients WHERE campaign_id = ?", (campaign_id,))
            target_count = len(recs)
            clicks = 0
            reports = []
            for email, token, sent_at in recs:
                evs = db_query("SELECT event_type, timestamp FROM events WHERE token = ?", (token,))
                if any(e[0]=="click" for e in evs): clicks += 1
                rts = [datetime.fromisoformat(e[1]) for e in evs if e[0]=="report"]
                if rts:
                    send_time = datetime.fromisoformat(sent_at)
                    reports.append((rts[0] - send_time).total_seconds() / 60.0)
            click_rate = round(100.0 * clicks / target_count, 2) if target_count else 0.0
            report_rate = round(100.0 * len(reports) / target_count, 2) if target_count else 0.0
            median_ttr = ""
            if reports:
                reports.sort()
                mid = len(reports)//2
                median = (reports[mid] if len(reports)%2==1 else (reports[mid-1]+reports[mid])/2.0)
                median_ttr = round(median, 2)
            writer.writerow([campaign_id, target_count, click_rate, report_rate, median_ttr])
    return per_user_path, campaign_path

@app.route("/export_weekly", methods=["POST", "GET"])
def export_weekly_endpoint():
    per_user, campaign = export_weekly()
    return jsonify({"per_user_csv": per_user, "campaign_csv": campaign})

# --- Safety: simple admin check (very basic) ---
def authorized():
    # In production, replace with real auth. For local dev, allow all.
    return True

if __name__ == "__main__":
    init_db()
    print("Starting Phishing Simulation app (dev). Ensure Mailhog is running on localhost:1025.")
    app.run(debug=True)
