"use client";

interface MailboxRow {
  sender: string;
  sent: number;
  replied: number;
  replyRate: number;
}

export default function MailboxTable({ rows }: { rows: MailboxRow[] }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100">
        <h2 className="text-sm font-semibold text-gray-700">Per-mailbox breakdown</h2>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 text-xs font-medium text-gray-500 uppercase tracking-wide">
            <th className="px-5 py-3 text-left">Mailbox</th>
            <th className="px-5 py-3 text-right">Sent</th>
            <th className="px-5 py-3 text-right">Replied</th>
            <th className="px-5 py-3 text-right">Reply rate</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.length === 0 && (
            <tr>
              <td colSpan={4} className="px-5 py-6 text-center text-gray-400">
                No sends yet
              </td>
            </tr>
          )}
          {rows.map((row) => (
            <tr key={row.sender} className="hover:bg-gray-50">
              <td className="px-5 py-3 font-mono text-xs text-gray-700">{row.sender}</td>
              <td className="px-5 py-3 text-right">{row.sent}</td>
              <td className="px-5 py-3 text-right">{row.replied}</td>
              <td className="px-5 py-3 text-right">
                <span
                  className={
                    row.replyRate >= 5
                      ? "text-green-600 font-medium"
                      : row.replyRate >= 2
                      ? "text-yellow-600"
                      : "text-gray-500"
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
  );
}
