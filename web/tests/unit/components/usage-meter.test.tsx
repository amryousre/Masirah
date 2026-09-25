// @vitest-environment jsdom
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { UsageMeter } from "@/components/usage-meter/usage-meter";

import { renderIn } from "./render";

describe("UsageMeter", () => {
  it("shows use against the limit and when it renews", () => {
    renderIn("ar", <UsageMeter used={126} limit={300} renewsOn="1 أكتوبر" />);
    expect(screen.getByText("126 من 300")).toBeInTheDocument();
    expect(screen.getByText("يتجدد في 1 أكتوبر.")).toBeInTheDocument();
    expect(screen.getByRole("meter", { name: "السير الذاتية هذا الشهر" })).toHaveAttribute(
      "aria-valuenow",
      "126",
    );
  });

  it("from 80 percent, says how many are left and that processing continues", () => {
    renderIn("en", <UsageMeter used={246} limit={300} renewsOn="1 Oct" />);
    expect(screen.getByText("54 CVs left this month. Processing continues.")).toBeInTheDocument();
  });

  it("uses the right Arabic plural", () => {
    renderIn("ar", <UsageMeter used={298} limit={300} renewsOn="1 أكتوبر" />);
    expect(screen.getByText("بقيت سيرتان هذا الشهر. المعالجة مستمرة.")).toBeInTheDocument();
  });

  it("at the limit, explains the pause and offers a way on", async () => {
    const onUpgrade = vi.fn();
    renderIn(
      "en",
      <UsageMeter used={300} limit={300} renewsOn="1 Oct" waiting={14} onUpgrade={onUpgrade} />,
    );
    expect(
      screen.getByText(
        "Processing is paused. 14 files are waiting and will be processed when you upgrade or on 1 Oct. Nothing was deleted or hidden.",
      ),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Upgrade plan" }));
    expect(onUpgrade).toHaveBeenCalledTimes(1);
  });

  it("says so while usage is loading", () => {
    renderIn("en", <UsageMeter loading />);
    expect(screen.getByText("Loading usage…")).toBeInTheDocument();
  });
});
