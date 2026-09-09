"""Shared email plumbing used by send_gmail, followup, and warmup.

Keeping message construction, SMTP sending, sender-config loading, and the
warm-up cap ramp in one place means the outreach sender, the follow-up sender,
and the warm-up engine all behave identically (threading headers, encoding,
caps) instead of drifting apart.
"""

import os
import uuid
import smtplib
import yaml
from datetime import date, datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

CONFIG_PATH = "config.yaml"

# Per-mailbox daily cap ramps up over the first weeks of warm-up. Values are
# (max day-of-warmup inclusive, cap). After the last threshold, max_daily_cap
# from config applies.
WARMUP_RAMP = [
    (7, 10),   # days 1-7   → 10/day
    (14, 30),  # days 8-14  → 30/day
    (21, 60),  # days 15-21 → 60/day
]


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f) or {}


def load_senders() -> list[dict]:
    return load_config().get("senders", []) or []


def get_app_password(sender: dict) -> str | None:
    env_var = sender.get("app_password_env", "")
    return os.environ.get(env_var)


def sender_domain(email: str) -> str:
    return email.split("@")[-1]


def new_message_id(domain: str) -> str:
    return f"<{uuid.uuid4()}@{domain}>"


def current_cap(warmup_start: str, max_daily_cap: int) -> int:
    """Allowed sends today for a mailbox, based on days since warm-up start."""
    start = date.fromisoformat(warmup_start)
    days_since = (date.today() - start).days + 1
    for threshold, cap in WARMUP_RAMP:
        if days_since <= threshold:
            return cap
    return max_daily_cap


def build_message(
    sender_email: str,
    to_email: str,
    subject: str,
    body: str,
    message_id: str,
    in_reply_to: str | None = None,
    references: str | None = None,
    extra_headers: dict[str, str] | None = None,
) -> MIMEMultipart:
    """Build a multipart (plain + HTML) email.

    ``in_reply_to`` / ``references`` set the RFC 5322 threading headers so
    follow-ups and warm-up replies land in the same conversation as the
    original message instead of as fresh emails.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Message-ID"] = message_id
    msg["Date"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        # References should chain the whole thread; fall back to just the parent.
        msg["References"] = references or in_reply_to

    for key, value in (extra_headers or {}).items():
        msg[key] = value

    plain = MIMEText(body, "plain", "utf-8")
    html_body = body.replace("\n", "<br>")
    html = MIMEText(f"<html><body><p>{html_body}</p></body></html>", "html", "utf-8")
    msg.attach(plain)
    msg.attach(html)
    return msg


def send_smtp(sender_email: str, app_password: str, to_email: str, msg: MIMEMultipart) -> None:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, app_password)
        server.sendmail(sender_email, to_email, msg.as_string())
