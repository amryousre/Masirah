import { describe, expect, it } from "vitest";

import { nameNormalised } from "@/lib/domain/names";

import examples from "./fixtures/name-examples.json";

// The web folds a search the way the worker folded each candidate's name (T069), so a search for
// Mohamed finds Mohammed, Muhammad and محمد. The examples and their forms come from the pipeline's
// own function (pipeline/tools/export_name_spellings.py); the port must give every one the same.

describe("nameNormalised", () => {
  it.each(examples as [string, string][])("folds %j as the worker does", (name, form) => {
    expect(nameNormalised(name)).toBe(form);
  });

  it("keeps different names apart", () => {
    expect(nameNormalised("Mohamed")).not.toBe(nameNormalised("Mahmoud"));
    expect(nameNormalised("Hassan")).not.toBe(nameNormalised("Hussein"));
    expect(nameNormalised("Amr")).not.toBe(nameNormalised("Omar"));
  });
});
