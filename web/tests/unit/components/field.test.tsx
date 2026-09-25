// @vitest-environment jsdom
import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SelectField, TextField } from "@/components/field/field";

import { renderIn } from "./render";

describe("TextField", () => {
  it("is labelled, and described by its helper text", () => {
    renderIn("en", <TextField label="Job title" help="Candidates see it." defaultValue="" />);
    const input = screen.getByRole("textbox", { name: "Job title" });
    expect(input).toHaveAccessibleDescription("Candidates see it.");
    expect(input).not.toHaveAttribute("aria-invalid");
  });

  it("replaces the helper text with the error, and marks the field invalid", () => {
    renderIn(
      "en",
      <TextField
        label="Job title"
        help="Candidates see it."
        error="A job title is needed to save the job."
        defaultValue=""
      />,
    );
    const input = screen.getByRole("textbox", { name: "Job title" });
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("A job title is needed to save the job.");
    expect(screen.queryByText("Candidates see it.")).toBeNull();
  });

  it("while loading, says what it is doing in place of the helper", () => {
    renderIn(
      "en",
      <TextField
        label="Job title"
        help="Candidates see it."
        loading="Checking for a job with the same name…"
        defaultValue=""
      />,
    );
    const input = screen.getByRole("textbox", { name: "Job title" });
    expect(input).toHaveAttribute("aria-busy", "true");
    expect(input).toHaveAccessibleDescription("Checking for a job with the same name…");
  });

  it("marks a value the system proposed, read after the field's name", () => {
    renderIn(
      "ar",
      <TextField label="الموقع" help="اقترحناه من وصف الوظيفة." suggested defaultValue="القاهرة" />,
    );
    const input = screen.getByRole("textbox", { name: "الموقع" });
    expect(input).toHaveValue("القاهرة");
    expect(input).toHaveAccessibleDescription("مقترح اقترحناه من وصف الوظيفة.");
  });
});

describe("SelectField", () => {
  const options = [
    { value: "ar", label: "Arabic" },
    { value: "en", label: "English" },
  ];

  it("offers a prompt until something is chosen", () => {
    renderIn("en", <SelectField label="Required language" options={options} defaultValue="" />);
    const select = screen.getByRole("combobox", { name: "Required language" });
    expect(select).toHaveValue("");
    expect(screen.getByRole("option", { name: "Choose…" })).toBeDisabled();
  });

  it("shows its error the same way a text field does", () => {
    renderIn(
      "en",
      <SelectField
        label="Required language"
        options={options}
        error="Choose at least one language."
        defaultValue=""
      />,
    );
    const select = screen.getByRole("combobox", { name: "Required language" });
    expect(select).toHaveAttribute("aria-invalid", "true");
    expect(select).toHaveAccessibleDescription("Choose at least one language.");
  });
});
