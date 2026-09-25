"use server";

import { redirect as redirectOut } from "next/navigation";
import { hasLocale } from "next-intl";

import { redirect } from "@/i18n/navigation";
import { type Locale, routing } from "@/i18n/routing";
import { readAccess } from "@/lib/adapters/session";
import { createSupabaseServerClient, siteUrl } from "@/lib/adapters/supabase";

export interface PasswordSignInState {
  readonly error?: "missing" | "invalid" | "unavailable";
  /** Given back so a failed attempt does not make the person retype it. */
  readonly email: string;
}

// The locale is bound on the server, but an action is still an endpoint: check it anyway.
function checked(locale: string): Locale {
  if (!hasLocale(routing.locales, locale)) throw new Error("Unknown locale");
  return locale;
}

function text(form: FormData, name: string): string {
  const value = form.get(name);
  return typeof value === "string" ? value : "";
}

/** Sends the person to Google, which returns them to /{lang}/auth/callback. */
export async function signInWithGoogle(locale: Locale): Promise<void> {
  const lang = checked(locale);
  const supabase = await createSupabaseServerClient();
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: `${siteUrl()}/${lang}/auth/callback`,
      // Always offer Google's account chooser, so someone signed in to a personal account in
      // this browser can pick the work account they were invited with.
      queryParams: { prompt: "select_account" },
    },
  });
  if (error) {
    return redirect({ href: { pathname: "/sign-in", query: { error: "google" } }, locale: lang });
  }
  redirectOut(data.url);
}

export async function signInWithPassword(
  locale: Locale,
  _previous: PasswordSignInState,
  form: FormData,
): Promise<PasswordSignInState> {
  const lang = checked(locale);
  const email = text(form, "email").trim();
  const password = text(form, "password");
  if (email === "" || password === "") return { error: "missing", email };

  const supabase = await createSupabaseServerClient();
  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) {
    // One message for a wrong email and a wrong password, so the form does not reveal which
    // addresses have accounts.
    return { error: error.code === "invalid_credentials" ? "invalid" : "unavailable", email };
  }

  const access = await readAccess(supabase);
  if (access.kind !== "member") {
    await supabase.auth.signOut({ scope: "local" });
    return redirect({
      href: { pathname: "/sign-in/no-access", query: { reason: "no-organisation" } },
      locale: lang,
    });
  }
  return redirect({ href: "/jobs", locale: lang });
}

/** Ends this browser's session only; other devices stay signed in. */
export async function signOut(locale: Locale): Promise<void> {
  const lang = checked(locale);
  const supabase = await createSupabaseServerClient();
  await supabase.auth.signOut({ scope: "local" });
  redirect({ href: "/sign-in", locale: lang });
}
