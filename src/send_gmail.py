import os
import uuid
import smtplib
import logging
import yaml
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from src import supabase_client

logger = logging.getLogger(__name__)

WARMUP_RAMP = [
    (7, 10),   # days 1-7   → 10/day
    (14, 30),  # days 8-14  → 30/day
    (21, 60),  # days 15-21 → 60/day
]


def _current_cap(warmup_start: str, max_daily_cap: int) -> int:
    start = date.fromisoformat(warmup_start)
    days_since = (date.today() - start).days + 1
    for threshold, cap in WARMUP_RAMP:
        if days_since <= threshold:
            return cap
    return max_daily_cap


def _load_senders() -> list[dict]:
    with open("config.yaml") as f:
        return yaml.safe_load(f).get("senders", [])


def _get_app_password(sender: dict) -> str | None:
    env_var = sender.get("app_password_env", "")
    return os.environ.get(env_var)


def _build_message(
    sender_email: str,
    to_email: str,
    subject: str,
    body: str,
    message_id: str,
) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Message-ID"] = message_id
    msg["Date"] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")

    plain = MIMEText(body, "plain", "utf-8")
    html_body = body.replace("\n", "<br>")
    html = MIMEText(f"<html><body><p>{html_body}</p></body></html>", "html", "utf-8")
    msg.attach(plain)
    msg.attach(html)
    return msg


def _send_smtp(sender_email: str, app_password: str, to_email: str, msg: MIMEMultipart) -> None:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, app_password)
        server.sendmail(sender_email, to_email, msg.as_string())


def _sender_domain(email: str) -> str:
    return email.split("@")[-1]


def run_sends() -> int:
    senders = _load_senders()
    leads = supabase_client.get_unsent_leads()

    # Filter to only leads with drafted emails and contact emails
    ready = [
        l for l in leads
        if l.get("contact_email") and l.get("email_subject") and l.get("email_body")
    ]

    if not ready:
        logger.info("No leads ready to send")
        return 0

    # Build per-sender remaining cap
    sender_caps: list[dict] = []
    for s in senders:
        app_pw = _get_app_password(s)
        if not app_pw:
            logger.warning("No app password for %s — skipping", s["email"])
            continue
        cap = _current_cap(s["warmup_start"], s["max_daily_cap"])
        sent_today = supabase_client.get_today_send_count(s["email"])
        remaining = cap - sent_today
        if remaining > 0:
            sender_caps.append({**s, "remaining": remaining, "app_password": app_pw})

    if not sender_caps:
        logger.info("All mailboxes at daily cap — skipping send run")
        return 0

    sent_count = 0
    rr = 0  # round-robin pointer across mailboxes

    for lead in ready:
        # Stop once every mailbox has exhausted its remaining cap
        if all(s["remaining"] <= 0 for s in sender_caps):
            break

        to_email = lead["contact_email"]

        if supabase_client.is_unsubscribed(to_email):
            logger.info("Skipping unsubscribed %s", to_email)
            continue

        # Pick the next mailbox (round-robin) that still has cap left today
        sender = None
        for _ in range(len(sender_caps)):
            candidate = sender_caps[rr % len(sender_caps)]
            rr += 1
            if candidate["remaining"] > 0:
                sender = candidate
                break
        if sender is None:
            break

        domain = _sender_domain(sender["email"])
        message_id = f"<{uuid.uuid4()}@{domain}>"
        msg = _build_message(
            sender["email"],
            to_email,
            lead["email_subject"],
            lead["email_body"],
            message_id,
        )

        try:
            _send_smtp(sender["email"], sender["app_password"], to_email, msg)
        except smtplib.SMTPException as e:
            logger.error("SMTP error sending to %s via %s: %s", to_email, sender["email"], e)
            continue

        supabase_client.log_send(
            lead_id=lead["id"],
            sender=sender["email"],
            subject=lead["email_subject"],
            message_id=message_id,
        )

        logger.info("Sent to %s via %s", to_email, sender["email"])
        sent_count += 1
        sender["remaining"] -= 1

    logger.info("Send run complete: %d emails sent", sent_count)
    return sent_count
