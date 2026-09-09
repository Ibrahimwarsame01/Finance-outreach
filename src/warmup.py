"""Automated mailbox warm-up.

Before (and while) you send real cold outreach, your own mailboxes quietly email
each other so mailbox providers see natural, replied-to conversations from your
sending domain. Good sender reputation is what keeps your real pitch landing in
the inbox instead of spam.

Two phases per run (both driven entirely by the ``warmup`` block in config.yaml):

  1. SEND    — each mailbox sends up to ``daily_per_mailbox`` short warm-up
               emails to the other mailboxes, tagged with the ``subject_prefix``
               and an ``X-Outreach-Warmup`` header so they're never mistaken for
               outreach. Logged to the ``warmup_log`` table.
  2. RECEIVE — over IMAP, each mailbox rescues warm-up mail from Spam (so the
               provider learns these are wanted), auto-replies once to originals
               (real back-and-forth), and marks everything read.

Warm-up traffic is intentionally tiny and only ever flows between your own
mailboxes — it never emails a lead.
"""

import email
import imaplib
import logging
import random
import smtplib

from src import supabase_client
from src import mailer

logger = logging.getLogger(__name__)

WARMUP_HEADER = "X-Outreach-Warmup"
SPAM_FOLDER = "[Gmail]/Spam"


def _config() -> dict:
    return mailer.load_config().get("warmup", {}) or {}


def _usable_senders() -> list[dict]:
    """Senders that have an app password (needed to send + read over IMAP)."""
    out = []
    for s in mailer.load_senders():
        pw = mailer.get_app_password(s)
        if pw:
            out.append({"email": s["email"], "app_password": pw})
    return out


def _subject(prefix: str, snippet: str) -> str:
    core = " ".join(snippet.split()[:4]) or "touching base"
    return f"{prefix} {core}"


# ── Phase 1: send warm-up emails ──────────────────────────────────────────────

def _send_warmups(cfg: dict, senders: list[dict]) -> int:
    prefix = cfg.get("subject_prefix", "[wu]")
    snippets = cfg.get("snippets") or ["Quick note — following up. Talk soon."]
    per_mailbox = int(cfg.get("daily_per_mailbox", 0) or 0)
    if per_mailbox <= 0:
        return 0

    emails = [s["email"] for s in senders]
    sent = 0

    for s in senders:
        recipients = [e for e in emails if e != s["email"]]
        if not recipients:
            continue  # can't warm up a single lonely mailbox

        already = supabase_client.get_today_warmup_count(s["email"])
        to_send = max(0, per_mailbox - already)
        if to_send == 0:
            continue

        for i in range(to_send):
            recipient = recipients[(already + i) % len(recipients)]
            snippet = random.choice(snippets)
            domain = mailer.sender_domain(s["email"])
            message_id = mailer.new_message_id(domain)
            msg = mailer.build_message(
                s["email"],
                recipient,
                _subject(prefix, snippet),
                snippet,
                message_id,
                extra_headers={WARMUP_HEADER: "1"},
            )
            try:
                mailer.send_smtp(s["email"], s["app_password"], recipient, msg)
            except smtplib.SMTPException as e:
                logger.error("Warm-up send error %s → %s: %s", s["email"], recipient, e)
                continue

            supabase_client.log_warmup(s["email"], recipient, message_id, kind="sent")
            logger.info("Warm-up email %s → %s", s["email"], recipient)
            sent += 1

    return sent


# ── Phase 2: receive / rescue / auto-reply ────────────────────────────────────

def _is_warmup(msg: email.message.Message, prefix: str) -> bool:
    if msg.get(WARMUP_HEADER):
        return True
    subject = msg.get("Subject", "")
    return prefix and prefix in subject


def _rescue_from_spam(mail: imaplib.IMAP4_SSL, prefix: str) -> None:
    """Move any warm-up mail out of Spam into the inbox (best effort)."""
    try:
        status, _ = mail.select(SPAM_FOLDER)
        if status != "OK":
            return
        typ, data = mail.search(None, "SUBJECT", prefix)
        if typ != "OK":
            return
        for num in data[0].split():
            try:
                mail.copy(num, "INBOX")
                mail.store(num, "+FLAGS", "\\Deleted")
            except imaplib.IMAP4.error:
                continue
        mail.expunge()
    except imaplib.IMAP4.error as e:
        logger.debug("Spam rescue skipped for warm-up: %s", e)


def _process_inbox(cfg: dict, sender: dict) -> int:
    prefix = cfg.get("subject_prefix", "[wu]")
    auto_reply = bool(cfg.get("auto_reply", True))
    snippets = cfg.get("snippets") or ["Got it, thanks. Talk soon."]
    actions = 0

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(sender["email"], sender["app_password"])
    except imaplib.IMAP4.error as e:
        logger.error("Warm-up IMAP login failed for %s: %s", sender["email"], e)
        return 0

    try:
        if cfg.get("rescue_from_spam", True):
            _rescue_from_spam(mail, prefix)

        mail.select("INBOX")
        typ, data = mail.search(None, "UNSEEN", "SUBJECT", prefix)
        if typ != "OK":
            return 0

        for num in data[0].split():
            typ, raw = mail.fetch(num, "(RFC822)")
            if typ != "OK" or not raw or not raw[0]:
                continue
            msg = email.message_from_bytes(raw[0][1])

            if not _is_warmup(msg, prefix):
                continue

            # Only auto-reply to ORIGINAL warm-up emails (no In-Reply-To), so
            # replies don't bounce back and forth unbounded across runs.
            is_original = not msg.get("In-Reply-To")
            if auto_reply and is_original:
                parent_id = msg.get("Message-ID", "").strip()
                from_addr = email.utils.parseaddr(msg.get("From", ""))[1]
                if from_addr:
                    reply_body = random.choice(snippets)
                    reply_subject = msg.get("Subject", f"{prefix} re")
                    domain = mailer.sender_domain(sender["email"])
                    reply_id = mailer.new_message_id(domain)
                    reply_msg = mailer.build_message(
                        sender["email"],
                        from_addr,
                        reply_subject if reply_subject.lower().startswith("re:") else f"Re: {reply_subject}",
                        reply_body,
                        reply_id,
                        in_reply_to=parent_id or None,
                        extra_headers={WARMUP_HEADER: "1"},
                    )
                    try:
                        mailer.send_smtp(sender["email"], sender["app_password"], from_addr, reply_msg)
                        supabase_client.log_warmup(sender["email"], from_addr, reply_id, kind="reply")
                        actions += 1
                        logger.info("Warm-up auto-reply %s → %s", sender["email"], from_addr)
                    except smtplib.SMTPException as e:
                        logger.error("Warm-up reply error for %s: %s", sender["email"], e)

            # Mark read so it isn't reprocessed next run.
            mail.store(num, "+FLAGS", "\\Seen")

        mail.logout()
    except imaplib.IMAP4.error as e:
        logger.error("Warm-up IMAP error for %s: %s", sender["email"], e)

    return actions


def run_warmup() -> int:
    cfg = _config()
    if not cfg.get("enabled"):
        logger.info("Warm-up disabled — skipping")
        return 0

    senders = _usable_senders()
    if len(senders) < 2:
        logger.info("Warm-up needs 2+ mailboxes with app passwords — skipping")
        return 0

    actions = _send_warmups(cfg, senders)
    for s in senders:
        actions += _process_inbox(cfg, s)

    logger.info("Warm-up run complete: %d actions", actions)
    return actions
