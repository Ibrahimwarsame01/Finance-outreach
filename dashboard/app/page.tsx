import { redirect } from "next/navigation";
import { createServerSupabaseClient } from "@/lib/supabase-server";
import Sidebar from "@/components/Sidebar";
import StatsCards from "@/components/StatsCards";
import SendsChart from "@/components/SendsChart";
import MailboxTable from "@/components/MailboxTable";
import LeadsTable from "@/components/LeadsTable";
import RealtimeRefresh from "@/components/RealtimeRefresh";

async function fetchDashboardData(
  supabase: Awaited<ReturnType<typeof createServerSupabaseClient>>
) {
  const sevenDaysAgo = new Date();
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

  const [sentResult, repliesResult, leadsResult, warmupResult] = await Promise.all([
    supabase.from("sent_log").select("sender, sent_at, step"),
    supabase.from("replies").select("sent_log_id, reply_body, reply_from"),
    supabase
      .from("leads")
      .select(
        "id, company, contact_email, job_title, job_url, email_subject, email_body, sent_log(id, sender, sent_at, step, replies(reply_body))"
      )
      .order("scraped_at", { ascending: false })
      .limit(50),
    // Resilient: if warmup_log doesn't exist yet, count comes back null → 0.
    supabase
      .from("warmup_log")
      .select("id", { count: "exact", head: true })
      .gte("created_at", sevenDaysAgo.toISOString()),
  ]);

  const sentRows: { sender: string; sent_at: string; step: number | null }[] =
    sentResult.data ?? [];
  const replyRows: { sent_log_id: string; reply_body: string; reply_from: string }[] =
    repliesResult.data ?? [];

  // Stats
  const totalSent = sentRows.length;
  const totalReplies = replyRows.length;
  const totalFollowups = sentRows.filter((r) => (r.step ?? 0) > 0).length;
  const replyRate = totalSent > 0 ? (totalReplies / totalSent) * 100 : 0;
  const activeMailboxes = new Set(sentRows.map((r) => r.sender)).size;
  const warmupLast7 = warmupResult.count ?? 0;

  // Sends over time (last 30 days)
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - 30);
  const countByDate: Record<string, number> = {};
  for (const row of sentRows) {
    const d = row.sent_at.slice(0, 10);
    if (new Date(d) >= cutoff) {
      countByDate[d] = (countByDate[d] ?? 0) + 1;
    }
  }
  const sendsOverTime = Object.entries(countByDate)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, count]) => ({ date, count }));

  // Per-mailbox breakdown
  const mailboxSent: Record<string, number> = {};
  for (const row of sentRows) {
    mailboxSent[row.sender] = (mailboxSent[row.sender] ?? 0) + 1;
  }

  const allSentLog = await supabase.from("sent_log").select("id, sender");
  const sentLogMap: Record<string, string> = {};
  for (const row of allSentLog.data ?? []) {
    sentLogMap[row.id] = row.sender;
  }

  const mailboxReplied: Record<string, number> = {};
  for (const reply of replyRows) {
    const sender = sentLogMap[reply.sent_log_id];
    if (sender) {
      mailboxReplied[sender] = (mailboxReplied[sender] ?? 0) + 1;
    }
  }

  const mailboxRows = Object.entries(mailboxSent).map(([sender, sent]) => {
    const replied = mailboxReplied[sender] ?? 0;
    return { sender, sent, replied, replyRate: sent > 0 ? (replied / sent) * 100 : 0 };
  });

  // Recent leads — flatten nested joins
  type RawSend = {
    id: string;
    sender: string;
    sent_at: string;
    step: number | null;
    replies: { reply_body: string }[] | null;
  };
  type RawLead = {
    id: string;
    company: string;
    contact_email: string | null;
    job_title: string | null;
    job_url: string | null;
    email_subject: string | null;
    email_body: string | null;
    sent_log: RawSend[] | null;
  };

  const leads = ((leadsResult.data as RawLead[]) ?? []).map((l) => {
    const sends = l.sent_log ?? [];
    const initial = sends.find((s) => (s.step ?? 0) === 0) ?? sends[0];
    const replyBody =
      sends.map((s) => s.replies?.[0]?.reply_body).find((b) => b) ?? null;
    return {
      id: l.id,
      company: l.company,
      contact_email: l.contact_email,
      job_title: l.job_title,
      job_url: l.job_url,
      email_subject: l.email_subject,
      email_body: l.email_body,
      sent_at: initial?.sent_at ?? null,
      sender: initial?.sender ?? null,
      reply_body: replyBody,
      followups: sends.filter((s) => (s.step ?? 0) > 0).length,
    };
  });

  return {
    totalSent,
    totalReplies,
    totalFollowups,
    replyRate,
    activeMailboxes,
    warmupLast7,
    sendsOverTime,
    mailboxRows,
    leads,
  };
}

export default async function DashboardPage() {
  const supabase = await createServerSupabaseClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  const data = await fetchDashboardData(supabase);

  const statItems = [
    { label: "Emails Sent", value: data.totalSent.toLocaleString(), accent: "brand" as const },
    { label: "Replies", value: data.totalReplies.toLocaleString(), accent: "emerald" as const },
    { label: "Reply Rate", value: `${data.replyRate.toFixed(1)}%`, accent: "emerald" as const },
    { label: "Follow-ups", value: data.totalFollowups.toLocaleString(), accent: "accent" as const },
    {
      label: "Warm-ups 7d",
      value: data.warmupLast7.toLocaleString(),
      hint: "mailbox reputation",
      accent: "accent" as const,
    },
    { label: "Active Mailboxes", value: data.activeMailboxes, accent: "slate" as const },
  ];

  return (
    <div className="flex min-h-screen">
      <RealtimeRefresh />
      <Sidebar />

      <main className="min-w-0 flex-1">
        {/* Top bar */}
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-white/5 bg-ink-950/80 px-6 py-4 backdrop-blur">
          <div>
            <h1 className="text-lg font-semibold text-white">Outreach Overview</h1>
            <p className="text-xs text-slate-500">Sends, follow-ups, warm-up & mailbox health</p>
          </div>
          <form action="/api/logout" method="POST">
            <button className="rounded-lg border border-white/10 px-3 py-1.5 text-sm text-slate-400 transition-colors hover:bg-white/5 hover:text-white">
              Sign out
            </button>
          </form>
        </header>

        <div className="mx-auto max-w-7xl space-y-6 px-6 py-8">
          <section id="overview">
            <StatsCards items={statItems} />
          </section>

          <section id="performance">
            <SendsChart data={data.sendsOverTime} />
          </section>

          <section id="mailboxes">
            <MailboxTable rows={data.mailboxRows} />
          </section>

          <section id="leads">
            <LeadsTable leads={data.leads} />
          </section>
        </div>
      </main>
    </div>
  );
}
