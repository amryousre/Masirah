import { render, type RenderResult } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";

import { direction, type Locale } from "@/i18n/routing";
import ar from "@/messages/ar.json";
import en from "@/messages/en.json";

/** Renders a component the way a page would: inside its locale's messages and direction. */
export function renderIn(locale: Locale, ui: ReactElement): RenderResult {
  return render(
    <NextIntlClientProvider locale={locale} messages={locale === "ar" ? ar : en}>
      <div dir={direction(locale)} lang={locale}>
        {ui}
      </div>
    </NextIntlClientProvider>,
  );
}
