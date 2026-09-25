import { createServerClient, type CookieMethodsServer } from "@supabase/ssr";
import { cookies } from "next/headers";

import type { Database } from "./database.types";

function required(name: string, value: string | undefined): string {
  if (!value) {
    throw new Error(`${name} is not set. See web/.env.example for the variables sign-in needs.`);
  }
  return value;
}

/**
 * The address this app is served from, which Google sign-in returns to. It is configuration
 * rather than read from the request, so a forged Host header cannot choose where sign-in lands.
 */
export function siteUrl(): string {
  return required("SITE_URL", process.env["SITE_URL"]).replace(/\/$/, "");
}

/** A Supabase client acting as the signed-in user, with row level security applied. */
export function createSupabaseClient(cookieMethods: CookieMethodsServer) {
  return createServerClient<Database>(
    required("NEXT_PUBLIC_SUPABASE_URL", process.env["NEXT_PUBLIC_SUPABASE_URL"]),
    required(
      "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
      process.env["NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"],
    ),
    { cookies: cookieMethods },
  );
}

export type SupabaseClient = ReturnType<typeof createSupabaseClient>;

/** The client for Server Components, Server Actions and Route Handlers. */
export async function createSupabaseServerClient(): Promise<SupabaseClient> {
  const store = await cookies();
  return createSupabaseClient({
    getAll: () => store.getAll(),
    setAll: (toSet) => {
      try {
        for (const { name, value, options } of toSet) store.set(name, value, options);
      } catch {
        // A Server Component cannot set cookies. The proxy has already refreshed the session
        // for this request, so there is nothing to write.
      }
    },
  });
}
