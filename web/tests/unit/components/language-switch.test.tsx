// @vitest-environment jsdom
import { screen } from "@testing-library/react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

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
  afterEach(() => {
    vi.restoreAllMocks();
  });

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
  it("disabled, is announced as unavailable, stays reachable, and leads nowhere", () => {
    renderIn("ar", <LanguageSwitch disabled />);
    const link = screen.getByRole("link", { name: "English" });
    expect(link).toHaveAttribute("aria-disabled", "true");
    expect(link).not.toHaveAttribute("href");
    expect(link).toHaveAttribute("tabindex", "0");
  });

  it("offline, stays on the page, says why, and can be tried again", async () => {
    vi.spyOn(navigator, "onLine", "get").mockReturnValue(false);
    renderIn("ar", <LanguageSwitch />);
    const link = screen.getByRole("link", { name: "English" });
    const click = new MouseEvent("click", { bubbles: true, cancelable: true });
    link.dispatchEvent(click);
    expect(click.defaultPrevented).toBe(true);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("تعذّر تغيير اللغة. ما زالت الصفحة بالعربية.");
    expect(link).toHaveAttribute("aria-describedby", alert.id);
    expect(link).toHaveAttribute("href", "/en/jobs/42");
  });

  it("online, opens the other language as usual", () => {
    renderIn("en", <LanguageSwitch />);
    const click = new MouseEvent("click", { bubbles: true, cancelable: true });
    screen.getByRole("link", { name: "العربية" }).dispatchEvent(click);
    expect(click.defaultPrevented).toBe(false);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("as a specimen, shows the message in English without announcing it", () => {
    renderIn("en", <LanguageSwitch failed />);
    expect(screen.queryByRole("alert")).toBeNull();
    expect(
      screen.getByText("Couldn't change the language. The page is still in English."),
    ).toBeVisible();
  });
});
