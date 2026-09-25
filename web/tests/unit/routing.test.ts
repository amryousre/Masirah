import { describe, expect, it } from "vitest";

import { direction, routing } from "@/i18n/routing";

describe("locale routing", () => {
  it("serves Arabic first and English second", () => {
    expect(routing.locales).toEqual(["ar", "en"]);
    expect(routing.defaultLocale).toBe("ar");
  });

  it("always shows the locale in the path, so a shared link opens in its language", () => {
    expect(routing.localePrefix).toBe("always");
  });

  it("decides the direction from the locale", () => {
    expect(direction("ar")).toBe("rtl");
    expect(direction("en")).toBe("ltr");
  });
});
