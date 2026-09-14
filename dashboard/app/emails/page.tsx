import { redirect } from "next/navigation";
import { createServerSupabaseClient } from "@/lib/supabase-server";
import { resolveRole } from "@/lib/role";
import Sidebar from "@/components/Sidebar";
import RealtimeRefresh from "@/components/RealtimeRefresh";
import EmailThreads, {
  type Thread,
  type ThreadMessage,
} from "@/components/EmailThreads";

type RawReply = {
  id: string;
  reply_from: string | null;
  reply_body: string | null;
  received_at: string | null;
};
type RawSend = {
  id: string;
  sender: string;
  sent_at: string | null;
  subject: string | null;
  body: string | null;
  step: number | null;
  message_id: string | null;
  replies: RawReply[] | null;
};
type RawLead = {
  id: string;
  company: string;
  contact_email: string | null;
  job_title: string | null;
  job_url: string | null;
  email_subject: string | null;
  email_body: string | null;
  scraped_at: string | null;
  sent_log: RawSend[] | null;
};

function buildThreads(leads: RawLead[], mailbox: string | null): Thread[] {
  const threads: Thread[] = [];
  for (const l of leads) {
    // Non-admins only see their own mailbox's messages on each lead.
    const sends = (l.sent_log ?? []).filter((s) => !mailbox || s.sender === mailbox);
    // For a non-admin, skip leads their mailbox never touched.
    if (mailbox && sends.length === 0) continue;
    const messages: ThreadMessage[] = [];

    for (const s of sends) {
      const step = s.step ?? 0;
      messages.push({
        kind: "sent",
        step,
        sender: s.sender,
        at: s.sent_at,
        subject: s.subject,
        // Older step-0 sends predate body logging; fall back to the lead draft.
        body: s.body ?? (step === 0 ? l.email_body : null),
      });
      for (const r of s.replies ?? []) {
        messages.push({
          kind: "reply",
          from: r.reply_from,
          at: r.received_at,
          body: r.reply_body,
        });
      }
    }

    // Lead drafted but not yet sent — surface the draft so it's visible.
    if (sends.length === 0 && l.email_body) {
      messages.push({
        kind: "sent",
        step: 0,
        sender: "",
        at: null,
        subject: l.email_subject,
        body: l.email_body,
      });
    }

    // Chronological order; drafts (null timestamp) sort to the top.
    messages.sort((a, b) => (a.at ?? "").localeCompare(b.at ?? ""));

    const senders = Array.from(
      new Set(sends.map((s) => s.sender).filter(Boolean))
    );
    const hasReply = sends.some((s) => (s.replies ?? []).length > 0);
    const hasFollowup = sends.some((s) => (s.step ?? 0) > 0);
    const hasSend = sends.length > 0;

    const status: Thread["status"] = hasReply
      ? "replied"
      : hasFollowup
        ? "followed_up"
        : hasSend
          ? "sent"
          : l.email_body
            ? "drafted"
            : "new";

    const times = messages
      .map((m) => m.at)
      .filter((t): t is string => !!t)
      .sort();
    const lastActivity = times[times.length - 1] ?? l.scraped_at;

    threads.push({
      id: l.id,
      company: l.company,
      contact_email: l.contact_email,
      job_title: l.job_title,
      job_url: l.job_url,
      senders,
      lastActivity,
      status,
      messages,
    });
  }

  // Most recently active threads first.
  threads.sort((a, b) => (b.lastActivity ?? "").localeCompare(a.lastActivity ?? ""));
  return threads;
}

export default async function EmailsPage() {
  const supabase = await createServerSupabaseClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  const role = resolveRole(user.email);

  const { data } = await supabase
    .from("leads")
    .select(
      "id, company, contact_email, job_title, job_url, email_subject, email_body, scraped_at, sent_log(id, sender, sent_at, subject, body, step, message_id, replies(id, reply_from, reply_body, received_at))"
    )
    .order("scraped_at", { ascending: false });

  const threads = buildThreads((data as RawLead[]) ?? [], role.mailbox);

  return (
    <div className="flex min-h-screen">
      <RealtimeRefresh />
      <Sidebar isAdmin={role.isAdmin} />

      <main className="min-w-0 flex-1">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-white/5 bg-ink-950/80 px-6 py-4 backdrop-blur">
          <div>
            <h1 className="text-lg font-semibold text-white">Inbox</h1>
            <p className="text-xs text-slate-500">
              {role.isAdmin
                ? "Every mailbox · sent, received & replies in one place"
                : `${role.email} · your sent, received & replies`}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden rounded-full border border-white/10 px-2.5 py-1 text-[11px] text-slate-400 sm:inline">
              {role.isAdmin ? "Admin" : "Mailbox"}
            </span>
            <form action="/api/logout" method="POST">
              <button className="rounded-lg border border-white/10 px-3 py-1.5 text-sm text-slate-400 transition-colors hover:bg-white/5 hover:text-white">
                Sign out
              </button>
            </form>
          </div>
        </header>

        <div className="mx-auto max-w-7xl px-6 py-8">
          <EmailThreads threads={threads} isAdmin={role.isAdmin} />
        </div>
      </main>
    </div>
  );
}
