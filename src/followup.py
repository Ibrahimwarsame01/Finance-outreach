"""Follow-up sequences.

Leads that were emailed but haven't replied get gentle, threaded follow-ups
according to the ``followups`` block in config.yaml. Each follow-up:

  * is sent from the SAME mailbox that started the thread (continuity + it's
    what a real person would do),
  * threads onto the previous message via In-Reply-To/References (lands in the
    same conversation, "Re: <original subject>"),
  * counts against that mailbox's daily warm-up cap (shared with outreach),
  * is skipped if the lead replied or unsubscribed.

Step numbering: the initial outreach is step 0. followups.steps[0] is the first
follow-up (step 1), steps[1] the second (step 2), and so on.
"""

import logging
import smtplib
from datetime import datetime, timezone

from src import supabase_client
from src import mailer
from src import personalize

logger = logging.getLogger(__name__)


def _parse_ts(value: str) -> datetime:
    """Parse a Supabase timestamptz string into an aware UTC datetime."""
    ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def _re_subject(subject: str | None) -> str:
    subject = (subject or "").strip()
    if not subject:
        return "Following up"
    if subject.lower().startswith("re:"):
        return subject
    return f"Re: {subject}"


def _latest_send(sends: list[dict]) -> dict:
    return max(sends, key=lambda s: s["sent_at"])


def run_followups(now: datetime | None = None) -> int:
    config = mailer.load_config().get("followups", {}) or {}
    if not config.get("enabled"):
        logger.info("Follow-ups disabled — skipping")
        return 0

    steps = config.get("steps", []) or []
    if not steps:
        logger.info("No follow-up steps configured — skipping")
        return 0

    # Same CASL preflight as initial sends: follow-ups also carry the footer.
    issues = personalize.outreach_config_issues()
    if issues:
        logger.warning(
            "Skipping follow-ups — outreach config not send-ready (fix in config.yaml): %s",
            ", ".join(issues),
        )
        return 0

    now = now or datetime.now(timezone.utc)

    # Mailbox state: only mailboxes with an app password can send. Track each
    # one's remaining daily cap so follow-ups respect the same limit as outreach.
    senders_by_email: dict[str, dict] = {}
    for s in mailer.load_senders():
        app_pw = mailer.get_app_password(s)
        if not app_pw:
            continue
        cap = mailer.current_cap(s["warmup_start"], s["max_daily_cap"])
        remaining = cap - supabase_client.get_today_send_count(s["email"])
        senders_by_email[s["email"]] = {"app_password": app_pw, "remaining": remaining, "config": s}

    if not senders_by_email:
        logger.info("No usable mailboxes for follow-ups — skipping")
        return 0

    sent_log = supabase_client.get_sent_log_full()
    if not sent_log:
        return 0
    replied_ids = supabase_client.get_replied_sent_log_ids()
    unsubscribed = supabase_client.get_unsubscribed_set()

    # Group every send by lead.
    by_lead: dict[str, list[dict]] = {}
    for row in sent_log:
        if row.get("lead_id"):
            by_lead.setdefault(row["lead_id"], []).append(row)

    # Decide which leads are due for a follow-up right now.
    due: list[dict] = []  # {lead_id, next_step, parent}
    for lead_id, sends in by_lead.items():
        # Skip if the lead replied anywhere in the thread.
        if any(s["id"] in replied_ids for s in sends):
            continue

        current_step = max(s.get("step", 0) for s in sends)
        if current_step >= len(steps):
            continue  # sequence exhausted

        parent = _latest_send(sends)
        delay_days = steps[current_step].get("delay_days", 3)
        age_days = (now - _parse_ts(parent["sent_at"])).total_seconds() / 86400
        if age_days < delay_days:
            continue

        due.append({"lead_id": lead_id, "next_step": current_step, "parent": parent})

    if not due:
        logger.info("No leads due for a follow-up")
        return 0

    leads = supabase_client.get_leads_by_ids([d["lead_id"] for d in due])

    sent_count = 0
    for item in due:
        lead = leads.get(item["lead_id"])
        if not lead:
            continue

        to_email = lead.get("contact_email")
        if not to_email:
            continue
        if to_email.lower() in unsubscribed:
            logger.info("Skipping unsubscribed %s", to_email)
            continue

        parent = item["parent"]
        sender_email = parent["sender"]
        state = senders_by_email.get(sender_email)
        if not state:
            logger.info("Original mailbox %s not available — skipping follow-up", sender_email)
            continue
        if state["remaining"] <= 0:
            logger.info("Mailbox %s at cap — deferring follow-up", sender_email)
            continue

        step_cfg = steps[item["next_step"]]
        try:
            body = personalize.draft_followup(lead, step_cfg.get("prompt", ""))
            body = personalize.finalize_body(body, lead, state["config"])
        except Exception as e:
            logger.error("Failed to draft follow-up for lead %s: %s", item["lead_id"], e)
            continue

        subject = _re_subject(lead.get("email_subject"))
        domain = mailer.sender_domain(sender_email)
        message_id = mailer.new_message_id(domain)
        msg = mailer.build_message(
            sender_email,
            to_email,
            subject,
            body,
            message_id,
            in_reply_to=parent.get("message_id"),
        )

        try:
            mailer.send_smtp(sender_email, state["app_password"], to_email, msg)
        except smtplib.SMTPException as e:
            logger.error("SMTP error sending follow-up to %s via %s: %s", to_email, sender_email, e)
            continue

        supabase_client.log_send(
            lead_id=item["lead_id"],
            sender=sender_email,
            subject=subject,
            message_id=message_id,
            step=item["next_step"] + 1,
            in_reply_to=parent.get("message_id"),
        )
        logger.info(
            "Follow-up step %d sent to %s via %s", item["next_step"] + 1, to_email, sender_email
        )
        sent_count += 1
        state["remaining"] -= 1

    logger.info("Follow-up run complete: %d follow-ups sent", sent_count)
    return sent_count
