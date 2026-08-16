"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";

/**
 * Subscribes to Supabase Realtime and refreshes the dashboard's server data
 * whenever a row changes in the tables that feed the page. This makes the
 * stat cards / tables update live, with no manual page refresh.
 *
 * Requires Realtime to be enabled on these tables in Supabase (see
 * supabase/enable_realtime.sql).
 */
export default function RealtimeRefresh() {
  const router = useRouter();

  useEffect(() => {
    const supabase = createClient();

    const channel = supabase
      .channel("dashboard-changes")
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "sent_log" },
        () => router.refresh()
      )
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "leads" },
        () => router.refresh()
      )
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "replies" },
        () => router.refresh()
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [router]);

  return null;
}
