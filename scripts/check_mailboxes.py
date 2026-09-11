"""One-off connectivity check: log into each configured mailbox over SMTP + IMAP.

Sends NOTHING. Just verifies that the App Password in .env actually
authenticates for each sender in config.yaml, so a bad/missing credential is
caught before the pipeline (or the GitHub Actions cron) ever relies on it.

Run:  python scripts/check_mailboxes.py
"""
import imaplib
import smtplib
import sys

from dotenv import load_dotenv

load_dotenv()

# Import after load_dotenv so mailer sees the env.
sys.path.insert(0, ".")
from src import mailer  # noqa: E402


def check(sender: dict) -> bool:
    email = sender.get("email", "?")
    env_var = sender.get("app_password_env", "?")
    pw = mailer.get_app_password(sender)
    if not pw:
        print(f"  [{email}] NO PASSWORD — {env_var} is unset or empty")
        return False

    ok = True
    # SMTP (sending path)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as s:
            s.login(email, pw)
        print(f"  [{email}] SMTP  OK")
    except Exception as e:
        print(f"  [{email}] SMTP  FAIL — {e}")
        ok = False
    # IMAP (reply-checking + warm-up path)
    try:
        m = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        m.login(email, pw)
        m.logout()
        print(f"  [{email}] IMAP  OK")
    except Exception as e:
        print(f"  [{email}] IMAP  FAIL — {e}")
        ok = False
    return ok


def main() -> int:
    senders = mailer.load_senders()
    if not senders:
        print("No senders in config.yaml")
        return 1
    print(f"Checking {len(senders)} mailbox(es)...\n")
    results = [check(s) for s in senders]
    print()
    good = sum(results)
    print(f"{good}/{len(results)} mailboxes authenticated.")
    return 0 if good == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
