import { redirect } from "next/navigation";
import { createServerSupabaseClient } from "@/lib/supabase-server";
import StatsCards from "@/components/StatsCards";
import SendsChart from "@/components/SendsChart";
import MailboxTable from "@/components/MailboxTable";
import LeadsTable from "@/components/LeadsTable";

async function fetchDashboardData(supabase: Awaited<ReturnType<typeof createServerSupabaseClient>>) {
  const [sentResult, repliesResult, leadsResult] = await Promise.all([
    supabase.from("sent_log").select("sender, sent_at"),
    supabase.from("replies").select("sent_log_id, reply_body, reply_from"),
    supabase
      .from("leads")
      .select(
        "id, company, contact_email, job_title, job_url, email_subject, email_body, sent_log(id, sender, sent_at, replies(reply_body))"
      )
      .order("scraped_at", { ascending: false })
      .limit(50),
  ]);

  const sentRows: { sender: string; sent_at: string }[] = sentResult.data ?? [];
  const replyRows: { sent_log_id: string; reply_body: string; reply_from: string }[] =
    repliesResult.data ?? [];

  // Stats
  const totalSent = sentRows.length;
  const totalReplies = replyRows.length;
  const replyRate = totalSent > 0 ? (totalReplies / totalSent) * 100 : 0;
  const activeMailboxes = new Set(sentRows.map((r) => r.sender)).size;

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

  // Build sent_log_id → sender map for reply attribution
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
  type RawLead = {
    id: string;
    company: string;
    contact_email: string | null;
    job_title: string | null;
    job_url: string | null;
    email_subject: string | null;
    email_body: string | null;
    sent_log:
      | { id: string; sender: string; sent_at: string; replies: { reply_body: string }[] | null }[]
      | null;
  };

  const leads = ((leadsResult.data as RawLead[]) ?? []).map((l) => ({
    id: l.id,
    company: l.company,
    contact_email: l.contact_email,
    job_title: l.job_title,
    job_url: l.job_url,
    email_subject: l.email_subject,
    email_body: l.email_body,
    sent_at: l.sent_log?.[0]?.sent_at ?? null,
    sender: l.sent_log?.[0]?.sender ?? null,
    reply_body: l.sent_log?.[0]?.replies?.[0]?.reply_body ?? null,
  }));

  return { totalSent, totalReplies, replyRate, activeMailboxes, sendsOverTime, mailboxRows, leads };
}

export default async function DashboardPage() {
  const supabase = await createServerSupabaseClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  const { totalSent, totalReplies, replyRate, activeMailboxes, sendsOverTime, mailboxRows, leads } =
    await fetchDashboardData(supabase);

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Outreach Dashboard</h1>
        <form action="/api/logout" method="POST">
          <button className="text-sm text-gray-500 hover:text-gray-700">Sign out</button>
        </form>
      </div>

      <StatsCards
        totalSent={totalSent}
        totalReplies={totalReplies}
        replyRate={replyRate}
        activeMailboxes={activeMailboxes}
      />

      <SendsChart data={sendsOverTime} />

      <MailboxTable rows={mailboxRows} />

      <LeadsTable leads={leads} />
    </main>
  );
}
