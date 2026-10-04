import { describe, expect, it } from "vitest";

import { placeInRanking, profileRows, scoreParts, summaryLines } from "@/lib/domain/candidate";

// A candidate's own page (T065, T066): the score as points earned out of each weight, the
// summary as its lines, and where the candidate sits in the job's ranking.

const WEIGHTS = {
  skills_match: 30,
  experience_relevance: 25,
  education: 15,
  tenure_stability: 10,
  language: 10,
  location: 10,
};

const rated = (ratings: Record<string, number>) =>
  Object.fromEntries(
    Object.entries(ratings).map(([name, rating]) => [name, { rating, evidence: `${name} notes` }]),
  );

describe("scoreParts", () => {
  it("gives each component the points it earned out of its weight, with its evidence", () => {
    const parts = scoreParts(
      rated({
        skills_match: 70,
        experience_relevance: 80,
        education: 100,
        tenure_stability: 50,
        language: 100,
        location: 0,
      }),
      WEIGHTS,
    );
    expect(parts).toEqual([
      { key: "skills", earned: 21, weight: 30, evidence: "skills_match notes" },
      { key: "experience", earned: 20, weight: 25, evidence: "experience_relevance notes" },
      { key: "education", earned: 15, weight: 15, evidence: "education notes" },
      { key: "tenure", earned: 5, weight: 10, evidence: "tenure_stability notes" },
      { key: "language", earned: 10, weight: 10, evidence: "language notes" },
      { key: "location", earned: 0, weight: 10, evidence: "location notes" },
    ]);
  });

  it("rounds a part's points half up, as the total is", () => {
    const parts = scoreParts(
      rated({
        skills_match: 75,
        experience_relevance: 50,
        education: 50,
        tenure_stability: 50,
        language: 50,
        location: 50,
      }),
      { ...WEIGHTS, skills_match: 30 },
    );
    // 75 × 30 / 100 = 22.5, which shows as 23.
    expect(parts?.[0]?.earned).toBe(23);
    // 50 × 25 / 100 = 12.5, which shows as 13.
    expect(parts?.[1]?.earned).toBe(13);
  });

  it("refuses components it cannot read rather than showing invented points", () => {
    expect(scoreParts({}, WEIGHTS)).toBeNull();
    expect(scoreParts(null, WEIGHTS)).toBeNull();
    const missingRating = rated({
      skills_match: 70,
      experience_relevance: 80,
      education: 100,
      tenure_stability: 50,
      language: 100,
    });
    expect(scoreParts(missingRating, WEIGHTS)).toBeNull();
    expect(
      scoreParts({ ...missingRating, location: { rating: "high", evidence: "" } }, WEIGHTS),
    ).toBeNull();
    expect(scoreParts({ ...missingRating, location: { rating: 50, evidence: "" } }, {})).toBeNull();
  });
});

describe("summaryLines", () => {
  it("splits the stored summary into its lines, dropping blank ones", () => {
    expect(summaryLines("Six years at Nile Pharma.\n\nSAP daily.\n")).toEqual([
      "Six years at Nile Pharma.",
      "SAP daily.",
    ]);
  });
});

describe("profileRows", () => {
  const profile = {
    name: "Mohamed Abdallah",
    emails: ["mohamed@example.test"],
    phones: ["+201005552841"],
    location: "Nasr City, Cairo",
    years_of_experience: 6,
    employment: [
      { employer: "Vodafone Egypt", title: "Front-end Engineer", start: "2020", end: "2024" },
      { employer: "Raya IT", title: null, start: "2018", end: null },
    ],
    education: [
      {
        institution: "Cairo University",
        qualification: "B.Sc. Computer Engineering",
        start: null,
        end: "2018",
      },
    ],
    skills: ["React", "TypeScript"],
    languages: [{ language: "Arabic", level: "native" }],
    certifications: [],
  };

  it("lists every extracted field in reading order, each entry as one line", () => {
    expect(profileRows(profile)).toEqual([
      { field: "name", values: ["Mohamed Abdallah"] },
      { field: "emails", values: ["mohamed@example.test"] },
      { field: "phones", values: ["+201005552841"] },
      { field: "location", values: ["Nasr City, Cairo"] },
      { field: "experience", values: ["6"] },
      {
        field: "employment",
        values: ["Front-end Engineer · Vodafone Egypt · 2020 – 2024", "Raya IT · 2018"],
      },
      { field: "education", values: ["B.Sc. Computer Engineering · Cairo University · 2018"] },
      { field: "skills", values: ["React, TypeScript"] },
      { field: "languages", values: ["Arabic · native"] },
      { field: "certifications", values: [] },
    ]);
  });

  it("shows a field the CV did not give as empty, never leaves it out", () => {
    const rows = profileRows({ ...profile, location: null, years_of_experience: null });
    expect(rows?.find((row) => row.field === "location")).toEqual({
      field: "location",
      values: [],
    });
    expect(rows?.find((row) => row.field === "experience")?.values).toEqual([]);
  });

  it("reads nothing from a profile that is not one", () => {
    expect(profileRows(null)).toBeNull();
    expect(profileRows("profile")).toBeNull();
  });
});

describe("placeInRanking", () => {
  const ranking = [
    { candidateId: "c-a", score: 86 },
    { candidateId: "c-b", score: 81 },
    { candidateId: "c-c", score: 78 },
  ];

  it("gives the rank, the count and the candidates either side", () => {
    expect(placeInRanking(ranking, "c-b")).toEqual({
      rank: 2,
      of: 3,
      previous: "c-a",
      next: "c-c",
    });
  });

  it("has no neighbour beyond either end", () => {
    expect(placeInRanking(ranking, "c-a")).toMatchObject({ rank: 1, previous: null, next: "c-b" });
    expect(placeInRanking(ranking, "c-c")).toMatchObject({ rank: 3, previous: "c-b", next: null });
  });

  it("has no place for a candidate not ranked yet", () => {
    expect(placeInRanking(ranking, "c-z")).toBeNull();
  });
});
