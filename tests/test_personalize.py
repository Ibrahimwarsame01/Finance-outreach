from src import personalize


LEAD = {"contact_email": "prospect@example.com", "company": "Acme"}


def test_signature_uses_sender_persona():
    """The signature name/title come from the sending mailbox, not a fixed value."""
    sender = {"name": "Sam Carter", "title": "Client Partnerships"}
    out = personalize.finalize_body("Hi there — quick idea.", LEAD, sender)

    assert "Sam Carter" in out
    assert "Client Partnerships" in out
    assert personalize.FOOTER_MARKER in out          # CASL unsubscribe footer present
    assert out.startswith("Hi there — quick idea.")   # original body preserved


def test_different_senders_get_different_signatures():
    a = personalize.finalize_body("Body.", LEAD, {"name": "Alex Brown", "title": "Client Partnerships"})
    b = personalize.finalize_body("Body.", LEAD, {"name": "Josh Wang", "title": "Client Partnerships"})
    assert "Alex Brown" in a and "Josh Wang" not in a
    assert "Josh Wang" in b and "Alex Brown" not in b


def test_finalize_body_is_idempotent():
    """A body that already has the footer is never signed twice."""
    once = personalize.finalize_body("Body.", LEAD, {"name": "Sam Carter", "title": "X"})
    twice = personalize.finalize_body(once, LEAD, {"name": "Sam Carter", "title": "X"})
    assert once == twice
    assert twice.count(personalize.FOOTER_MARKER) == 1


def test_outreach_config_issues_flags_placeholders():
    cfg = {
        "business_address": "YOUR_BUSINESS_ADDRESS",
        "unsubscribe_base_url": "https://YOUR_VERCEL_APP.vercel.app",
    }
    issues = personalize.outreach_config_issues(cfg)
    assert set(issues) == {"business_address", "unsubscribe_base_url"}


def test_outreach_config_issues_flags_blank():
    cfg = {"business_address": "  ", "unsubscribe_base_url": ""}
    assert set(personalize.outreach_config_issues(cfg)) == {"business_address", "unsubscribe_base_url"}


def test_outreach_config_issues_empty_when_ready():
    cfg = {
        "business_address": "123 Main St, Toronto, ON M5V 1A1",
        "unsubscribe_base_url": "https://clearbooks-outreach.vercel.app",
    }
    assert personalize.outreach_config_issues(cfg) == []
