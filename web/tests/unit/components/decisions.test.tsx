// @vitest-environment jsdom
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { AdvisoryNotice } from "@/components/advisory-notice/advisory-notice";
import { RejectCandidate } from "@/components/reject-candidate/reject-candidate";

import { renderIn } from "./render";

beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
    this.removeAttribute("open");
  };
});

describe("AdvisoryNotice", () => {
  it("says the score is advice and the decision is the reader's", () => {
    renderIn("en", <AdvisoryNotice decided={false} />);
    expect(
      screen.getByText(
        "No decision yet. The score is advice; the decision is yours and is recorded under your name.",
      ),
    ).toBeInTheDocument();
  });

  it("stays once a decision is made, without asking again", () => {
    renderIn("ar", <AdvisoryNotice decided />);
    expect(screen.getByText("الدرجة رأي استشاري؛ القرار لك ويُسجَّل باسمك.")).toBeInTheDocument();
  });
});

describe("RejectCandidate", () => {
  const renderControl = (onReject = vi.fn(() => Promise.resolve(true))) => {
    renderIn(
      "en",
      <RejectCandidate candidate="Omar Hassan" actor="nourhan@example.test" onReject={onReject} />,
    );
    return onReject;
  };

  it("opens a confirmation that says what follows, instead of rejecting at once", async () => {
    const onReject = renderControl();
    await userEvent.click(screen.getByRole("button", { name: "Reject candidate…" }));
    expect(screen.getByRole("dialog", { name: "Reject Omar Hassan?" })).toBeInTheDocument();
    expect(screen.getByText(/You'll be recorded as the person who decided/)).toBeInTheDocument();
    expect(onReject).not.toHaveBeenCalled();
  });

  it("records only with a reason chosen, and offers no notice the product cannot send", async () => {
    const onReject = renderControl();
    await userEvent.click(screen.getByRole("button", { name: "Reject candidate…" }));
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reject candidate" })).toBeDisabled();
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Reason (required)" }),
      "Required skills missing",
    );
    await userEvent.click(screen.getByRole("button", { name: "Reject candidate" }));
    expect(onReject).toHaveBeenCalledWith("skills");
  });

  it("says inside the confirmation when the rejection could not be recorded", async () => {
    renderIn(
      "en",
      <RejectCandidate
        candidate="Omar Hassan"
        actor="nourhan@example.test"
        error="The decision could not be recorded. Try again."
        onReject={vi.fn(() => Promise.resolve(false))}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Reject candidate…" }));
    const dialog = screen.getByRole("dialog", { name: "Reject Omar Hassan?" });
    expect(
      within(dialog).getByText("The decision could not be recorded. Try again."),
    ).toBeInTheDocument();
  });

  it("names who will be recorded", async () => {
    renderControl();
    await userEvent.click(screen.getByRole("button", { name: "Reject candidate…" }));
    expect(
      screen.getByText(/Will be recorded: \u2068nourhan@example.test\u2069/),
    ).toBeInTheDocument();
  });
});
