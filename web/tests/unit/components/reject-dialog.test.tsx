// @vitest-environment jsdom
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { RejectDialog } from "@/components/reject-dialog/reject-dialog";

import { renderIn } from "./render";

beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
    this.removeAttribute("open");
  };
});

const reasons = [
  { value: "skills", label: "Required skills are missing" },
  { value: "experience", label: "Less experience than required" },
];

function renderDialog(onConfirm = vi.fn()) {
  renderIn(
    "en",
    <RejectDialog
      open
      candidate="Mohamed Abdallah"
      actor="Nourhan Saeed"
      when="today 14:32"
      reasons={reasons}
      onCancel={vi.fn()}
      onConfirm={onConfirm}
    />,
  );
  return onConfirm;
}

describe("RejectDialog", () => {
  it("names the candidate and who will be recorded as deciding", () => {
    renderDialog();
    expect(screen.getByRole("dialog", { name: "Reject Mohamed Abdallah?" })).toBeVisible();
    expect(screen.getByText("Will be recorded: Nourhan Saeed · today 14:32")).toBeInTheDocument();
  });

  it("will not reject until a reason is chosen", async () => {
    const onConfirm = renderDialog();
    const reject = screen.getByRole("button", { name: "Reject candidate" });
    expect(reject).toBeDisabled();
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Reason (required)" }),
      "skills",
    );
    expect(reject).toBeEnabled();
    await userEvent.click(reject);
    expect(onConfirm).toHaveBeenCalledWith({ reason: "skills", notify: true });
  });

  it("lets the notice to the candidate be switched off", async () => {
    const onConfirm = renderDialog();
    await userEvent.selectOptions(screen.getByRole("combobox"), "experience");
    await userEvent.click(
      screen.getByRole("checkbox", { name: "Send the candidate a rejection notice after 3 days" }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Reject candidate" }));
    expect(onConfirm).toHaveBeenCalledWith({ reason: "experience", notify: false });
  });
});
