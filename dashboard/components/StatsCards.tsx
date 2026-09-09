interface StatItem {
  label: string;
  value: string | number;
  hint?: string;
  accent?: "brand" | "accent" | "emerald" | "slate";
}

const ACCENTS: Record<NonNullable<StatItem["accent"]>, string> = {
  brand: "from-brand-400/20 to-brand-500/5 text-brand-400",
  accent: "from-accent-400/20 to-accent-500/5 text-accent-400",
  emerald: "from-emerald-400/20 to-emerald-500/5 text-emerald-400",
  slate: "from-slate-400/20 to-slate-500/5 text-slate-300",
};

function Card({ label, value, hint, accent = "slate" }: StatItem) {
  return (
    <div className="card p-5 relative overflow-hidden">
      <div
        className={`pointer-events-none absolute -right-6 -top-6 h-20 w-20 rounded-full bg-gradient-to-br ${ACCENTS[accent]} blur-xl`}
      />
      <p className="text-[11px] font-medium uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-white">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

export default function StatsCards({ items }: { items: StatItem[] }) {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
      {items.map((item) => (
        <Card key={item.label} {...item} />
      ))}
    </div>
  );
}
