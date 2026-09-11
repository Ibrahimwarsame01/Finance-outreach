import os
import logging
import yaml
import google.generativeai as genai

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        _model = genai.GenerativeModel("gemini-flash-latest")
    return _model


def _load_outreach_config() -> dict:
    with open("config.yaml") as f:
        return yaml.safe_load(f).get("outreach", {})


def draft_email(lead: dict) -> tuple[str, str]:
    """Return (subject, body) for a given lead dict."""
    cfg = _load_outreach_config()
    model = _get_model()

    prompt = f"""You are drafting a personalized cold outreach email.

Sender: {cfg.get('sender_name')} — {cfg.get('sender_title')} at {cfg.get('sender_company')}
Service being pitched: {cfg.get('service_pitch')}

Target company: {lead.get('company')}
Role they are hiring for: {lead.get('job_title')}

Write a SHORT, personalized cold email (under 180 words total) with these rules:
- Subject line first (label it "Subject:"), then blank line, then body
- Open with ONE specific observation about their hiring for {lead.get('job_title')} and what that signals about their growth or needs
- Pitch {cfg.get('service_pitch')} as a way to support that need without full-time overhead
- End with ONE low-friction CTA: "Would a 15-min call this week make sense?"
- No filler phrases ("Hope this finds you well", "I came across your posting")
- Sound like a human, not a template
- Do NOT sign off — signature will be added separately

Return only the subject line + body, nothing else.
"""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
    except Exception as e:
        logger.error("Gemini API error for lead %s: %s", lead.get("id"), e)
        raise

    lines = raw.splitlines()
    subject = ""
    body_lines = []
    in_body = False

    for line in lines:
        if line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
        elif subject and not in_body and line.strip() == "":
            in_body = True
        elif in_body or (subject and line.strip()):
            body_lines.append(line)
            in_body = True

    body = "\n".join(body_lines).strip()

    if not subject:
        subject = f"Quick question — {lead.get('company', 'your team')}"

    return subject, body


def draft_followup(lead: dict, step_prompt: str) -> str:
    """Draft a threaded follow-up body for a lead that hasn't replied.

    Returns only the body — no subject (follow-ups reuse the original subject,
    prefixed with "Re:", so they thread in the recipient's inbox).
    """
    cfg = _load_outreach_config()
    model = _get_model()

    prompt = f"""You are writing a follow-up in an existing cold email thread.

Sender: {cfg.get('sender_name')} — {cfg.get('sender_title')} at {cfg.get('sender_company')}
Service being pitched: {cfg.get('service_pitch')}
Target company: {lead.get('company')}
Role they are hiring for: {lead.get('job_title')}

Original email subject: {lead.get('email_subject')}

{step_prompt}

Rules:
- Under 90 words.
- No subject line, no greeting line with their name if you don't know it.
- No filler ("Hope this finds you well", "Just circling back").
- Sound like a real person nudging, not a template.
- Do NOT sign off — a signature is added separately.

Return only the follow-up body, nothing else.
"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error("Gemini API error drafting follow-up for lead %s: %s", lead.get("id"), e)
        raise


def personalize_unsent_leads() -> int:
    from src import supabase_client

    cfg = _load_outreach_config()
    leads = supabase_client.get_unsent_leads()

    drafted = 0
    for lead in leads:
        if lead.get("email_subject"):
            continue  # already drafted
        try:
            subject, body = draft_email(lead)
            # Store the RAW body (no signature). The signature + CASL footer are
            # attached at SEND time so they match the actual sending mailbox's
            # persona — see finalize_body() / send_gmail.
            supabase_client.get_client().table("leads").update({
                "email_subject": subject,
                "email_body": body,
            }).eq("id", lead["id"]).execute()
            drafted += 1
        except Exception as e:
            logger.error("Failed to draft for lead %s: %s", lead.get("id"), e)

    logger.info("Personalization complete: %d emails drafted", drafted)
    return drafted


def finalize_body(body: str, lead: dict, sender: dict | None = None) -> str:
    """Public: attach signature + CASL footer for a specific sending mailbox.

    ``sender`` is a senders[] entry from config.yaml (with name/title). The
    signature uses that mailbox's persona so the "From" name always matches the
    signature. Falls back to outreach.sender_name/title if not given.

    Idempotent: if the body already carries the unsubscribe footer (e.g. an old
    draft that was signed at draft time), it's returned unchanged so it never
    gets double-signed.
    """
    if FOOTER_MARKER in body:
        return body
    return _add_signature_and_footer(body, lead, _load_outreach_config(), sender)


FOOTER_MARKER = "To unsubscribe:"


def _add_signature_and_footer(body: str, lead: dict, cfg: dict, sender: dict | None = None) -> str:
    sender = sender or {}
    name = sender.get("name") or cfg.get("sender_name")
    title = sender.get("title") or cfg.get("sender_title")
    unsubscribe_url = _unsubscribe_url(lead.get("contact_email", ""), cfg)
    signature = (
        f"\n\nBest,\n"
        f"{name}\n"
        f"{title}, {cfg.get('sender_company')}\n"
        f"{cfg.get('website', '')}"
    )
    footer = (
        f"\n\n---\n"
        f"{cfg.get('sender_company')} | {cfg.get('business_address')}\n"
        f"{FOOTER_MARKER} {unsubscribe_url}"
    )
    return body + signature + footer


def _unsubscribe_url(email: str, cfg: dict) -> str:
    import hmac
    import hashlib
    import base64

    secret = os.environ.get("UNSUBSCRIBE_SECRET", "")
    token = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), email.lower().encode(), hashlib.sha256).digest()
    ).decode().rstrip("=")
    base = cfg.get("unsubscribe_base_url", "https://yourapp.vercel.app")
    return f"{base}/api/unsubscribe?email={email}&token={token}"
