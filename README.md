# finance-outreach

An automated pipeline that finds companies hiring for a finance role, drafts a
personalized cold email pitching a fractional-finance service, sends it via a
rotating pool of warmed-up Gmail mailboxes, sends threaded follow-ups to
non-repliers, and tracks everything on a password-protected web dashboard.

Runs on a schedule via GitHub Actions (every 15–30 min). Built to run on free
or low-cost infrastructure — Gemini's free tier for drafting, Supabase's free
tier for data, Vercel's free tier for the dashboard.

## How it works

`src/main.py` → `run_pipeline()` runs these in order each pass:

```
scrape ──▶ find_email ──▶ personalize ──▶ check_replies ──▶ send ──▶ follow-ups ──▶ warm-up
 find      fill contact    draft email     log new replies   rotate    threaded      inter-mailbox
 leads     email from       per lead        (before sends,    senders,  nudges to     reputation
           company site     via Gemini      so we never       caps +    non-repliers  traffic
                                            nudge a replier)   suppress
```

- **Sourcing** (`scrape.py`) — RemoteOK's public API, the Indeed API connector
  (when a publisher ID is set), and allowed company career pages (robots.txt is
  honored). LinkedIn/Indeed are never scraped directly.
  > **Note:** fully-automated sourcing is low-yield for this niche — see
  > [Sourcing reality](#sourcing-reality) below. In practice lead sourcing is
  > semi-automated (curated into Supabase), and the cron handles everything else.
- **Email finding** (`find_email.py`) — job boards rarely give a contact email,
  and a lead with no `contact_email` is never sent. This step scrapes the
  company's own site (contact/about/careers), scores candidates to prefer a
  role-based address on the company's own domain, and honors robots.txt + the
  suppression list.
- **Personalization** (`personalize.py`) — Google Gemini (free tier) drafts a
  short, tailored email per lead. The Gemini call is isolated behind
  `draft_email(lead)` so swapping providers later is a one-function change.
- **Sending** (`send_gmail.py` + `mailer.py`) — round-robins across multiple
  Gmail mailboxes on a dedicated outreach domain. Each mailbox has its own daily
  cap that ramps up over weeks as it warms up. The signature + CASL footer are
  attached at send time using the sending mailbox's persona, so the "From" name
  always matches the signature. A shared suppression list is checked before
  every send, and a send-time preflight refuses to send while CASL-required
  config is still unset.
- **Follow-ups** (`followup.py`) — gentle, threaded Gemini-drafted nudges to
  leads that haven't replied, reusing the original mailbox and counting against
  its daily cap.
- **Warm-up** (`warmup.py`) — your own mailboxes email each other on a small
  daily schedule (and reply, and rescue from spam) to build sending reputation
  before real cold volume. Never touches real leads.
- **Reply checking** (`check_replies.py`) — polls mailboxes over IMAP and writes
  new replies to Supabase.
- **Tracking** (`dashboard/`) — a Next.js app on Vercel showing sent/reply
  counts, reply rate, a sends-over-time chart, and a per-mailbox breakdown (how
  you spot a flagged or underperforming mailbox), all behind a single admin
  login. Includes the public `/api/unsubscribe` endpoint.

## Repo structure

```
finance-outreach/
├── CLAUDE.md                  # build brief / session notes for Claude Code
├── config.yaml                # senders, personas, role keywords, sources, caps, warm-up, follow-ups
├── requirements.txt
├── conftest.py
├── src/
│   ├── main.py                # run_pipeline() — the only entrypoint the cron calls
│   ├── scrape.py              # RemoteOK + Indeed API + career pages
│   ├── find_email.py          # find a public contact email from the company site
│   ├── personalize.py         # Gemini drafts + signature/CASL footer + send-readiness guard
│   ├── send_gmail.py          # sender rotation, warm-up ramp, suppression
│   ├── followup.py            # threaded follow-up sequences
│   ├── warmup.py              # inter-mailbox warm-up traffic
│   ├── check_replies.py       # IMAP reply polling → Supabase
│   ├── mailer.py              # shared: message build (threading) + SMTP + cap ramp
│   ├── webutil.py             # shared HTTP + a correct robots.txt check
│   └── supabase_client.py     # Supabase reads/writes
├── scripts/
│   └── check_mailboxes.py     # verify each mailbox's SMTP+IMAP login (sends nothing)
├── supabase/
│   ├── schema.sql             # tables: leads, sent_log, replies, unsubscribed, senders, warmup_log
│   ├── upgrade_warmup_followups.sql
│   ├── enable_realtime.sql
│   └── lockdown_rls.sql
├── tests/                     # pytest — pure logic, no network
├── .github/workflows/
│   └── pipeline.yml           # cron: python src/main.py
└── dashboard/                 # Next.js app, deployed on Vercel
    ├── app/
    │   ├── login/page.tsx
    │   ├── page.tsx
    │   └── api/unsubscribe/route.ts
    └── lib/supabase.ts
```

## Setup

1. **Clone + install**
   ```bash
   git clone https://github.com/Ibrahimwarsame01/Finance-outreach.git
   cd Finance-outreach
   pip install -r requirements.txt
   ```

2. **Supabase** — create a project, run `supabase/schema.sql` (then
   `upgrade_warmup_followups.sql`, `enable_realtime.sql`, `lockdown_rls.sql`),
   enable Auth, and create the single admin user manually.

3. **Sending domain** — a Google Workspace domain kept separate from your main
   brand. Configure **SPF, DKIM, and DMARC** before sending anything. Create the
   sender mailboxes and, for each, enable 2-Step Verification and generate an
   **App Password** (16 lowercase letters, not the account password).

4. **Gemini API key** — free at [Google AI Studio](https://aistudio.google.com/).

5. **Local `.env`** (gitignored) — see `.env.example`:
   - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
   - `GEMINI_API_KEY`
   - `GMAIL_APP_PASSWORD_1`, `_2`, `_3` (one per mailbox)
   - `UNSUBSCRIBE_SECRET` (also set in Vercel)

6. **Fill `config.yaml`** — sender mailboxes (email, `name`/`title` persona,
   `warmup_start`, `max_daily_cap`, `app_password_env`), role keywords, sources,
   and the `outreach` block. **`business_address` and `unsubscribe_base_url`
   must be real** — the pipeline refuses to send while they're placeholders.

7. **Verify mailboxes** before trusting the cron:
   ```bash
   python scripts/check_mailboxes.py   # SMTP + IMAP login for each mailbox; sends nothing
   ```

8. **GitHub Actions secrets** (Settings → Secrets and variables → Actions):
   `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`,
   `UNSUBSCRIBE_SECRET`, `GMAIL_APP_PASSWORD_1/2/3`,
   `INDEED_PUBLISHER_ID` (optional).

9. **Run the full pipeline locally** to sanity-check before the cron:
   ```bash
   python src/main.py
   ```

10. **Dashboard** — deploy `dashboard/` to Vercel pointed at the same Supabase
    project (`NEXT_PUBLIC_SUPABASE_URL` / `SUPABASE_ANON_KEY` as Vercel env vars).

11. **Enable the workflow** — `.github/workflows/pipeline.yml` runs
    `python src/main.py` on a schedule once you're confident.

## Testing

```bash
python -m pytest -q
```

Tests are pure logic (cap ramp, follow-up scheduling, persona signatures,
email scoring, robots parsing, send-readiness) with no network or live DB.

## Compliance

This project sends unsolicited commercial email and must stay CASL compliant:
- Every email includes a working unsubscribe link and the sender's business
  address. A send-time preflight blocks sends until both are configured.
- Unsubscribes are honored immediately and permanently via the Supabase
  `unsubscribed` table (a serverless `/api/unsubscribe` endpoint inserts on
  click), checked before every send across **every** mailbox.
- Only sent/replied are tracked — no tracking pixels or open tracking.

## Sourcing reality

Fully-unattended "source finance-hiring companies → auto-find email →
cold-pitch" is low-yield for this niche, confirmed by testing the finder
against many real trucking/moving companies:
- The ideal customers (small/mid companies) rarely expose a plaintext email —
  they use contact forms, JS-obfuscated addresses, or block bots.
- The companies that *do* expose an email tend to be large carriers with
  generic `customerservice@`/`safety@` inboxes — wrong contact, wrong fit.
- Modern career pages render job listings via JavaScript/ATS widgets, so static
  scraping finds no postings.

So sourcing + email-finding is best done **semi-automated** (interactive
research + curation into Supabase), while the cron reliably handles warm-up,
reply checking, follow-ups, personalization, sending, and the dashboard for any
lead that has an email.

## Status

Pipeline logic + dashboard are built and tested. Before real outreach:
fill the CASL config, add the GitHub secrets, warm up the mailboxes for 1–2
weeks, and curate real leads. See `CLAUDE.md` for detailed session notes.
