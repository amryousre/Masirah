import { describe, expect, it } from "vitest";

import { DEFAULT_WEIGHTS, jobDraftFrom, LIMITS } from "@/lib/domain/job-draft";

// What a job needs before it can be saved (T059, FR-001), read from the submitted form. The
// form is untrusted input: every value is trimmed, bounded and checked here, on the server.
function form(fields: Record<string, string | string[]>): FormData {
  const data = new FormData();
  for (const [name, value] of Object.entries(fields)) {
    for (const item of Array.isArray(value) ? value : [value]) data.append(name, item);
  }
  return data;
}

describe("a job draft", () => {
  it("needs only a title", () => {
    const result = jobDraftFrom(form({ title: "  Senior Accountant  " }));
    expect(result).toEqual({
      ok: true,
      draft: {
        title: "Senior Accountant",
        description: null,
        requiredSkills: [],
        preferredSkills: [],
        minimumExperienceYears: null,
        location: null,
        languageRequirement: null,
      },
    });
  });

  it("keeps everything a recruiter filled in", () => {
    const result = jobDraftFrom(
      form({
        title: "Senior Front-end Developer",
        description: "Build dashboards for the payments app.",
        requiredSkills: ["React", "TypeScript"],
        preferredSkills: ["Next.js"],
        minimumExperienceYears: "3",
        location: "Cairo",
        languageRequirement: "both",
      }),
    );
    expect(result.ok && result.draft).toEqual({
      title: "Senior Front-end Developer",
      description: "Build dashboards for the payments app.",
      requiredSkills: ["React", "TypeScript"],
      preferredSkills: ["Next.js"],
      minimumExperienceYears: 3,
      location: "Cairo",
      languageRequirement: "both",
    });
  });

  it("refuses a job without a title", () => {
    expect(jobDraftFrom(form({ title: "   " }))).toEqual({
      ok: false,
      errors: { title: "missing" },
    });
  });

  it("refuses a title longer than a title", () => {
    const long = "x".repeat(LIMITS.title + 1);
    expect(jobDraftFrom(form({ title: long }))).toEqual({
      ok: false,
      errors: { title: "tooLong" },
    });
  });

  it("drops empty and repeated skills, ignoring case", () => {
    const result = jobDraftFrom(
      form({ title: "Dev", requiredSkills: ["React", " react ", "", "SQL"] }),
    );
    expect(result.ok && result.draft.requiredSkills).toEqual(["React", "SQL"]);
  });

  it("leaves a skill out of preferred when it is already required", () => {
    const result = jobDraftFrom(
      form({ title: "Dev", requiredSkills: ["React"], preferredSkills: ["react", "Jest"] }),
    );
    expect(result.ok && result.draft.preferredSkills).toEqual(["Jest"]);
  });

  it("refuses more skills than a job can sensibly list", () => {
    const many = Array.from({ length: LIMITS.skills + 1 }, (_, n) => `Skill ${String(n)}`);
    expect(jobDraftFrom(form({ title: "Dev", requiredSkills: many }))).toEqual({
      ok: false,
      errors: { requiredSkills: "tooMany" },
    });
  });

  it.each(["-1", "51", "2.5", "three"])("refuses %s years of experience", (years) => {
    expect(jobDraftFrom(form({ title: "Dev", minimumExperienceYears: years }))).toEqual({
      ok: false,
      errors: { minimumExperienceYears: "invalid" },
    });
  });

  it("refuses a language requirement it does not offer", () => {
    expect(jobDraftFrom(form({ title: "Dev", languageRequirement: "fr" }))).toEqual({
      ok: false,
      errors: { languageRequirement: "invalid" },
    });
  });

  it("reports every problem at once", () => {
    const result = jobDraftFrom(form({ title: "", minimumExperienceYears: "x" }));
    expect(result).toEqual({
      ok: false,
      errors: { title: "missing", minimumExperienceYears: "invalid" },
    });
  });
});

describe("the default weights", () => {
  it("are the pipeline's, totalling 100", () => {
    // pipeline/src/masirah_pipeline/domain/scoring.py DEFAULT_WEIGHTS
    expect(DEFAULT_WEIGHTS).toEqual({
      skills_match: 30,
      experience_relevance: 25,
      education: 15,
      tenure_stability: 10,
      language: 10,
      location: 10,
    });
    expect(Object.values(DEFAULT_WEIGHTS).reduce((sum, weight) => sum + weight, 0)).toBe(100);
  });
});
