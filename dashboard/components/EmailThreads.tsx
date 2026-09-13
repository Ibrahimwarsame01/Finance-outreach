"use client";

import { Fragment, useMemo, useState } from "react";

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

const STATUS_STYLES: Record<Thread["status"], { label: string; cls: string }> = {
  replied: { label: "Replied", cls: "bg-emerald-400/15 text-emerald-300" },
  followed_up: { label: "Followed up", cls: "bg-accent-400/15 text-accent-400" },
  sent: { label: "Sent", cls: "bg-brand-400/15 text-brand-400" },
  drafted: { label: "Drafted", cls: "bg-amber-400/15 text-amber-300" },
  new: { label: "New", cls: "bg-white/5 text-slate-400" },
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

function stepLabel(step: number): string {
  return step === 0 ? "Initial outreach" : `Follow-up #${step}`;
}

function MessageBubble({ msg }: { msg: ThreadMessage }) {
  if (msg.kind === "reply") {
    return (
      <div className="flex justify-start">
        <div className="max-w-[85%] rounded-2xl rounded-tl-sm border border-emerald-400/20 bg-emerald-400/5 p-3">
          <div className="mb-1 flex items-center gap-2 text-[11px]">
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
      <div className="max-w-[85%] rounded-2xl rounded-tr-sm border border-brand-400/20 bg-brand-400/5 p-3">
        <div className="mb-1 flex flex-wrap items-center gap-2 text-[11px]">
          <span className="font-semibold text-brand-300">{stepLabel(msg.step)}</span>
          {msg.sender && <span className="font-mono text-slate-500">{msg.sender}</span>}
          <span className="text-slate-600">
            · {pending ? "not sent yet (draft)" : fmt(msg.at)}
          </span>
        </div>
        {msg.subject && (
          <p className="mb-1 text-xs font-medium text-slate-300">{msg.subject}</p>
        )}
        <pre className="whitespace-pre-wrap break-words font-sans text-xs text-slate-300">
          {msg.body ?? "(body not stored — sent before body logging was added)"}
        </pre>
      </div>
    </div>
  );
}

export default function EmailThreads({ threads }: { threads: Thread[] }) {
  const [query, setQuery] = useState("");
  const [mailbox, setMailbox] = useState("all");
  const [expanded, setExpanded] = useState<string | null>(null);

  const mailboxes = useMemo(() => {
    const set = new Set<string>();
    threads.forEach((t) => t.senders.forEach((s) => set.add(s)));
    return Array.from(set).sort();
  }, [threads]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return threads.filter((t) => {
      if (mailbox !== "all" && !t.senders.includes(mailbox)) return false;
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
  }, [threads, query, mailbox]);

  return (
    <div className="card overflow-hidden">
      {/* Controls */}
      <div className="flex flex-col gap-3 border-b border-white/5 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold text-white">All email threads</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {filtered.length} of {threads.length} leads · click a row for the full thread
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search company, email, subject, body…"
            className="w-full rounded-lg border border-white/10 bg-ink-950 px-3 py-1.5 text-sm text-slate-200 placeholder:text-slate-600 focus:border-brand-500/50 focus:outline-none sm:w-72"
          />
          <select
            value={mailbox}
            onChange={(e) => setMailbox(e.target.value)}
            className="rounded-lg border border-white/10 bg-ink-950 px-3 py-1.5 text-sm text-slate-300 focus:border-brand-500/50 focus:outline-none"
          >
            <option value="all">All mailboxes</option>
            {mailboxes.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto scrollbar-thin">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
              <th className="px-5 py-3 text-left">Company</th>
              <th className="px-5 py-3 text-left">Role</th>
              <th className="px-5 py-3 text-left">Contact</th>
              <th className="px-5 py-3 text-left">Mailbox(es)</th>
              <th className="px-5 py-3 text-left">Msgs</th>
              <th className="px-5 py-3 text-left">Last activity</th>
              <th className="px-5 py-3 text-left">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {filtered.length === 0 && (
              <tr>
                <td colSpan={7} className="px-5 py-10 text-center text-slate-600">
                  {threads.length === 0 ? "No leads yet" : "No threads match your filters"}
                </td>
              </tr>
            )}
            {filtered.map((t) => {
              const status = STATUS_STYLES[t.status];
              const isOpen = expanded === t.id;
              return (
                <Fragment key={t.id}>
                  <tr
                    className="cursor-pointer transition-colors hover:bg-white/5"
                    onClick={() => setExpanded(isOpen ? null : t.id)}
                  >
                    <td className="px-5 py-3 font-medium text-slate-200">{t.company}</td>
                    <td className="max-w-[180px] truncate px-5 py-3 text-slate-400">
                      {t.job_title ?? "—"}
                    </td>
                    <td className="px-5 py-3 font-mono text-xs text-slate-400">
                      {t.contact_email ?? "—"}
                    </td>
                    <td className="px-5 py-3 font-mono text-xs text-slate-500">
                      {t.senders.length ? t.senders.join(", ") : "—"}
                    </td>
                    <td className="px-5 py-3 text-slate-400">{t.messages.length}</td>
                    <td className="whitespace-nowrap px-5 py-3 text-xs text-slate-500">
                      {fmt(t.lastActivity)}
                    </td>
                    <td className="px-5 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${status.cls}`}>
                        {status.label}
                      </span>
                    </td>
                  </tr>
                  {isOpen && (
                    <tr className="bg-ink-950/40">
                      <td colSpan={7} className="px-5 pb-5 pt-2">
                        {t.messages.length === 0 ? (
                          <p className="py-4 text-center text-xs text-slate-600">
                            No email drafted or sent for this lead yet.
                          </p>
                        ) : (
                          <div className="flex flex-col gap-3">
                            {t.messages.map((m, i) => (
                              <MessageBubble key={i} msg={m} />
                            ))}
                          </div>
                        )}
                        {t.job_url && (
                          <a
                            href={t.job_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-3 inline-block text-xs text-brand-400 hover:text-brand-300 hover:underline"
                          >
                            View job posting →
                          </a>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
