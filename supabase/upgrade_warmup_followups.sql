-- ============================================================================
-- UPGRADE: follow-up sequences + automated warm-up.
-- Run this ONCE in the Supabase SQL Editor on an EXISTING project.
--
-- schema.sql uses CREATE TABLE IF NOT EXISTS, so it will NOT add new columns
-- to tables that already exist. This migration is safe to run repeatedly:
-- every statement is guarded with IF NOT EXISTS.
-- ============================================================================

-- 1. Follow-up tracking on sent_log ------------------------------------------
--    step 0 = initial outreach; 1, 2, … = follow-up sequence steps.
ALTER TABLE sent_log ADD COLUMN IF NOT EXISTS step INTEGER NOT NULL DEFAULT 0;
--    Message-ID the email was sent in reply to (keeps follow-ups threaded).
ALTER TABLE sent_log ADD COLUMN IF NOT EXISTS in_reply_to TEXT;

-- 2. Warm-up traffic log between your OWN mailboxes --------------------------
CREATE TABLE IF NOT EXISTS warmup_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sender TEXT NOT NULL,
    recipient TEXT NOT NULL,
    message_id TEXT UNIQUE,
    kind TEXT NOT NULL DEFAULT 'sent',   -- 'sent' | 'reply'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE warmup_log ENABLE ROW LEVEL SECURITY;

-- Logged-in dashboard users can read warm-up stats; the pipeline uses the
-- service_role key which bypasses RLS.
DROP POLICY IF EXISTS "authenticated_all" ON warmup_log;
CREATE POLICY "authenticated_all" ON warmup_log FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- 3. (Optional) push warm-up rows to the live dashboard over Realtime.
--    Wrapped so re-running doesn't error if it's already in the publication.
DO $$
BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE warmup_log;
EXCEPTION
    WHEN duplicate_object THEN NULL;  -- already added
    WHEN undefined_object THEN NULL;  -- publication doesn't exist yet
END $$;
