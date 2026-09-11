from datetime import datetime, timedelta, timezone

import pytest

from src import followup, mailer, supabase_client, personalize


NOW = datetime(2026, 9, 9, 12, 0, 0, tzinfo=timezone.utc)


def _iso(days_ago: float) -> str:
    return (NOW - timedelta(days=days_ago)).isoformat()


def test_parse_ts_handles_z_suffix():
    assert followup._parse_ts("2026-09-09T12:00:00Z") == NOW


def test_re_subject():
    assert followup._re_subject("Quick idea") == "Re: Quick idea"
    assert followup._re_subject("Re: Quick idea") == "Re: Quick idea"
    assert followup._re_subject("") == "Following up"
    assert followup._re_subject(None) == "Following up"


@pytest.fixture
def wired(monkeypatch):
    """Wire followup's dependencies to in-memory fakes (no network)."""
    sent_smtp: list[dict] = []
    logged: list[dict] = []

    followups_cfg = {
        "enabled": True,
        "steps": [
            {"delay_days": 3, "prompt": "p1"},
            {"delay_days": 5, "prompt": "p2"},
        ],
    }
    senders = [{
        "email": "a@d.com",
        "warmup_start": "2020-01-01",  # long warmed → full cap
        "max_daily_cap": 100,
        "app_password_env": "PW",
    }]

    monkeypatch.setattr(mailer, "load_config", lambda: {"followups": followups_cfg})
    monkeypatch.setattr(mailer, "load_senders", lambda: senders)
    monkeypatch.setattr(mailer, "get_app_password", lambda s: "pw")
    monkeypatch.setattr(mailer, "send_smtp",
                        lambda se, pw, to, msg: sent_smtp.append({"to": to, "msg": msg}))

    monkeypatch.setattr(supabase_client, "get_today_send_count", lambda e: 0)
    monkeypatch.setattr(supabase_client, "get_unsubscribed_set", lambda: {"unsub@x.com"})
    monkeypatch.setattr(supabase_client, "get_replied_sent_log_ids", lambda: {"s3"})
    monkeypatch.setattr(
        supabase_client, "log_send",
        lambda **kw: logged.append(kw) or {"id": "new"},
    )

    monkeypatch.setattr(personalize, "draft_followup", lambda lead, prompt: "body text")
    monkeypatch.setattr(
        personalize, "finalize_body",
        lambda body, lead, sender=None: body + "\n--sig--",
    )

    return {"sent": sent_smtp, "logged": logged}


def _leads():
    return {
        "lead-old": {"id": "lead-old", "company": "Old Co", "job_title": "Controller",
                     "contact_email": "old@x.com", "email_subject": "Quick idea"},
        "lead-recent": {"id": "lead-recent", "company": "New Co", "job_title": "Accountant",
                        "contact_email": "recent@x.com", "email_subject": "Hello"},
        "lead-replied": {"id": "lead-replied", "company": "Rep Co", "job_title": "CFO",
                         "contact_email": "rep@x.com", "email_subject": "Hi"},
        "lead-unsub": {"id": "lead-unsub", "company": "Unsub Co", "job_title": "Bookkeeper",
                       "contact_email": "unsub@x.com", "email_subject": "Yo"},
    }


def test_followup_sends_only_to_due_unreplied_subscribed(monkeypatch, wired):
    sent_log = [
        {"id": "s1", "lead_id": "lead-old", "sender": "a@d.com",
         "sent_at": _iso(5), "message_id": "<m1>", "step": 0},
        {"id": "s2", "lead_id": "lead-recent", "sender": "a@d.com",
         "sent_at": _iso(1), "message_id": "<m2>", "step": 0},   # too recent (delay 3)
        {"id": "s3", "lead_id": "lead-replied", "sender": "a@d.com",
         "sent_at": _iso(10), "message_id": "<m3>", "step": 0},  # replied
        {"id": "s4", "lead_id": "lead-unsub", "sender": "a@d.com",
         "sent_at": _iso(5), "message_id": "<m4>", "step": 0},   # unsubscribed
    ]
    monkeypatch.setattr(supabase_client, "get_sent_log_full", lambda: sent_log)
    monkeypatch.setattr(supabase_client, "get_leads_by_ids", lambda ids: _leads())

    count = followup.run_followups(now=NOW)

    assert count == 1
    assert len(wired["sent"]) == 1
    assert wired["sent"][0]["to"] == "old@x.com"

    # Correct step + threading recorded
    logged = wired["logged"]
    assert len(logged) == 1
    assert logged[0]["step"] == 1
    assert logged[0]["in_reply_to"] == "<m1>"
    assert logged[0]["subject"] == "Re: Quick idea"


def test_followup_advances_to_second_step(monkeypatch, wired):
    # lead-old already got step 1 six days ago → due for step 2 (delay 5)
    sent_log = [
        {"id": "s1", "lead_id": "lead-old", "sender": "a@d.com",
         "sent_at": _iso(20), "message_id": "<m1>", "step": 0},
        {"id": "s1b", "lead_id": "lead-old", "sender": "a@d.com",
         "sent_at": _iso(6), "message_id": "<m1b>", "step": 1},
    ]
    monkeypatch.setattr(supabase_client, "get_sent_log_full", lambda: sent_log)
    monkeypatch.setattr(supabase_client, "get_leads_by_ids", lambda ids: _leads())

    count = followup.run_followups(now=NOW)
    assert count == 1
    assert wired["logged"][0]["step"] == 2
    assert wired["logged"][0]["in_reply_to"] == "<m1b>"  # threads onto latest


def test_followup_stops_after_last_step(monkeypatch, wired):
    # Already at step 2 (== len(steps)) → sequence exhausted
    sent_log = [
        {"id": "s1", "lead_id": "lead-old", "sender": "a@d.com",
         "sent_at": _iso(30), "message_id": "<m1>", "step": 2},
    ]
    monkeypatch.setattr(supabase_client, "get_sent_log_full", lambda: sent_log)
    monkeypatch.setattr(supabase_client, "get_leads_by_ids", lambda ids: _leads())

    assert followup.run_followups(now=NOW) == 0
    assert wired["sent"] == []


def test_followup_respects_disabled(monkeypatch):
    monkeypatch.setattr(mailer, "load_config", lambda: {"followups": {"enabled": False}})
    assert followup.run_followups(now=NOW) == 0
