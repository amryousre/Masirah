import { captureException } from "@sentry/nextjs";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { SupabaseClient } from "@/lib/adapters/supabase";
import { joinWaitlist } from "@/lib/adapters/waitlist";

vi.mock("@sentry/nextjs", () => ({ captureException: vi.fn() }));

// What the waitlist tells the visitor and the operator for each answer from join_waitlist
// (migration 0027, T031). The hourly limit is the list holding off a flood, as designed: it is
// logged, never sent to Sentry, so a flood cannot spend the quota real errors need.

function answering(code: string | null): SupabaseClient {
  const error = code === null ? null : { code, message: `refused with ${code}` };
  return { rpc: vi.fn(() => Promise.resolve({ error })) } as unknown as SupabaseClient;
}

describe("joinWaitlist", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.mocked(captureException).mockClear();
  });

  it("joins", async () => {
    expect(await joinWaitlist(answering(null), "a@b.co", "en")).toBe("joined");
  });

  it("answers an address the database refused as invalid", async () => {
    expect(await joinWaitlist(answering("22023"), "a@b", "en")).toBe("invalid");
    expect(captureException).not.toHaveBeenCalled();
  });

  it("logs the hourly limit as a warning and reports nothing", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    expect(await joinWaitlist(answering("53400"), "a@b.co", "ar")).toBe("unavailable");
    expect(warn).toHaveBeenCalledOnce();
    expect(captureException).not.toHaveBeenCalled();
  });

  it("reports any other failure", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(await joinWaitlist(answering("42501"), "a@b.co", "en")).toBe("unavailable");
    expect(captureException).toHaveBeenCalledOnce();
  });
});
