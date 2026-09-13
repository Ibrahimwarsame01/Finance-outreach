const NAV = [
  { label: "Overview", href: "/#overview", icon: "M3 12l9-9 9 9M4 10v10h16V10" },
  { label: "Performance", href: "/#performance", icon: "M4 19V5m0 14h16M8 15l3-4 3 2 4-6" },
  { label: "Mailboxes", href: "/#mailboxes", icon: "M3 8l9 6 9-6M3 8v10h18V8M3 8l9-5 9 5" },
  { label: "Leads", href: "/#leads", icon: "M17 20v-2a4 4 0 00-4-4H7a4 4 0 00-4 4v2M12 3a4 4 0 100 8 4 4 0 000-8z" },
  { label: "All Emails", href: "/emails", icon: "M3 7l9 6 9-6M4 6h16a1 1 0 011 1v10a1 1 0 01-1 1H4a1 1 0 01-1-1V7a1 1 0 011-1z" },
];

export default function Sidebar() {
  return (
    <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-white/5 bg-ink-900/60 px-4 py-6">
      <div className="flex items-center gap-2.5 px-2">
        <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-brand-400 to-accent-500 shadow-lg shadow-brand-500/20" />
        <div className="leading-tight">
          <p className="text-sm font-semibold text-white">Outreach</p>
          <p className="text-[11px] text-slate-500">Console</p>
        </div>
      </div>

      <nav className="mt-8 flex flex-col gap-1">
        {NAV.map((item) => (
          <a
            key={item.label}
            href={item.href}
            className="group flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-400 transition-colors hover:bg-white/5 hover:text-white"
          >
            <svg
              className="text-slate-500 group-hover:text-brand-400"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d={item.icon} />
            </svg>
            {item.label}
          </a>
        ))}
      </nav>

      <div className="mt-auto rounded-xl border border-white/5 bg-ink-800/50 p-3">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-brand-500" />
          </span>
          <p className="text-xs text-slate-400">Live — auto-updating</p>
        </div>
      </div>
    </aside>
  );
}
