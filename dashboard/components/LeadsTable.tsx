"use client";

import { Fragment, useState } from "react";

interface Lead {
  id: string;
  company: string;
  contact_email: string | null;
  job_title: string | null;
  job_url: string | null;
  email_subject: string | null;
  email_body: string | null;
  sent_at: string | null;
  sender: string | null;
  reply_body: string | null;
  followups: number;
}

function StatusBadge({ lead }: { lead: Lead }) {
  const base = "px-2 py-0.5 rounded-full text-xs font-medium";
  if (lead.reply_body)
    return <span className={`${base} bg-emerald-400/15 text-emerald-300`}>Replied</span>;
  if (lead.followups > 0)
    return (
      <span className={`${base} bg-accent-400/15 text-accent-400`}>
        Followed up ×{lead.followups}
      </span>
    );
  if (lead.sent_at)
    return <span className={`${base} bg-brand-400/15 text-brand-400`}>Sent</span>;
  if (lead.email_body)
    return <span className={`${base} bg-amber-400/15 text-amber-300`}>Drafted</span>;
  return <span className={`${base} bg-white/5 text-slate-400`}>New</span>;
}

function ExpandedRow({ lead }: { lead: Lead }) {
  return (
    <tr className="bg-ink-950/40">
      <td colSpan={5} className="px-5 pb-4 pt-2">
        {lead.email_subject && (
          <div className="mb-2">
            <span className="text-xs font-semibold text-slate-500">Subject: </span>
            <span className="text-xs text-slate-300">{lead.email_subject}</span>
          </div>
        )}
        {lead.email_body && (
          <pre className="max-h-48 overflow-y-auto scrollbar-thin whitespace-pre-wrap rounded-lg border border-white/5 bg-ink-900 p-3 font-sans text-xs text-slate-300">
            {lead.email_body}
          </pre>
        )}
        {lead.reply_body && (
          <>
            <p className="mb-1 mt-3 text-xs font-semibold text-emerald-400">Reply received</p>
            <pre className="max-h-40 overflow-y-auto scrollbar-thin whitespace-pre-wrap rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3 font-sans text-xs text-slate-200">
              {lead.reply_body}
            </pre>
          </>
        )}
        {lead.job_url && (
          <a
            href={lead.job_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 inline-block text-xs text-brand-400 hover:text-brand-300 hover:underline"
          >
            View job posting →
          </a>
        )}
      </td>
    </tr>
  );
}

export default function LeadsTable({ leads }: { leads: Lead[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="card overflow-hidden">
      <div className="border-b border-white/5 px-5 py-4">
        <h2 className="text-sm font-semibold text-white">Recent leads</h2>
        <p className="mt-0.5 text-xs text-slate-500">Click a row to see the email + reply thread</p>
      </div>
      <div className="overflow-x-auto scrollbar-thin">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
              <th className="px-5 py-3 text-left">Company</th>
              <th className="px-5 py-3 text-left">Role</th>
              <th className="px-5 py-3 text-left">Contact</th>
              <th className="px-5 py-3 text-left">Sent via</th>
              <th className="px-5 py-3 text-left">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {leads.length === 0 && (
              <tr>
                <td colSpan={5} className="px-5 py-8 text-center text-slate-600">
                  No leads yet
                </td>
              </tr>
            )}
            {leads.map((lead) => (
              <Fragment key={lead.id}>
                <tr
                  className="cursor-pointer transition-colors hover:bg-white/5"
                  onClick={() => setExpanded(expanded === lead.id ? null : lead.id)}
                >
                  <td className="px-5 py-3 font-medium text-slate-200">{lead.company}</td>
                  <td className="max-w-[180px] truncate px-5 py-3 text-slate-400">
                    {lead.job_title ?? "—"}
                  </td>
                  <td className="px-5 py-3 font-mono text-xs text-slate-400">
                    {lead.contact_email ?? "—"}
                  </td>
                  <td className="px-5 py-3 font-mono text-xs text-slate-500">
                    {lead.sender ?? "—"}
                  </td>
                  <td className="px-5 py-3">
                    <StatusBadge lead={lead} />
                  </td>
                </tr>
                {expanded === lead.id && <ExpandedRow lead={lead} />}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
