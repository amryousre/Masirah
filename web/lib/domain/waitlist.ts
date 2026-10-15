// The landing page's waitlist (migration 0027): a company gives a work email and nothing else. This
// is the page's check, so it can answer in its own language; public.join_waitlist checks again.

const LONGEST = 254;
const ADDRESS = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

/** The address as the waitlist keeps it, trimmed and lowercased, or null when it isn't one. */
export function waitlistEmail(raw: string): string | null {
  const address = raw.trim().toLowerCase();
  if (address.length === 0 || address.length > LONGEST || !ADDRESS.test(address)) return null;
  return address;
}
