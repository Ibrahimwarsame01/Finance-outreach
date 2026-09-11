"""Find a public contact email for a lead by scraping its own website.

Job boards give a company + a job URL but almost never a contact email, and
``get_unsent_leads()`` skips any lead whose ``contact_email`` is null — so
without this step career-page leads never get emailed. This module fills that
gap: for a lead on a company's own domain, it fetches a few likely pages
(home, /contact, /about, /careers), pulls every email it can find, scores them
(prefer a role-based address on the company's own domain), and writes the best
one back to the lead.

Only public pages the site allows (robots.txt is honoured). Sends nothing.

The scoring/extraction/URL logic is kept as small pure functions so it can be
unit-tested without any network access; ``find_contact_email`` and
``run_find_emails`` are the thin network/DB layers on top.
"""
import logging
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from src import supabase_client, webutil

logger = logging.getLogger(__name__)

_HEADERS = webutil.HEADERS

# Job boards / aggregators — a job_url on one of these tells us nothing about
# the company's own domain, so we can't mine a contact email from it.
JOB_BOARD_DOMAINS = {
    "remoteok.com", "remoteok.io", "indeed.com", "ziprecruiter.com",
    "linkedin.com", "glassdoor.com", "lever.co", "greenhouse.io",
    "workable.com", "smartrecruiters.com", "myworkdayjobs.com",
    "bamboohr.com", "jobs.lever.co", "boards.greenhouse.io",
}

# Pages most likely to carry a public contact address, relative to the site root.
CONTACT_PATHS = ["", "/contact", "/contact-us", "/contactus", "/about",
                 "/about-us", "/careers", "/jobs", "/company"]

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# Local-part prefixes we prefer for cold outreach, best first.
_PREFERRED_PREFIXES = ["careers", "jobs", "recruiting", "hr", "hiring",
                       "people", "talent", "info", "contact", "hello",
                       "admin", "office", "sales"]

# Addresses that are never useful to email.
_BAD_PREFIXES = ("noreply", "no-reply", "donotreply", "postmaster", "mailer-daemon",
                 "abuse", "unsubscribe")
# Emails from example/CDN/tracking domains, or files misread as emails.
_BAD_DOMAIN_SUBSTR = ("example.com", "sentry.", "wixpress.com", "@2x", "@3x",
                      "domain.com", "yourdomain.com", "email.com")
_IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")


def registrable_domain(host: str) -> str:
    """Best-effort registrable domain (last two labels) for comparison.

    ``www.hinestrucking.com`` -> ``hinestrucking.com``. Good enough to tell a
    same-company address from a third-party one; not a full public-suffix parse.
    """
    host = (host or "").lower().split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    return ".".join(labels[-2:])


def is_job_board(url: str) -> bool:
    host = registrable_domain(urlparse(url).netloc)
    return host in JOB_BOARD_DOMAINS


def base_url_for_lead(lead: dict) -> str | None:
    """The company's own site root to crawl, or None if we can't determine it.

    Prefers an explicit ``website``/``company_domain`` field; otherwise derives
    it from ``job_url`` — unless that URL is on a job board, in which case we
    have no company domain to work with.
    """
    site = lead.get("website") or lead.get("company_domain")
    if site:
        if not site.startswith("http"):
            site = "https://" + site
        p = urlparse(site)
        return f"{p.scheme}://{p.netloc}"

    job_url = lead.get("job_url") or ""
    if not job_url.startswith("http") or is_job_board(job_url):
        return None
    p = urlparse(job_url)
    return f"{p.scheme}://{p.netloc}"


def candidate_urls(base_url: str) -> list[str]:
    """Likely contact-bearing pages for a site root, de-duplicated, in order."""
    seen: set[str] = set()
    out: list[str] = []
    for path in CONTACT_PATHS:
        url = urljoin(base_url + "/", path.lstrip("/"))
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def extract_emails(html: str) -> list[str]:
    """All plausible email addresses in a page (mailto: links + body text).

    Order-preserving and de-duplicated (case-insensitively).
    """
    emails: list[str] = []
    seen: set[str] = set()

    def _add(candidate: str) -> None:
        e = candidate.strip().strip(".,;:()<>\"'").lower()
        if e and e not in seen and _EMAIL_RE.fullmatch(e):
            seen.add(e)
            emails.append(e)

    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().startswith("mailto:"):
            addr = href[len("mailto:"):].split("?")[0]
            _add(addr)

    for match in _EMAIL_RE.findall(soup.get_text(" ")):
        _add(match)

    return emails


def _is_usable(email: str) -> bool:
    local, _, domain = email.partition("@")
    if local.startswith(_BAD_PREFIXES):
        return False
    if any(bad in email for bad in _BAD_DOMAIN_SUBSTR):
        return False
    if email.endswith(_IMAGE_EXT):
        return False
    return True


def score_email(email: str, site_domain: str) -> int:
    """Higher is better. Ranks same-domain, role-based addresses first."""
    local, _, domain = email.partition("@")
    score = 0
    if registrable_domain(domain) == registrable_domain(site_domain):
        score += 100  # on the company's own domain — most trustworthy
    for i, prefix in enumerate(_PREFERRED_PREFIXES):
        if local == prefix or local.startswith(prefix + "."):
            score += (len(_PREFERRED_PREFIXES) - i)
            break
    return score


def best_email(emails: list[str], site_domain: str) -> str | None:
    """Pick the most outreach-worthy usable email, or None."""
    usable = [e for e in emails if _is_usable(e)]
    if not usable:
        return None
    # Stable sort keeps first-seen order among equal scores.
    return max(usable, key=lambda e: score_email(e, site_domain))


# ── network + DB layers ───────────────────────────────────────────────────────

def find_contact_email(base_url: str, session: requests.Session | None = None) -> str | None:
    """Fetch a site's likely contact pages and return its best public email."""
    site_domain = urlparse(base_url).netloc
    getter = session or requests
    found: list[str] = []
    for url in candidate_urls(base_url):
        if not webutil.robots_allowed(url):
            logger.info("robots.txt disallows %s — skipping", url)
            continue
        try:
            resp = getter.get(url, headers=_HEADERS, timeout=15)
            if resp.status_code != 200 or not resp.text:
                continue
        except requests.RequestException:
            continue
        page_emails = extract_emails(resp.text)
        found.extend(page_emails)
        # A same-domain role address is as good as it gets — stop early.
        picked = best_email(found, site_domain)
        if picked and score_email(picked, site_domain) >= 100:
            return picked
    return best_email(found, site_domain)


def run_find_emails() -> int:
    """Fill contact_email for leads that don't have one. Returns count filled."""
    leads = supabase_client.get_leads_without_email()
    if not leads:
        logger.info("No leads missing a contact email")
        return 0

    filled = 0
    for lead in leads:
        base = base_url_for_lead(lead)
        if not base:
            logger.info("Lead %s (%s): no company domain to search — skipping",
                        lead.get("id"), lead.get("company"))
            continue
        try:
            email = find_contact_email(base)
        except Exception as e:
            logger.error("Email search failed for %s: %s", base, e)
            continue
        if not email:
            logger.info("No public email found for %s (%s)", lead.get("company"), base)
            continue
        if supabase_client.is_unsubscribed(email):
            logger.info("Found %s but it's unsubscribed — not attaching", email)
            continue
        supabase_client.update_lead_contact_email(lead["id"], email)
        logger.info("Lead %s (%s): found %s", lead.get("id"), lead.get("company"), email)
        filled += 1

    logger.info("Email finding complete: %d lead(s) filled", filled)
    return filled
