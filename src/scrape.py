import os
import time
import logging
import requests
import yaml
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
from src import supabase_client

logger = logging.getLogger(__name__)


def load_config() -> dict:
    with open("config.yaml") as f:
        return yaml.safe_load(f)


def _keywords(config: dict) -> list[str]:
    return [k.lower() for k in config.get("role_keywords", [])]


def _matches_keywords(text: str, keywords: list[str]) -> bool:
    text = text.lower()
    return any(kw in text for kw in keywords)


def _robots_allowed(url: str) -> bool:
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch("*", url)
    except Exception:
        return True  # assume allowed if robots.txt unreachable


# ── RemoteOK ──────────────────────────────────────────────────────────────────

def scrape_remoteok(keywords: list[str]) -> list[dict]:
    url = "https://remoteok.com/api"
    headers = {"User-Agent": "finance-outreach-bot/1.0 (job board research)"}
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("RemoteOK fetch failed: %s", e)
        return []

    jobs = resp.json()
    leads = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        title = job.get("position", "")
        tags = " ".join(job.get("tags", []))
        description = job.get("description", "")
        if not _matches_keywords(f"{title} {tags} {description}", keywords):
            continue

        company = job.get("company", "")
        job_url = job.get("url", "")
        contact_email = job.get("email")  # sometimes present

        if not company or not job_url:
            continue

        leads.append({
            "company": company,
            "contact_email": contact_email,
            "job_title": title,
            "job_url": job_url,
            "source": "remoteok",
        })

    logger.info("RemoteOK: found %d matching leads", len(leads))
    return leads


# ── Indeed (via MCP connector — stub for pipeline) ────────────────────────────

def scrape_indeed(keywords: list[str], countries: list[str]) -> list[dict]:
    # The Indeed MCP connector is available for interactive Claude use.
    # For the pipeline, use the Indeed Publisher API:
    # https://ads.indeed.com/jobroll/xmlfeed
    # Set INDEED_PUBLISHER_ID env var to enable.
    #
    # `countries` is a list of ISO country codes (e.g. ["US", "CA", "GB"])
    # from config.yaml -> sources.indeed_countries. Indeed's API is
    # per-country, so worldwide coverage = searching each country in turn.
    publisher_id = os.getenv("INDEED_PUBLISHER_ID")
    if not publisher_id:
        logger.info("INDEED_PUBLISHER_ID not set — skipping Indeed")
        return []

    if not countries:
        logger.info("No indeed_countries configured — skipping Indeed")
        return []

    leads = []
    for kw in keywords[:3]:  # limit API calls per country
        for co in countries:
            url = (
                f"https://api.indeed.com/ads/apisearch"
                f"?publisher={publisher_id}&q={requests.utils.quote(kw)}"
                f"&co={co}&limit=25&format=json&v=2"
            )
            try:
                resp = requests.get(url, timeout=20)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error("Indeed API error for '%s' in %s: %s", kw, co, e)
                continue

            for result in data.get("results", []):
                leads.append({
                    "company": result.get("company", ""),
                    "contact_email": None,
                    "job_title": result.get("jobtitle", ""),
                    "job_url": result.get("url", ""),
                    "source": "indeed",
                })
            time.sleep(1)

    logger.info("Indeed: found %d leads across %d countries", len(leads), len(countries))
    return leads


# ── Career pages ──────────────────────────────────────────────────────────────

def scrape_career_page(entry: dict, keywords: list[str]) -> list[dict]:
    url = entry["url"]
    company = entry["company"]

    if not _robots_allowed(url):
        logger.info("robots.txt disallows scraping %s — skipping", url)
        return []

    headers = {"User-Agent": "finance-outreach-bot/1.0 (job board research)"}
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("Career page fetch failed for %s: %s", url, e)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    leads = []

    # Generic heuristic: look for anchor tags whose text matches keywords
    for tag in soup.find_all("a", href=True):
        text = tag.get_text(strip=True)
        href = tag["href"]
        if not _matches_keywords(text, keywords):
            continue

        job_url = href if href.startswith("http") else f"{urlparse(url).scheme}://{urlparse(url).netloc}{href}"
        leads.append({
            "company": company,
            "contact_email": None,
            "job_title": text,
            "job_url": job_url,
            "source": "career_page",
        })

    logger.info("Career page %s: found %d matching leads", url, len(leads))
    return leads


# ── Orchestrator ──────────────────────────────────────────────────────────────

def run_scrape() -> int:
    config = load_config()
    keywords = _keywords(config)
    sources = config.get("sources", {})

    all_leads: list[dict] = []

    if sources.get("remoteok", True):
        all_leads.extend(scrape_remoteok(keywords))

    if sources.get("indeed", False):
        countries = sources.get("indeed_countries", [])
        all_leads.extend(scrape_indeed(keywords, countries))

    for page in sources.get("career_pages", []):
        all_leads.extend(scrape_career_page(page, keywords))

    saved = 0
    for lead in all_leads:
        if not lead.get("job_url"):
            continue
        result = supabase_client.insert_lead(lead)
        if result:
            saved += 1

    logger.info("Scrape complete: %d new leads saved", saved)
    return saved
