import type ar from "../messages/ar.json";
import type { routing } from "./routing";

// Arabic is the source of truth for message keys; tests/unit/messages.test.ts holds English to it.
declare module "next-intl" {
  interface AppConfig {
    Locale: (typeof routing.locales)[number];
    Messages: typeof ar;
  }
}
