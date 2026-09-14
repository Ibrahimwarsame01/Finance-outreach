/**
 * Role resolution for the dashboard.
 *
 * There is exactly one admin, identified by the ADMIN_EMAIL env var (set in
 * Vercel). The admin sees everything across all mailboxes. Every other
 * authenticated user is a "non-admin" scoped to a single mailbox — the one
 * whose address equals their login email (e.g. someone who logs in as
 * sam@clearbooks-plus.com only sees sam's sent/received/replies and stats).
 *
 * Because the check is done server-side against the authenticated session's
 * email, it can't be spoofed from the browser.
 */
export interface Role {
  isAdmin: boolean;
  /** For a non-admin, the mailbox address their view is scoped to. null = all (admin). */
  mailbox: string | null;
  email: string;
}

export function resolveRole(email: string | null | undefined): Role {
  const adminEmail = (process.env.ADMIN_EMAIL ?? "").trim().toLowerCase();
  const e = (email ?? "").trim().toLowerCase();
  const isAdmin = !!e && !!adminEmail && e === adminEmail;
  return { isAdmin, mailbox: isAdmin ? null : e, email: e };
}
