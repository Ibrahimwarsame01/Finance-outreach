import email
import imaplib
import logging
import yaml
import os
from datetime import datetime, timedelta
from email.header import decode_header
from src import supabase_client

logger = logging.getLogger(__name__)


def _load_senders() -> list[dict]:
    with open("config.yaml") as f:
        return yaml.safe_load(f).get("senders", [])


def _get_app_password(sender: dict) -> str | None:
    env_var = sender.get("app_password_env", "")
    return os.environ.get(env_var)


def _decode_header_value(value: str) -> str:
    parts = decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)


def _get_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
    return ""


def _check_mailbox(sender_email: str, app_password: str) -> int:
    sent_rows = supabase_client.get_sent_message_ids(sender_email)
    if not sent_rows:
        return 0

    # Map message_id → sent_log row id
    id_map = {row["message_id"]: row["id"] for row in sent_rows if row.get("message_id")}
    if not id_map:
        return 0

    logged = 0
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(sender_email, app_password)
        mail.select("INBOX")

        # Search inbox for emails from the last 30 days
        since = (datetime.utcnow() - timedelta(days=30)).strftime("%d-%b-%Y")
        _, data = mail.search(None, "SINCE", since)
        msg_nums = data[0].split()

        for num in msg_nums:
            _, raw = mail.fetch(num, "(RFC822)")
            raw_email = raw[0][1]
            msg = email.message_from_bytes(raw_email)

            in_reply_to = msg.get("In-Reply-To", "").strip()
            references = msg.get("References", "").strip().split()

            # Check if this email is a reply to any of our sent messages
            matched_id = None
            if in_reply_to and in_reply_to in id_map:
                matched_id = id_map[in_reply_to]
            else:
                for ref in references:
                    if ref in id_map:
                        matched_id = id_map[ref]
                        break

            if not matched_id:
                continue

            if supabase_client.reply_already_logged(matched_id):
                continue

            from_addr = _decode_header_value(msg.get("From", ""))
            body = _get_body(msg)
            supabase_client.log_reply(matched_id, from_addr, body)
            logged += 1
            logger.info("Logged reply from %s", from_addr)

        mail.logout()
    except imaplib.IMAP4.error as e:
        logger.error("IMAP error for %s: %s", sender_email, e)

    return logged


def run_check_replies() -> int:
    senders = _load_senders()
    total = 0
    for s in senders:
        app_pw = _get_app_password(s)
        if not app_pw:
            continue
        total += _check_mailbox(s["email"], app_pw)
    logger.info("Reply check complete: %d new replies logged", total)
    return total
