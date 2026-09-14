"use client";

import { useMemo, useState } from "react";

export type ThreadMessage =
  | {
      kind: "sent";
      step: number;
      sender: string;
      at: string | null;
      subject: string | null;
      body: string | null;
    }
  | {
      kind: "reply";
      from: string | null;
      at: string | null;
      body: string | null;
    };

export interface Thread {
  id: string;
  company: string;
  contact_email: string | null;
  job_title: string | null;
  job_url: string | null;
  senders: string[];
  lastActivity: string | null;
  status: "replied" | "followed_up" | "sent" | "drafted" | "new";
  messages: ThreadMessage[];
}

const STATUS_STYLES: Record<Thread["status"], { label: string; cls: string; dot: string }> = {
  replied: { label: "Replied", cls: "bg-emerald-400/15 text-emerald-300", dot: "bg-emerald-400" },
  followed_up: { label: "Followed up", cls: "bg-accent-400/15 text-accent-400", dot: "bg-accent-400" },
  sent: { label: "Sent", cls: "bg-brand-400/15 text-brand-400", dot: "bg-brand-400" },
  drafted: { label: "Drafted", cls: "bg-amber-400/15 text-amber-300", dot: "bg-amber-400" },
  new: { label: "New", cls: "bg-white/5 text-slate-400", dot: "bg-slate-500" },
};

function fmt(ts: string | null): string {
  if (!ts) return "—";
  const d = new Date(ts);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function fmtShort(ts: string | null): string {
  if (!ts) return "";
  const d = new Date(ts);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function stepLabel(step: number): string {
  return step === 0 ? "Initial outreach" : `Follow-up #${step}`;
}

function snippet(t: Thread): string {
  const last = t.messages[t.messages.length - 1];
  const body = (last?.body ?? "").replace(/\s+/g, " ").trim();
  return body || "No content yet";
}

function MessageBubble({ msg }: { msg: ThreadMessage }) {
  if (msg.kind === "reply") {
    return (
      <div className="flex justify-start">
        <div className="max-w-[80%] rounded-2xl rounded-tl-sm border border-emerald-400/20 bg-emerald-400/5 p-3">
          <div className="mb-1 flex flex-wrap items-center gap-2 text-[11px]">
            <span className="font-semibold text-emerald-300">Reply</span>
            <span className="text-slate-500">{msg.from ?? "unknown"}</span>
            <span className="text-slate-600">· {fmt(msg.at)}</span>
          </div>
          <pre className="whitespace-pre-wrap break-words font-sans text-xs text-slate-200">
            {msg.body ?? "(no body captured)"}
          </pre>
        </div>
      </div>
    );
  }

  const pending = !msg.at;
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] rounded-2xl rounded-tr-sm border border-brand-400/20 bg-brand-400/5 p-3">
        <div className="mb-1 flex flex-wrap items-center gap-2 text-[11px]">
          <span className="font-semibold text-brand-300">{stepLabel(msg.step)}</span>
          {msg.sender && <span className="font-mono text-slate-500">{msg.sender}</span>}
          <span className="text-slate-600">· {pending ? "draft (not sent)" : fmt(msg.at)}</span>
        </div>
        {msg.subject && <p className="mb-1 text-xs font-medium text-slate-300">{msg.subject}</p>}
        <pre className="whitespace-pre-wrap break-words font-sans text-xs text-slate-300">
          {msg.body ?? "(body not stored — sent before body logging was added)"}
        </pre>
      </div>
    </div>
  );
}

export default function EmailThreads({
  threads,
  isAdmin = false,
}: {
  threads: Thread[];
  isAdmin?: boolean;
}) {
  const [query, setQuery] = useState("");
  const [mailbox, setMailbox] = useState("all");
  const [selectedId, setSelectedId] = useState<string | null>(threads[0]?.id ?? null);

  const mailboxes = useMemo(() => {
    const set = new Set<string>();
    threads.forEach((t) => t.senders.forEach((s) => set.add(s)));
    return Array.from(set).sort();
  }, [threads]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return threads.filter((t) => {
      if (isAdmin && mailbox !== "all" && !t.senders.includes(mailbox)) return false;
      if (!q) return true;
      const haystack = [
        t.company,
        t.contact_email,
        t.job_title,
        ...t.messages.map((m) => m.body ?? ""),
        ...t.messages.map((m) => (m.kind === "sent" ? m.subject ?? "" : "")),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [threads, query, mailbox, isAdmin]);

  const selected =
    filtered.find((t) => t.id === selectedId) ?? filtered[0] ?? null;

  return (
    <div className="card flex h-[calc(100vh-11rem)] min-h-[28rem] overflow-hidden">
      {/* ── Conversation list ─────────────────────────────────────────── */}
      <div className="flex w-full min-w-0 flex-col border-r border-white/5 sm:w-80 md:w-96">
        <div className="space-y-2 border-b border-white/5 p-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search conversations…"
            className="w-full rounded-lg border border-white/10 bg-ink-950 px-3 py-1.5 text-sm text-slate-200 placeholder:text-slate-600 focus:border-brand-500/50 focus:outline-none"
          />
          {isAdmin && mailboxes.length > 1 && (
            <select
              value={mailbox}
              onChange={(e) => setMailbox(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-ink-950 px-3 py-1.5 text-sm text-slate-300 focus:border-brand-500/50 focus:outline-none"
            >
              <option value="all">All mailboxes</option>
              {mailboxes.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          )}
          <p className="px-1 text-[11px] text-slate-500">
            {filtered.length} conversation{filtered.length === 1 ? "" : "s"}
          </p>
        </div>

        <div className="flex-1 overflow-y-auto scrollbar-thin">
          {filtered.length === 0 && (
            <p className="px-4 py-10 text-center text-xs text-slate-600">
              {threads.length === 0 ? "No emails yet" : "No conversations match"}
            </p>
          )}
          {filtered.map((t) => {
            const st = STATUS_STYLES[t.status];
            const active = selected?.id === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setSelectedId(t.id)}
                className={`flex w-full flex-col gap-1 border-b border-white/5 px-4 py-3 text-left transition-colors ${
                  active ? "bg-white/[0.07]" : "hover:bg-white/[0.03]"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="flex min-w-0 items-center gap-2">
                    <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${st.dot}`} />
                    <span className="truncate text-sm font-medium text-slate-200">{t.company}</span>
                  </span>
                  <span className="shrink-0 text-[10px] text-slate-500">{fmtShort(t.lastActivity)}</span>
                </div>
                <p className="truncate text-xs text-slate-500">{snippet(t)}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Reading pane ──────────────────────────────────────────────── */}
      <div className="hidden min-w-0 flex-1 flex-col sm:flex">
        {!selected ? (
          <div className="flex flex-1 items-center justify-center text-sm text-slate-600">
            Select a conversation
          </div>
        ) : (
          <>
            <div className="flex items-start justify-between gap-3 border-b border-white/5 px-5 py-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="truncate text-sm font-semibold text-white">{selected.company}</h3>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${STATUS_STYLES[selected.status].cls}`}
                  >
                    {STATUS_STYLES[selected.status].label}
                  </span>
                </div>
                <p className="mt-0.5 truncate text-xs text-slate-500">
                  {selected.contact_email ?? "no contact email"}
                  {selected.job_title ? ` · ${selected.job_title}` : ""}
                  {selected.senders.length ? ` · via ${selected.senders.join(", ")}` : ""}
                </p>
              </div>
              {selected.job_url && (
                <a
                  href={selected.job_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 text-xs text-brand-400 hover:text-brand-300 hover:underline"
                >
                  Job posting →
                </a>
              )}
            </div>

            <div className="flex flex-1 flex-col gap-3 overflow-y-auto scrollbar-thin p-5">
              {selected.messages.length === 0 ? (
                <p className="py-6 text-center text-xs text-slate-600">
                  No email drafted or sent for this lead yet.
                </p>
              ) : (
                selected.messages.map((m, i) => <MessageBubble key={i} msg={m} />)
              )}
            </div>
          </>
        )}
      </div>

      {/* ── Mobile reading pane (below the list) ─────────────────────── */}
      {selected && (
        <div className="fixed inset-x-0 bottom-0 z-20 max-h-[55vh] overflow-y-auto scrollbar-thin border-t border-white/10 bg-ink-900 p-4 sm:hidden">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">{selected.company}</h3>
            <span className={`rounded-full px-2 py-0.5 text-[10px] ${STATUS_STYLES[selected.status].cls}`}>
              {STATUS_STYLES[selected.status].label}
            </span>
          </div>
          <div className="flex flex-col gap-3">
            {selected.messages.map((m, i) => (
              <MessageBubble key={i} msg={m} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
