import email

from src import warmup, mailer, supabase_client


def test_subject_builds_from_snippet_with_prefix():
    s = warmup._subject("[wu]", "Quick note about the numbers this week")
    assert s == "[wu] Quick note about the"


def test_is_warmup_detects_header_or_prefix():
    m1 = email.message_from_string("X-Outreach-Warmup: 1\r\nSubject: anything\r\n\r\nbody")
    assert warmup._is_warmup(m1, "[wu]") is True

    m2 = email.message_from_string("Subject: [wu] touching base\r\n\r\nbody")
    assert warmup._is_warmup(m2, "[wu]") is True

    m3 = email.message_from_string("Subject: real outreach\r\n\r\nbody")
    assert warmup._is_warmup(m3, "[wu]") is False


def test_send_warmups_round_robins_between_mailboxes(monkeypatch):
    sent: list[dict] = []
    logged: list[dict] = []

    monkeypatch.setattr(mailer, "send_smtp",
                        lambda se, pw, to, msg: sent.append({"from": se, "to": to, "msg": msg}))
    monkeypatch.setattr(supabase_client, "get_today_warmup_count", lambda e: 0)
    monkeypatch.setattr(supabase_client, "log_warmup",
                        lambda s, r, mid, kind="sent": logged.append({"s": s, "r": r, "kind": kind}))

    cfg = {
        "subject_prefix": "[wu]",
        "daily_per_mailbox": 2,
        "snippets": ["hello there friend how are you"],
    }
    senders = [
        {"email": "a@d.com", "app_password": "pw"},
        {"email": "b@d.com", "app_password": "pw"},
    ]

    count = warmup._send_warmups(cfg, senders)

    # 2 mailboxes × 2/day = 4 warm-up emails, each to the OTHER mailbox
    assert count == 4
    assert len(sent) == 4
    for item in sent:
        assert item["from"] != item["to"]
        assert item["msg"]["X-Outreach-Warmup"] == "1"
        assert item["msg"]["Subject"].startswith("[wu]")
    assert all(row["kind"] == "sent" for row in logged)


def test_send_warmups_respects_already_sent_today(monkeypatch):
    sent: list[dict] = []
    monkeypatch.setattr(mailer, "send_smtp",
                        lambda se, pw, to, msg: sent.append(to))
    # Each mailbox already sent 2 today; cap is 2 → nothing more should go out
    monkeypatch.setattr(supabase_client, "get_today_warmup_count", lambda e: 2)
    monkeypatch.setattr(supabase_client, "log_warmup", lambda *a, **k: None)

    cfg = {"subject_prefix": "[wu]", "daily_per_mailbox": 2, "snippets": ["hi there ok"]}
    senders = [{"email": "a@d.com", "app_password": "pw"},
               {"email": "b@d.com", "app_password": "pw"}]

    assert warmup._send_warmups(cfg, senders) == 0
    assert sent == []


def test_run_warmup_needs_two_mailboxes(monkeypatch):
    monkeypatch.setattr(warmup, "_config", lambda: {"enabled": True})
    monkeypatch.setattr(warmup, "_usable_senders", lambda: [{"email": "a@d.com", "app_password": "pw"}])
    assert warmup.run_warmup() == 0


def test_run_warmup_disabled(monkeypatch):
    monkeypatch.setattr(warmup, "_config", lambda: {"enabled": False})
    assert warmup.run_warmup() == 0
