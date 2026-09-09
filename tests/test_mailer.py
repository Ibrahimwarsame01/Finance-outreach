from datetime import date, timedelta

from src import mailer


def test_current_cap_ramps_over_weeks():
    today = date.today()

    def cap_after(days_ago: int) -> int:
        start = (today - timedelta(days=days_ago)).isoformat()
        return mailer.current_cap(start, max_daily_cap=100)

    assert cap_after(0) == 10    # day 1
    assert cap_after(6) == 10    # day 7
    assert cap_after(7) == 30    # day 8
    assert cap_after(13) == 30   # day 14
    assert cap_after(14) == 60   # day 15
    assert cap_after(20) == 60   # day 21
    assert cap_after(21) == 100  # day 22 → full cap
    assert cap_after(60) == 100


def test_new_message_id_uses_domain():
    mid = mailer.new_message_id("outreach.example.com")
    assert mid.startswith("<") and mid.endswith("@outreach.example.com>")


def test_sender_domain():
    assert mailer.sender_domain("alex@outreach.example.com") == "outreach.example.com"


def test_build_message_basic_multipart():
    msg = mailer.build_message(
        "alex@d.com", "lead@x.com", "Hi there", "Line one\nLine two", "<abc@d.com>"
    )
    assert msg["Subject"] == "Hi there"
    assert msg["From"] == "alex@d.com"
    assert msg["To"] == "lead@x.com"
    assert msg["Message-ID"] == "<abc@d.com>"
    # No threading headers when not a reply
    assert msg["In-Reply-To"] is None
    parts = msg.get_payload()
    assert len(parts) == 2  # plain + html
    assert parts[0].get_content_type() == "text/plain"
    assert parts[1].get_content_type() == "text/html"


def test_build_message_threading_and_extra_headers():
    msg = mailer.build_message(
        "alex@d.com",
        "lead@x.com",
        "Re: Hi",
        "a follow-up",
        "<new@d.com>",
        in_reply_to="<orig@d.com>",
        extra_headers={"X-Outreach-Warmup": "1"},
    )
    assert msg["In-Reply-To"] == "<orig@d.com>"
    # References falls back to the parent when not given explicitly
    assert msg["References"] == "<orig@d.com>"
    assert msg["X-Outreach-Warmup"] == "1"
