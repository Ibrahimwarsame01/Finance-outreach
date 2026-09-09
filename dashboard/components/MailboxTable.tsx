interface MailboxRow {
  sender: string;
  sent: number;
  replied: number;
  replyRate: number;
}

function healthDot(replyRate: number, sent: number) {
  // Not enough signal yet
  if (sent < 5) return "bg-slate-500";
  if (replyRate >= 5) return "bg-emerald-400";
  if (replyRate >= 2) return "bg-amber-400";
  return "bg-rose-400";
}

export default function MailboxTable({ rows }: { rows: MailboxRow[] }) {
  return (
    <div className="card overflow-hidden">
      <div className="border-b border-white/5 px-5 py-4">
        <h2 className="text-sm font-semibold text-white">Per-mailbox breakdown</h2>
        <p className="mt-0.5 text-xs text-slate-500">
          Spot an underperforming or flagged mailbox at a glance
        </p>
      </div>
      <div className="overflow-x-auto scrollbar-thin">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
              <th className="px-5 py-3 text-left">Mailbox</th>
              <th className="px-5 py-3 text-right">Sent</th>
              <th className="px-5 py-3 text-right">Replied</th>
              <th className="px-5 py-3 text-right">Reply rate</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {rows.length === 0 && (
              <tr>
                <td colSpan={4} className="px-5 py-8 text-center text-slate-600">
                  No sends yet
                </td>
              </tr>
            )}
            {rows.map((row) => (
              <tr key={row.sender} className="transition-colors hover:bg-white/5">
                <td className="px-5 py-3">
                  <div className="flex items-center gap-2.5">
                    <span className={`h-2 w-2 rounded-full ${healthDot(row.replyRate, row.sent)}`} />
                    <span className="font-mono text-xs text-slate-300">{row.sender}</span>
                  </div>
                </td>
                <td className="px-5 py-3 text-right text-slate-300">{row.sent}</td>
                <td className="px-5 py-3 text-right text-slate-300">{row.replied}</td>
                <td className="px-5 py-3 text-right">
                  <span
                    className={
                      row.replyRate >= 5
                        ? "font-medium text-emerald-400"
                        : row.replyRate >= 2
                        ? "text-amber-400"
                        : "text-slate-500"
                    }
                  >
                    {row.replyRate.toFixed(1)}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
