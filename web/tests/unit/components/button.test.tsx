// @vitest-environment jsdom
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Button } from "@/components/button/button";

import { renderIn } from "./render";

describe("Button", () => {
  it("is a plain button named by its label", () => {
    renderIn("en", <Button>Save job</Button>);
    const button = screen.getByRole("button", { name: "Save job" });
    expect(button).toHaveAttribute("type", "button");
  });

  it("while loading, announces the progress verb and ignores clicks", async () => {
    const onClick = vi.fn();
    renderIn(
      "en",
      <Button variant="primary" loading loadingLabel="Saving…" onClick={onClick}>
        Save job
      </Button>,
    );
    const button = screen.getByRole("button", { name: "Saving…" });
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(button).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("keeps both labels in the button, so its width does not jump", () => {
    renderIn(
      "en",
      <Button loading={false} loadingLabel="Saving…">
        Save job
      </Button>,
    );
    const button = screen.getByRole("button", { name: "Save job" });
    expect(button).toHaveTextContent("Save job");
    expect(button).toHaveTextContent("Saving…");
  });

  it("says what went wrong beside the button, and ties it to the button", () => {
    renderIn("en", <Button error="Couldn't save. Try again.">Save job</Button>);
    const button = screen.getByRole("button", { name: "Save job" });
    expect(screen.getByRole("alert")).toHaveTextContent("Couldn't save. Try again.");
    expect(button).toHaveAccessibleDescription("Couldn't save. Try again.");
  });

  it("can be disabled", () => {
    renderIn("ar", <Button disabled>حفظ الوظيفة</Button>);
    expect(screen.getByRole("button", { name: "حفظ الوظيفة" })).toBeDisabled();
  });
});
