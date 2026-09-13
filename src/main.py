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
    from src.find_email import run_find_emails
    from src.personalize import personalize_unsent_leads
    from src.send_gmail import run_sends
    from src.followup import run_followups
    from src.warmup import run_warmup
    from src.check_replies import run_check_replies

    logger.info("=== Pipeline start ===")

    # Each stage runs independently. A failure in one is logged (with traceback)
    # and the pipeline moves on to the rest, so a transient error in an early
    # stage (a scrape source going down, an IMAP hiccup) can't stop warm-up /
    # reply-checking from running. This runs on a ~20-min cron with all state in
    # Supabase, so anything skipped this run is simply retried next run.
    #
    # Order still matters where it can: replies are checked before follow-ups so
    # we never nudge someone who already answered; follow-ups run after the
    # initial send so both share the same daily-cap view. Because every stage
    # reads its inputs from Supabase (not from the previous stage's return
    # value), running a later stage after an earlier one failed is safe — it
    # just operates on whatever is currently in the DB.
    stages = (
        ("scrape", run_scrape, "Scraped %s new leads"),
        ("find_emails", run_find_emails, "Found contact emails for %s leads"),
        ("personalize", personalize_unsent_leads, "Drafted %s emails"),
        ("check_replies", run_check_replies, "Logged %s new replies"),
        ("sends", run_sends, "Sent %s emails"),
        ("followups", run_followups, "Sent %s follow-ups"),
        ("warmup", run_warmup, "Warm-up actions: %s"),
    )

    failed = []
    for name, fn, done_msg in stages:
        try:
            result = fn()
            logger.info(done_msg, result)
        except Exception:
            logger.exception("Stage %r failed — continuing with remaining stages", name)
            failed.append(name)

    if failed:
        # Still surface the failure so GitHub Actions marks the run red and
        # notifies — but only after every stage got its chance to run.
        logger.error("=== Pipeline finished with %d failed stage(s): %s ===",
                     len(failed), ", ".join(failed))
        raise SystemExit(1)

    logger.info("=== Pipeline complete ===")


if __name__ == "__main__":
    run_pipeline()
