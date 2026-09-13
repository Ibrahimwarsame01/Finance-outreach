-- ============================================================================
-- Store the full body of each sent email so the dashboard can show complete
-- outreach threads (initial + every follow-up), not just the subject.
-- Run this ONCE in the Supabase SQL Editor. Safe to run repeatedly.
--
-- Existing rows keep body = NULL (their text wasn't captured at send time);
-- for step-0 sends the dashboard falls back to leads.email_body, and all
-- future sends/follow-ups store their body here.
-- ============================================================================

ALTER TABLE sent_log ADD COLUMN IF NOT EXISTS body TEXT;
