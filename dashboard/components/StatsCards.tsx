"use client";

interface Props {
  totalSent: number;
  totalReplies: number;
  replyRate: number;
  activeMailboxes: number;
}

function Card({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="mt-1 text-3xl font-bold text-gray-900">{value}</p>
    </div>
  );
}

export default function StatsCards({ totalSent, totalReplies, replyRate, activeMailboxes }: Props) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <Card label="Total Sent" value={totalSent.toLocaleString()} />
      <Card label="Replies" value={totalReplies.toLocaleString()} />
      <Card label="Reply Rate" value={`${replyRate.toFixed(1)}%`} />
      <Card label="Active Mailboxes" value={activeMailboxes} />
    </div>
  );
}
