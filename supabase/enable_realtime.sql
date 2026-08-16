-- ============================================================================
-- Enable Supabase Realtime so the dashboard updates live (no manual refresh).
-- Run this once in the Supabase SQL Editor.
--
-- This adds the dashboard's tables to the realtime publication, so INSERTs /
-- UPDATEs are pushed to the logged-in dashboard over a websocket. Row Level
-- Security still applies, so only authenticated users receive the changes.
-- ============================================================================

ALTER PUBLICATION supabase_realtime ADD TABLE leads;
ALTER PUBLICATION supabase_realtime ADD TABLE sent_log;
ALTER PUBLICATION supabase_realtime ADD TABLE replies;
