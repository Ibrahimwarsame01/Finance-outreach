"""Shared HTTP helpers for the scraping/email-finding steps.

Notably a correct ``robots_allowed`` check. The stdlib ``RobotFileParser.read()``
fetches robots.txt with Python's default urllib User-Agent, which many WAFs
(Cloudflare, Wordfence, etc.) answer with a 403 — and RobotFileParser treats a
403 as "disallow everything", so a site that actually permits crawling gets
wrongly skipped. We instead fetch robots.txt with our own User-Agent and parse
the body, following Google's convention for status codes: 2xx -> obey the rules,
4xx -> allow all (no usable rules), other/error -> assume allowed.
"""
import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

logger = logging.getLogger(__name__)

USER_AGENT = "finance-outreach-bot/1.0 (job board research)"
HEADERS = {"User-Agent": USER_AGENT}


def robots_allowed(url: str, user_agent: str = "*") -> bool:
    """Whether ``url`` may be fetched per its site's robots.txt.

    Fetches robots.txt with our real User-Agent (so a WAF 403 on the default
    urllib agent doesn't masquerade as a blanket Disallow). Assumes allowed if
    robots.txt is missing (4xx) or unreachable.
    """
    try:
        p = urlparse(url)
        robots_url = f"{p.scheme}://{p.netloc}/robots.txt"
        resp = requests.get(robots_url, headers=HEADERS, timeout=15)
    except requests.RequestException:
        return True  # unreachable — assume allowed

    if resp.status_code >= 400:
        return True  # no usable rules (404) or blocked (403) — treat as allowed

    rp = RobotFileParser()
    rp.parse(resp.text.splitlines())
    return rp.can_fetch(user_agent, url)
