import { createClient } from "@supabase/supabase-js";

import type { HealthFigures } from "@/lib/domain/health";

import type { Database } from "./database.types";

const TIMEOUT_MS = 5_000;

/**
 * The queue and heartbeat figures from public.service_health() (migration 0016). It is called
 * without a session, so a monitor needs no credentials: the function returns three aggregate
 * numbers and nothing about any organisation. Null when the database cannot be reached.
 */
export async function readHealthFigures(): Promise<HealthFigures | null> {
  const url = process.env["NEXT_PUBLIC_SUPABASE_URL"];
  const key = process.env["NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"];
  if (!url || !key) return null;
  const supabase = createClient<Database>(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
    // A stalled database must still produce a prompt 503, not a monitor's own timeout.
    db: { timeout: TIMEOUT_MS },
  });
  const { data, error } = await supabase.rpc("service_health");
  const row = data?.[0];
  if (error || !row) return null;
  // The generated types call these numbers, but an empty queue and a worker that never beat
  // both come back as null.
  const oldest: number | null = row.oldest_message_seconds;
  const heartbeat: number | null = row.heartbeat_age_seconds;
  return {
    queueDepth: row.queue_depth,
    oldestMessageSeconds: oldest,
    heartbeatAgeSeconds: heartbeat,
  };
}
