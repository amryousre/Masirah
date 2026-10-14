// @vitest-environment jsdom
import { screen } from "@testing-library/react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { LanguageSwitch } from "@/components/language-switch/language-switch";

import { renderIn } from "./render";

// The real Link needs the Next.js router; this one renders the href it would navigate to.
vi.mock("@/i18n/navigation", () => ({
  usePathname: () => "/jobs/42",
  Link: ({
    href,
    locale,
    children,
    ...rest
  }: AnchorHTMLAttributes<HTMLAnchorElement> & { locale: string; children: ReactNode }) => (
    <a href={`/${locale}${String(href)}`} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("next/link", () => ({ useLinkStatus: () => ({ pending: false }) }));

describe("LanguageSwitch", () => {
  it("names English in English on an Arabic page, and keeps the same page", () => {
    renderIn("ar", <LanguageSwitch />);
    const link = screen.getByRole("link", { name: "English" });
    expect(link).toHaveAttribute("href", "/en/jobs/42");
    expect(link).toHaveAttribute("hreflang", "en");
    expect(screen.getByText("English")).toHaveAttribute("lang", "en");
  });

  it("names Arabic in Arabic on an English page", () => {
    renderIn("en", <LanguageSwitch />);
    const link = screen.getByRole("link", { name: "العربية" });
    expect(link).toHaveAttribute("href", "/ar/jobs/42");
    expect(screen.getByText("العربية")).toHaveAttribute("lang", "ar");
  });

  // T107: the seven states. Hover, focus and active are styles; disabled, loading and error are
  // states the component renders.
  it("disabled, still names the other language but leads nowhere", () => {
    renderIn("ar", <LanguageSwitch disabled />);
    expect(screen.queryByRole("link")).toBeNull();
    const control = screen.getByText("English").closest("[aria-disabled]");
    expect(control).toHaveAttribute("aria-disabled", "true");
  });

  it("after a failed switch, says the page stayed in its language and can be tried again", () => {
    renderIn("ar", <LanguageSwitch failed />);
    expect(screen.getByRole("link", { name: /English/ })).toHaveAttribute("href", "/en/jobs/42");
    expect(screen.getByRole("alert")).toHaveTextContent(
      "تعذّر تغيير اللغة. ما زالت الصفحة بالعربية.",
    );
  });

  it("says so in English on an English page", () => {
    renderIn("en", <LanguageSwitch failed />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Couldn't change the language. The page is still in English.",
    );
  });
});
