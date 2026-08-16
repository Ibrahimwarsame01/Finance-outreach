-- ============================================================================
-- SECURITY LOCKDOWN — run this in the Supabase SQL Editor.
--
-- The original schema.sql created "USING (true)" policies, which let ANYONE
-- with the public anon key read/write every table (bypassing the login).
-- This script replaces them with least-privilege policies:
--
--   * Logged-in (authenticated) users  -> full read/write (the dashboard).
--   * The public anon key              -> can ONLY add to the suppression
--                                          list (for the unsubscribe link);
--                                          cannot read any of your data.
--   * The Python pipeline              -> uses the service_role key, which
--                                          BYPASSES RLS entirely, so it keeps
--                                          working with no changes.
-- ============================================================================

-- 1. Remove the old wide-open policies
DROP POLICY IF EXISTS "service_role_all" ON senders;
DROP POLICY IF EXISTS "service_role_all" ON leads;
DROP POLICY IF EXISTS "service_role_all" ON sent_log;
DROP POLICY IF EXISTS "service_role_all" ON replies;
DROP POLICY IF EXISTS "service_role_all" ON unsubscribed;

-- 2. Logged-in users get full access to the dashboard tables
CREATE POLICY "authenticated_all" ON senders      FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "authenticated_all" ON leads        FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "authenticated_all" ON sent_log     FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "authenticated_all" ON replies      FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "authenticated_all" ON unsubscribed FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- 3. The public unsubscribe endpoint runs as the anon role. It only needs to
--    add an email to the suppression list (the link's HMAC token is verified
--    in the API route BEFORE this runs). Anon can INSERT/UPDATE here but can
--    NOT read the list, so nobody can harvest your contacts.
CREATE POLICY "anon_add_unsubscribe" ON unsubscribed FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "anon_touch_unsubscribe" ON unsubscribed FOR UPDATE TO anon USING (true) WITH CHECK (true);
