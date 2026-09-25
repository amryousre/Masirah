// @vitest-environment jsdom
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Toast, ToastRegion } from "@/components/toast/toast";

import { renderIn } from "./render";

describe("Toast", () => {
  it("announces a fact politely and offers one action", async () => {
    const onAction = vi.fn();
    renderIn(
      "en",
      <ToastRegion>
        <Toast
          tone="success"
          message="24 of 25 files are processed."
          action={{ label: "Open ranking", onAction }}
        />
      </ToastRegion>,
    );
    expect(screen.getByRole("region", { name: "Notifications" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("24 of 25 files are processed.");
    await userEvent.click(screen.getByRole("button", { name: "Open ranking" }));
    expect(onAction).toHaveBeenCalledTimes(1);
  });

  it("announces a failure at once", () => {
    renderIn("en", <Toast tone="error" message="3 messages couldn't be sent." />);
    expect(screen.getByRole("alert")).toHaveTextContent("3 messages couldn't be sent.");
  });

  it("can be dismissed from a labelled button", async () => {
    const onDismiss = vi.fn();
    renderIn("ar", <Toast tone="neutral" message="رُفض المرشح." onDismiss={onDismiss} />);
    await userEvent.click(screen.getByRole("button", { name: "إغلاق الإشعار" }));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
