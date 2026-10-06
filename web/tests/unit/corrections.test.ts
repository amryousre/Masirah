import { describe, expect, it } from "vitest";

import {
  correctedProfile,
  correctedRows,
  correctionsFromForm,
  correctionsOf,
} from "@/lib/domain/corrections";

// Correcting an extracted field (T082, T083, FR-010): the form a recruiter fills in, what is sent
// to correct_profile, and how a corrected value is shown beside the one the machine read.

const EXTRACTED = {
  name: "Mona Abdalla",
  emails: ["mona@example.com"],
  phones: ["+201000000101"],
  location: "Cairo",
  years_of_experience: null,
  employment: [{ employer: "Nile Pharma", title: "Accountant", start: "2019-03", end: "present" }],
  education: [],
  skills: ["Excel", "SAP"],
  languages: [{ language: "Arabic", level: "Native" }],
  certifications: [],
};

const form = (fields: Record<string, string>): [string, string][] => Object.entries(fields);

const FILLED = {
  name: "Mona Abdalla",
  emails: "mona@example.com",
  phones: "+201000000101",
  location: "Cairo",
  years_of_experience: "",
  "employment.0.title": "Accountant",
  "employment.0.employer": "Nile Pharma",
  "employment.0.start": "2019-03",
  "employment.0.end": "present",
  skills: "Excel\nSAP",
  "languages.0.language": "Arabic",
  "languages.0.level": "Native",
};

describe("correctionsFromForm", () => {
  it("sends nothing when nothing was changed", () => {
    expect(correctionsFromForm(form(FILLED), EXTRACTED, {})).toEqual({ ok: true, corrections: {} });
  });

  it("sends only the fields that changed, in the shape extraction gives them", () => {
    const result = correctionsFromForm(
      form({
        ...FILLED,
        name: "  Mona Abdallah ",
        skills: "Excel\n\nSAP\nOracle  ",
        years_of_experience: "6",
        "employment.0.start": "2018-03",
      }),
      EXTRACTED,
      {},
    );
    expect(result).toEqual({
      ok: true,
      corrections: {
        name: "Mona Abdallah",
        years_of_experience: 6,
        employment: [
          { title: "Accountant", employer: "Nile Pharma", start: "2018-03", end: "present" },
        ],
        skills: ["Excel", "SAP", "Oracle"],
      },
    });
  });

  it("adds and removes whole entries", () => {
    const result = correctionsFromForm(
      form({
        ...FILLED,
        "employment.0.title": "",
        "employment.0.employer": "",
        "employment.0.start": "",
        "employment.0.end": "",
        "education.3.qualification": "B.Com",
        "education.3.institution": "Cairo University",
        "education.3.start": "",
        "education.3.end": "2017",
      }),
      EXTRACTED,
      {},
    );
    expect(result).toEqual({
      ok: true,
      corrections: {
        employment: [],
        education: [
          { qualification: "B.Com", institution: "Cairo University", start: null, end: "2017" },
        ],
      },
    });
  });

  it("restores an extracted value by sending it back", () => {
    const corrections = correctionsOf({
      location: { value: "Giza", by: "u1", at: "2026-10-06T10:00:00Z" },
    });
    expect(correctionsFromForm(form(FILLED), EXTRACTED, corrections)).toEqual({
      ok: true,
      corrections: { location: "Cairo" },
    });
  });

  it("names each field it cannot accept", () => {
    const result = correctionsFromForm(
      form({
        ...FILLED,
        emails: "mona@example.com\nnot an email",
        years_of_experience: "six",
        "employment.0.start": "March 2019",
      }),
      EXTRACTED,
      {},
    );
    expect(result).toEqual({
      ok: false,
      errors: { emails: "email", years_of_experience: "years", employment: "date" },
    });
  });

  it("reads a current job written in Arabic as present", () => {
    const result = correctionsFromForm(
      form({ ...FILLED, "employment.0.start": "2018-03", "employment.0.end": " حتى الآن " }),
      EXTRACTED,
      {},
    );
    expect(result).toEqual({
      ok: true,
      corrections: {
        employment: [
          { title: "Accountant", employer: "Nile Pharma", start: "2018-03", end: "present" },
        ],
      },
    });
  });

  it("ignores fields it does not know", () => {
    expect(correctionsFromForm(form({ ...FILLED, salary: "20000" }), EXTRACTED, {})).toEqual({
      ok: true,
      corrections: {},
    });
  });
});

describe("correctionsOf", () => {
  it("keeps only well-formed corrections of known fields", () => {
    expect(
      correctionsOf({
        name: { value: "Mona", by: "u1", at: "2026-10-06T10:00:00Z" },
        salary: { value: 1, by: "u1", at: "2026-10-06T10:00:00Z" },
        location: "Giza",
      }),
    ).toEqual({ name: { value: "Mona", by: "u1", at: "2026-10-06T10:00:00Z" } });
    expect(correctionsOf(null)).toEqual({});
  });
});

describe("correctedProfile and correctedRows", () => {
  const corrections = correctionsOf({
    name: { value: "Mona Abdallah", by: "u1", at: "2026-10-06T10:00:00Z" },
    skills: { value: ["Excel", "SAP", "Oracle"], by: "u2", at: "2026-10-06T11:00:00Z" },
  });

  it("puts each correction in place of the extracted value", () => {
    expect(correctedProfile(EXTRACTED, corrections)).toMatchObject({
      name: "Mona Abdallah",
      skills: ["Excel", "SAP", "Oracle"],
      location: "Cairo",
    });
  });

  it("marks a corrected row with what was extracted, who and when", () => {
    const rows = correctedRows(EXTRACTED, corrections);
    expect(rows?.find((row) => row.field === "name")).toEqual({
      field: "name",
      values: ["Mona Abdallah"],
      corrected: { extracted: ["Mona Abdalla"], by: "u1", at: "2026-10-06T10:00:00Z" },
    });
    expect(rows?.find((row) => row.field === "skills")?.corrected?.extracted).toEqual([
      "Excel, SAP",
    ]);
    expect(rows?.find((row) => row.field === "location")).toEqual({
      field: "location",
      values: ["Cairo"],
    });
  });
});
