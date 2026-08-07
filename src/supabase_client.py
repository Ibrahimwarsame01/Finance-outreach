import os
from supabase import create_client, Client

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        _client = create_client(url, key)
    return _client


def insert_lead(lead: dict) -> dict | None:
    client = get_client()
    result = client.table("leads").upsert(lead, on_conflict="job_url").execute()
    return result.data[0] if result.data else None


def get_unsent_leads() -> list[dict]:
    """Leads that have a contact email and have not yet been sent.

    Done as two queries + a Python filter rather than a PostgREST embedded
    anti-join: filtering on an embedded column (sent_log.id=is.null) filters
    the embedded rows, NOT the parent leads, so it would wrongly return
    already-sent leads and risk re-emailing them.
    """
    client = get_client()

    sent = client.table("sent_log").select("lead_id").execute()
    sent_ids = {row["lead_id"] for row in (sent.data or []) if row.get("lead_id")}

    leads = (
        client.table("leads")
        .select("*")
        .not_.is_("contact_email", "null")
        .execute()
    )
    return [lead for lead in (leads.data or []) if lead["id"] not in sent_ids]


def is_unsubscribed(email: str) -> bool:
    client = get_client()
    result = (
        client.table("unsubscribed")
        .select("email")
        .eq("email", email.lower())
        .execute()
    )
    return len(result.data) > 0


def log_send(lead_id: str, sender: str, subject: str, message_id: str) -> dict:
    client = get_client()
    result = client.table("sent_log").insert({
        "lead_id": lead_id,
        "sender": sender,
        "subject": subject,
        "message_id": message_id,
    }).execute()
    return result.data[0]


def get_today_send_count(sender_email: str) -> int:
    from datetime import date
    client = get_client()
    today = date.today().isoformat()
    result = (
        client.table("sent_log")
        .select("id", count="exact")
        .eq("sender", sender_email)
        .gte("sent_at", f"{today}T00:00:00")
        .execute()
    )
    return result.count or 0


def get_sent_message_ids(sender_email: str) -> list[str]:
    client = get_client()
    result = (
        client.table("sent_log")
        .select("id, message_id")
        .eq("sender", sender_email)
        .not_.is_("message_id", "null")
        .execute()
    )
    return result.data or []


def reply_already_logged(sent_log_id: str) -> bool:
    client = get_client()
    result = (
        client.table("replies")
        .select("id")
        .eq("sent_log_id", sent_log_id)
        .execute()
    )
    return len(result.data) > 0


def log_reply(sent_log_id: str, reply_from: str, reply_body: str) -> None:
    client = get_client()
    client.table("replies").insert({
        "sent_log_id": sent_log_id,
        "reply_from": reply_from,
        "reply_body": reply_body,
    }).execute()


def add_unsubscribe(email: str) -> None:
    client = get_client()
    client.table("unsubscribed").upsert({"email": email.lower()}).execute()
