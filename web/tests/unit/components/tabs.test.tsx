// @vitest-environment jsdom
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Tabs } from "@/components/tabs/tabs";
import type { Locale } from "@/i18n/routing";

import { renderIn } from "./render";

const items = [
  { id: "candidates", label: "Candidates", count: 42 },
  { id: "review", label: "Review queue", count: 3 },
  { id: "scorecard", label: "Scorecard", disabled: true },
  { id: "channels", label: "Channels", error: "Couldn't load channels." },
];

function renderTabs(locale: Locale, selected = "candidates") {
  const onSelect = vi.fn();
  renderIn(
    locale,
    <Tabs label="Job sections" items={items} selected={selected} onSelect={onSelect}>
      <p>Panel</p>
    </Tabs>,
  );
  return onSelect;
}

describe("Tabs", () => {
  it("marks the selected tab and labels the panel with it", () => {
    renderTabs("en");
    const tab = screen.getByRole("tab", { name: /Candidates/ });
    expect(tab).toHaveAttribute("aria-selected", "true");
    expect(tab).toHaveAttribute("tabindex", "0");
    expect(screen.getByRole("tab", { name: /Review queue/ })).toHaveAttribute("tabindex", "-1");
    expect(screen.getByRole("tabpanel")).toHaveAccessibleName(/Candidates/);
  });

  it("moves forward with the arrow that points forward in English", async () => {
    const onSelect = renderTabs("en");
    screen.getByRole("tab", { name: /Candidates/ }).focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(onSelect).toHaveBeenCalledWith("review");
  });

  it("moves forward with the left arrow in Arabic, because it reads right to left", async () => {
    const onSelect = renderTabs("ar");
    screen.getByRole("tab", { name: /Candidates/ }).focus();
    await userEvent.keyboard("{ArrowLeft}");
    expect(onSelect).toHaveBeenCalledWith("review");
  });

  it("skips a disabled tab", async () => {
    const onSelect = renderTabs("en", "review");
    screen.getByRole("tab", { name: /Review queue/ }).focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(onSelect).toHaveBeenCalledWith("channels");
  });

  it("jumps to the ends with Home and End", async () => {
    const onSelect = renderTabs("en", "review");
    screen.getByRole("tab", { name: /Review queue/ }).focus();
    await userEvent.keyboard("{End}");
    expect(onSelect).toHaveBeenLastCalledWith("channels");
    await userEvent.keyboard("{Home}");
    expect(onSelect).toHaveBeenLastCalledWith("candidates");
  });

  it("describes a tab that failed to load", () => {
    renderTabs("en");
    expect(screen.getByRole("tab", { name: /Channels/ })).toHaveAccessibleDescription(
      "Couldn't load channels.",
    );
  });
});
