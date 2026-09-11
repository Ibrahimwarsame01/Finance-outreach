"""Regression tests for robots_allowed.

The bug these guard against: stdlib RobotFileParser.read() fetches robots.txt
with Python's default urllib User-Agent, which WAFs often answer with 403 —
and RobotFileParser then treats 403 as "disallow everything", wrongly skipping
sites that actually permit crawling.
"""
from src import webutil


class _FakeResp:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


def _patch(monkeypatch, resp):
    monkeypatch.setattr(webutil.requests, "get", lambda *a, **k: resp)


# A real-world robots.txt (Yoast/WPForms style) that allows everything except
# one uploads path — the exact shape that tripped the stdlib parser.
_ALLOWING_ROBOTS = """Crawl-delay: 10
User-agent: *
Disallow: /wp-content/uploads/wpforms/
User-agent: *
Disallow:
"""


def test_allows_contact_page_when_robots_permits(monkeypatch):
    _patch(monkeypatch, _FakeResp(200, _ALLOWING_ROBOTS))
    assert webutil.robots_allowed("https://x.com/contact") is True


def test_still_respects_a_real_disallow(monkeypatch):
    _patch(monkeypatch, _FakeResp(200, _ALLOWING_ROBOTS))
    assert webutil.robots_allowed("https://x.com/wp-content/uploads/wpforms/f") is False


def test_403_on_robots_is_treated_as_allowed(monkeypatch):
    """A WAF blocking robots.txt must NOT become a blanket disallow."""
    _patch(monkeypatch, _FakeResp(403))
    assert webutil.robots_allowed("https://x.com/contact") is True


def test_404_robots_is_allowed(monkeypatch):
    _patch(monkeypatch, _FakeResp(404))
    assert webutil.robots_allowed("https://x.com/anything") is True


def test_network_error_is_allowed(monkeypatch):
    def boom(*a, **k):
        raise webutil.requests.RequestException("dns fail")
    monkeypatch.setattr(webutil.requests, "get", boom)
    assert webutil.robots_allowed("https://x.com/contact") is True


def test_explicit_full_disallow_is_respected(monkeypatch):
    _patch(monkeypatch, _FakeResp(200, "User-agent: *\nDisallow: /\n"))
    assert webutil.robots_allowed("https://x.com/contact") is False
