import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Outreach Console",
  description: "Cold outreach pipeline — sends, follow-ups, warm-up, and mailbox health",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans bg-ink-950 text-slate-200 antialiased">{children}</body>
    </html>
  );
}
