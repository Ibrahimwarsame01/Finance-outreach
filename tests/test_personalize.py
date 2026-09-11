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
