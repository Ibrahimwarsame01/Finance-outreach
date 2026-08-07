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
}

function StatusBadge({ lead }: { lead: Lead }) {
  if (lead.reply_body)
    return <span className="px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700 font-medium">Replied</span>;
  if (lead.sent_at)
    return <span className="px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-700 font-medium">Sent</span>;
  if (lead.email_body)
    return <span className="px-2 py-0.5 rounded-full text-xs bg-yellow-100 text-yellow-700 font-medium">Drafted</span>;
  return <span className="px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-500 font-medium">New</span>;
}

function ExpandedRow({ lead }: { lead: Lead }) {
  return (
    <tr className="bg-gray-50">
      <td colSpan={5} className="px-5 pb-4 pt-2">
        {lead.email_subject && (
          <div className="mb-2">
            <span className="text-xs font-semibold text-gray-500">Subject: </span>
            <span className="text-xs text-gray-800">{lead.email_subject}</span>
          </div>
        )}
        {lead.email_body && (
          <pre className="text-xs text-gray-700 whitespace-pre-wrap font-sans bg-white border border-gray-200 rounded-lg p-3 max-h-48 overflow-y-auto">
            {lead.email_body}
          </pre>
        )}
        {lead.reply_body && (
          <>
            <p className="text-xs font-semibold text-gray-500 mt-3 mb-1">Reply received:</p>
            <pre className="text-xs text-gray-700 whitespace-pre-wrap font-sans bg-green-50 border border-green-200 rounded-lg p-3 max-h-40 overflow-y-auto">
              {lead.reply_body}
            </pre>
          </>
        )}
        {lead.job_url && (
          <a
            href={lead.job_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block mt-2 text-xs text-blue-600 hover:underline"
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
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100">
        <h2 className="text-sm font-semibold text-gray-700">Recent leads</h2>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 text-xs font-medium text-gray-500 uppercase tracking-wide">
            <th className="px-5 py-3 text-left">Company</th>
            <th className="px-5 py-3 text-left">Role</th>
            <th className="px-5 py-3 text-left">Contact</th>
            <th className="px-5 py-3 text-left">Sent via</th>
            <th className="px-5 py-3 text-left">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {leads.length === 0 && (
            <tr>
              <td colSpan={5} className="px-5 py-6 text-center text-gray-400">
                No leads yet
              </td>
            </tr>
          )}
          {leads.map((lead) => (
            <Fragment key={lead.id}>
              <tr
                className="hover:bg-gray-50 cursor-pointer"
                onClick={() => setExpanded(expanded === lead.id ? null : lead.id)}
              >
                <td className="px-5 py-3 font-medium text-gray-800">{lead.company}</td>
                <td className="px-5 py-3 text-gray-600 truncate max-w-[180px]">{lead.job_title ?? "—"}</td>
                <td className="px-5 py-3 text-gray-600 font-mono text-xs">{lead.contact_email ?? "—"}</td>
                <td className="px-5 py-3 text-gray-500 font-mono text-xs">{lead.sender ?? "—"}</td>
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
  );
}
