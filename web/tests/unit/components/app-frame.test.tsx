// @vitest-environment jsdom
import { screen, within } from "@testing-library/react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { AppFrame } from "@/components/app-frame/app-frame";

import { renderIn } from "./render";

vi.mock("@/i18n/navigation", () => ({
  usePathname: () => "/jobs/42",
  Link: ({
    href,
    locale,
    children,
    ...rest
  }: AnchorHTMLAttributes<HTMLAnchorElement> & { locale?: string; children: ReactNode }) => (
    <a href={`/${locale ?? "xx"}${String(href)}`} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("next/link", () => ({ useLinkStatus: () => ({ pending: false }) }));

describe("AppFrame", () => {
  it("names the product and the organisation, and holds the page", () => {
    renderIn(
      "ar",
      <AppFrame organisation="دلتا سوفت" user={{ name: "نورهان سعيد", email: "n@example.com" }}>
        <h1>الوظائف</h1>
      </AppFrame>,
    );
    expect(screen.getByText("مسيرة")).toBeInTheDocument();
    expect(screen.getByText("دلتا سوفت")).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveTextContent("الوظائف");
  });

  it("marks the section the user is in, and shows what waits in review", () => {
    renderIn(
      "en",
      <AppFrame
        organisation="Delta Soft"
        user={{ name: "Nourhan Saeed", email: "n@example.com" }}
        reviewCount={5}
      >
        <p>Page</p>
      </AppFrame>,
    );
    const nav = screen.getByRole("navigation", { name: "Main navigation" });
    expect(within(nav).getByRole("link", { name: "Jobs" })).toHaveAttribute("aria-current", "page");
    expect(within(nav).getByRole("link", { name: /Review queue\s*5/ })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("keeps the language switch and the user on every screen", () => {
    renderIn(
      "en",
      <AppFrame organisation="Delta Soft" user={{ name: "Nourhan Saeed", email: "n@example.com" }}>
        <p>Page</p>
      </AppFrame>,
    );
    expect(screen.getByRole("link", { name: "العربية" })).toBeInTheDocument();
    expect(screen.getByText("Nourhan Saeed")).toBeInTheDocument();
  });

  it("names a user without a name by their email", () => {
    renderIn(
      "en",
      <AppFrame organisation="Delta Soft" user={{ name: null, email: "karim@example.com" }}>
        <p>Page</p>
      </AppFrame>,
    );
    expect(screen.getByText("karim@example.com")).toBeInTheDocument();
    expect(screen.getByText("K")).toBeInTheDocument();
  });

  it("offers sign-out as a form, so it works before any script loads", () => {
    const signOut = vi.fn(() => Promise.resolve());
    renderIn(
      "ar",
      <AppFrame
        organisation="دلتا سوفت"
        user={{ name: "نورهان سعيد", email: "n@example.com" }}
        signOut={signOut}
      >
        <p>الصفحة</p>
      </AppFrame>,
    );
    const button = screen.getByRole("button", { name: "تسجيل الخروج" });
    expect(button).toHaveAttribute("type", "submit");
    expect(button.closest("form")).not.toBeNull();
  });

  it("leaves sign-out out where there is no session to end", () => {
    renderIn(
      "en",
      <AppFrame organisation="Delta Soft" user={{ name: "Nourhan Saeed", email: "n@example.com" }}>
        <p>Page</p>
      </AppFrame>,
    );
    expect(screen.queryByRole("button", { name: "Sign out" })).toBeNull();
  });
});
