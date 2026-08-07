-- Run this in the Supabase SQL editor to set up all tables

CREATE TABLE IF NOT EXISTS senders (
    email TEXT PRIMARY KEY,
    warmup_start DATE NOT NULL,
    max_daily_cap INTEGER NOT NULL DEFAULT 100
);

CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company TEXT NOT NULL,
    contact_email TEXT,
    job_title TEXT,
    job_url TEXT UNIQUE,
    source TEXT,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    email_subject TEXT,
    email_body TEXT
);

CREATE TABLE IF NOT EXISTS sent_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID REFERENCES leads(id),
    sender TEXT NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    subject TEXT,
    message_id TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sent_log_id UUID REFERENCES sent_log(id),
    received_at TIMESTAMPTZ DEFAULT NOW(),
    reply_body TEXT,
    reply_from TEXT
);

CREATE TABLE IF NOT EXISTS unsubscribed (
    email TEXT PRIMARY KEY,
    unsubscribed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security on all tables
ALTER TABLE senders ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE sent_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE replies ENABLE ROW LEVEL SECURITY;
ALTER TABLE unsubscribed ENABLE ROW LEVEL SECURITY;

-- Allow service role (used by pipeline) full access
CREATE POLICY "service_role_all" ON senders FOR ALL USING (true);
CREATE POLICY "service_role_all" ON leads FOR ALL USING (true);
CREATE POLICY "service_role_all" ON sent_log FOR ALL USING (true);
CREATE POLICY "service_role_all" ON replies FOR ALL USING (true);
CREATE POLICY "service_role_all" ON unsubscribed FOR ALL USING (true);
