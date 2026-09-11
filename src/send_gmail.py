import smtplib
import logging
from src import supabase_client
from src import mailer
from src import personalize

logger = logging.getLogger(__name__)


def run_sends() -> int:
    senders = mailer.load_senders()
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
        app_pw = mailer.get_app_password(s)
        if not app_pw:
            logger.warning("No app password for %s — skipping", s["email"])
            continue
        cap = mailer.current_cap(s["warmup_start"], s["max_daily_cap"])
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

        # Attach this mailbox's signature + CASL footer now, so the signature
        # persona matches the "From" mailbox.
        full_body = personalize.finalize_body(lead["email_body"], lead, sender)

        domain = mailer.sender_domain(sender["email"])
        message_id = mailer.new_message_id(domain)
        msg = mailer.build_message(
            sender["email"],
            to_email,
            lead["email_subject"],
            full_body,
            message_id,
        )

        try:
            mailer.send_smtp(sender["email"], sender["app_password"], to_email, msg)
        except smtplib.SMTPException as e:
            logger.error("SMTP error sending to %s via %s: %s", to_email, sender["email"], e)
            continue

        supabase_client.log_send(
            lead_id=lead["id"],
            sender=sender["email"],
            subject=lead["email_subject"],
            message_id=message_id,
            step=0,
        )

        logger.info("Sent to %s via %s", to_email, sender["email"])
        sent_count += 1
        sender["remaining"] -= 1

    logger.info("Send run complete: %d emails sent", sent_count)
    return sent_count
