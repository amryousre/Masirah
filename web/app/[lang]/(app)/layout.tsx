import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";

import { AppFrame } from "@/components/app-frame/app-frame";
import { redirect } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";
import { UsageMeter } from "@/components/usage-meter/usage-meter";
import { countReviewQueue } from "@/lib/adapters/review-queue";
import { getAccess } from "@/lib/adapters/session";
import { createSupabaseServerClient } from "@/lib/adapters/supabase";
import { readUsage, renewalDay } from "@/lib/adapters/usage";

import { signOut } from "../sign-in/actions";

// Every product screen sits in this group, behind sign-in (T024). Row level security is what
// keeps an organisation's data to itself; this check is what sends a visitor to the right page.
export default async function ProductLayout({ children, params }: LayoutProps<"/[lang]">) {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();

  const access = await getAccess();
  if (access.kind === "signed-out") return redirect({ href: "/sign-in", locale: lang });
  if (access.kind === "no-organisation") {
    return redirect({
      href: { pathname: "/sign-in/no-access", query: { reason: "no-organisation" } },
      locale: lang,
    });
  }

  const { session } = access;
  // Beside the queue's link, so a file that was not ranked is seen from every screen (FR-011),
  // and the month's usage above the user (FR-026). Both are only signs: when either cannot be
  // read it is left out, and the page still renders.
  const supabase = await createSupabaseServerClient();
  const [reviewCount, usage] = await Promise.all([
    countReviewQueue(supabase).catch(() => undefined),
    readUsage(supabase).catch(() => null),
  ]);
  return (
    <AppFrame
      organisation={session.organisationName}
      user={{ name: session.name, email: session.email }}
      reviewCount={reviewCount}
      usage={
        usage === null ? undefined : (
          <UsageMeter
            used={usage.used}
            limit={usage.limit}
            renewsOn={renewalDay(usage.renewsAt, lang)}
            waiting={usage.waiting}
            paused={usage.atLimit}
          />
        )
      }
      signOut={signOut.bind(null, lang)}
    >
      {children}
    </AppFrame>
  );
}
