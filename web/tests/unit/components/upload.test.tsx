// @vitest-environment jsdom
import { createEvent, fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DropZone, type UploadItem, UploadList } from "@/components/upload/upload";

import { renderIn } from "./render";

const items: UploadItem[] = [
  { id: "1", fileName: "CV_Sara_Nabil.pdf", bytes: 240 * 1024, status: { kind: "queued" } },
  {
    id: "2",
    fileName: "Ahmed_Samir_CV.docx",
    bytes: 1.2 * 1024 * 1024,
    status: { kind: "uploading", percent: 64 },
  },
  {
    id: "3",
    fileName: "CV_final_v3.pdf",
    bytes: 1.1 * 1024 * 1024,
    status: { kind: "failed", reason: "Couldn’t upload. Check your connection and try again." },
  },
  {
    id: "4",
    fileName: "Lebenslauf_Weber.pdf",
    bytes: 520 * 1024,
    status: { kind: "unsupported", language: "German" },
  },
];

describe("UploadList", () => {
  it("shows each file's type, size and state in words", () => {
    renderIn("en", <UploadList items={items} />);
    expect(screen.getByText("CV_Sara_Nabil.pdf")).toBeInTheDocument();
    expect(screen.getAllByText("PDF")).toHaveLength(3);
    expect(screen.getByText("DOCX")).toBeInTheDocument();
    expect(screen.getByText("240 KB")).toBeInTheDocument();
    expect(screen.getByText("1.2 MB")).toBeInTheDocument();
    expect(screen.getByText("Uploading · 64%")).toBeInTheDocument();
    // The reason is the whole sentence: a file that was refused or never sent was not "read".
    expect(
      screen.getByText("Couldn’t upload. Check your connection and try again."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Unsupported language (German). The file is kept and not scored."),
    ).toBeInTheDocument();
  });

  it("counts every state, so nothing is silently lost", () => {
    renderIn("en", <UploadList items={items} />);
    expect(
      screen.getByText(
        "4 files · 0 parsed · 0 need review · 1 failed · 1 unsupported language · 2 in progress",
      ),
    ).toBeInTheDocument();
  });

  it("offers the one action that fixes a file", async () => {
    const onAction = vi.fn();
    const locked: UploadItem = {
      id: "3",
      fileName: "CV_final_v3.pdf",
      bytes: 1.1 * 1024 * 1024,
      status: { kind: "failed", reason: "the file is password-protected" },
      action: { label: "Replace file", onAction },
    };
    renderIn("en", <UploadList items={[locked]} />);
    await userEvent.click(screen.getByRole("button", { name: "Replace file" }));
    expect(onAction).toHaveBeenCalledTimes(1);
  });
});

describe("DropZone", () => {
  it("says how many files it takes and which formats", () => {
    renderIn("en", <DropZone job="Senior Front-end Developer" onFiles={vi.fn()} />);
    expect(screen.getByText("Drag up to 25 files here, or choose files")).toBeInTheDocument();
    expect(screen.getByLabelText("Drag up to 25 files here, or choose files")).toHaveAttribute(
      "type",
      "file",
    );
  });

  it("says what will happen while files are dragged over it", () => {
    renderIn("ar", <DropZone job="مطوّر واجهات أمامية أول" onFiles={vi.fn()} />);
    const zone = screen.getByTestId("drop-zone");
    const dragEnter = createEvent.dragEnter(zone);
    Object.defineProperty(dragEnter, "dataTransfer", {
      value: { items: { length: 12 }, types: ["Files"] },
    });
    fireEvent(zone, dragEnter);
    expect(screen.getByText("أفلت 12 ملفًا لرفعها")).toBeInTheDocument();
    expect(screen.getByText("ستُضاف إلى «مطوّر واجهات أمامية أول».")).toBeInTheDocument();
  });

  it("hands dropped files over", () => {
    const onFiles = vi.fn();
    renderIn("en", <DropZone job="Accountant" onFiles={onFiles} />);
    const file = new File(["%PDF"], "cv.pdf", { type: "application/pdf" });
    const zone = screen.getByTestId("drop-zone");
    const drop = createEvent.drop(zone);
    Object.defineProperty(drop, "dataTransfer", { value: { files: [file], items: { length: 1 } } });
    fireEvent(zone, drop);
    expect(onFiles).toHaveBeenCalledWith([file]);
  });

  it("takes at most its maximum at once, and says how many it left out", () => {
    const onFiles = vi.fn();
    renderIn("en", <DropZone job="Accountant" onFiles={onFiles} max={3} />);
    const files = ["a", "b", "c", "d", "e"].map(
      (name) => new File(["%PDF"], `${name}.pdf`, { type: "application/pdf" }),
    );
    const zone = screen.getByTestId("drop-zone");
    const drop = createEvent.drop(zone);
    Object.defineProperty(drop, "dataTransfer", { value: { files, items: { length: 5 } } });
    fireEvent(zone, drop);
    expect(onFiles).toHaveBeenCalledWith(files.slice(0, 3));
    expect(screen.getByRole("status")).toHaveTextContent(
      "2 files weren't added: you can upload up to 3 at a time.",
    );
  });

  it("says in Arabic how many files it left out", async () => {
    renderIn("ar", <DropZone job="محاسب" onFiles={vi.fn()} max={25} />);
    const files = Array.from(
      { length: 27 },
      (_, index) => new File(["%PDF"], `${String(index)}.pdf`, { type: "application/pdf" }),
    );
    await userEvent.upload(screen.getByLabelText("اسحب حتى 25 ملفًا هنا، أو اختر ملفات"), files);
    expect(screen.getByRole("status")).toHaveTextContent(
      "لم يُضف ملفان: يمكن رفع 25 ملفًا في كل مرة.",
    );
  });

  it("at the limit, stops taking files and says when it renews", () => {
    renderIn(
      "en",
      <DropZone
        job="Accountant"
        onFiles={vi.fn()}
        limitReached={{ limit: 300, renewsOn: "1 Oct" }}
      />,
    );
    expect(
      screen.getByText("Processing is paused: you've reached this month's limit of 300 CVs"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Everything you uploaded is still here. The limit renews on 1 Oct."),
    ).toBeInTheDocument();
    expect(screen.getByTestId("drop-zone").querySelector("input")).toBeDisabled();
  });

  it("paused by spending with CVs left, it names no count it has not reached", () => {
    renderIn(
      "en",
      <DropZone
        job="Accountant"
        onFiles={vi.fn()}
        limitReached={{ limit: null, renewsOn: "1 Oct" }}
      />,
    );
    expect(screen.getByText("Processing is paused for this month")).toBeInTheDocument();
    expect(screen.queryByText(/limit of/)).toBeNull();
    expect(
      screen.getByText("Everything you uploaded is still here. The limit renews on 1 Oct."),
    ).toBeInTheDocument();
    expect(screen.getByTestId("drop-zone").querySelector("input")).toBeDisabled();
  });
});
