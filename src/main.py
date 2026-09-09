import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_pipeline() -> None:
    from src.scrape import run_scrape
    from src.personalize import personalize_unsent_leads
    from src.send_gmail import run_sends
    from src.followup import run_followups
    from src.warmup import run_warmup
    from src.check_replies import run_check_replies

    logger.info("=== Pipeline start ===")

    new_leads = run_scrape()
    logger.info("Scraped %d new leads", new_leads)

    drafted = personalize_unsent_leads()
    logger.info("Drafted %d emails", drafted)

    # Check replies first so follow-ups never nudge someone who already answered.
    replies = run_check_replies()
    logger.info("Logged %d new replies", replies)

    sent = run_sends()
    logger.info("Sent %d emails", sent)

    # Follow-ups run after the initial send so both share the same daily cap view.
    followups = run_followups()
    logger.info("Sent %d follow-ups", followups)

    # Warm-up traffic between our own mailboxes (reputation building only).
    warmup_actions = run_warmup()
    logger.info("Warm-up actions: %d", warmup_actions)

    logger.info("=== Pipeline complete ===")


if __name__ == "__main__":
    run_pipeline()
