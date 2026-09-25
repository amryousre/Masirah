// @vitest-environment jsdom
import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { Dialog } from "@/components/dialog/dialog";

import { renderIn } from "./render";

// jsdom has <dialog> but not its modal methods; the browser behaviour is covered end to end.
beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
});

describe("Dialog", () => {
  it("is named by its title and offers a labelled close button", () => {
    renderIn(
      "ar",
      <Dialog open title="تجاهل التعديلات على الوظيفة؟" onClose={vi.fn()}>
        <p>نص</p>
      </Dialog>,
    );
    expect(screen.getByRole("dialog", { name: "تجاهل التعديلات على الوظيفة؟" })).toBeVisible();
    expect(screen.getByRole("button", { name: "إغلاق" })).toBeInTheDocument();
  });

  it("closes on Escape", () => {
    const onClose = vi.fn();
    renderIn(
      "en",
      <Dialog open title="Discard your changes?" onClose={onClose}>
        <p>Body</p>
      </Dialog>,
    );
    fireEvent(screen.getByRole("dialog"), new Event("cancel", { cancelable: true }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes from its close button", async () => {
    const onClose = vi.fn();
    renderIn(
      "en",
      <Dialog open title="Discard your changes?" onClose={onClose}>
        <p>Body</p>
      </Dialog>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("is not shown while closed", () => {
    renderIn(
      "en",
      <Dialog open={false} title="Discard your changes?" onClose={vi.fn()}>
        <p>Body</p>
      </Dialog>,
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
