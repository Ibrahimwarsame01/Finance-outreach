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
    from src.check_replies import run_check_replies

    logger.info("=== Pipeline start ===")

    new_leads = run_scrape()
    logger.info("Scraped %d new leads", new_leads)

    drafted = personalize_unsent_leads()
    logger.info("Drafted %d emails", drafted)

    sent = run_sends()
    logger.info("Sent %d emails", sent)

    replies = run_check_replies()
    logger.info("Logged %d new replies", replies)

    logger.info("=== Pipeline complete ===")


if __name__ == "__main__":
    run_pipeline()
