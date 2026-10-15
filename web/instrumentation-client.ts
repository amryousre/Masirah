import * as Sentry from "@sentry/nextjs";

import { sentryOptions } from "@/lib/adapters/telemetry";

// Error tracking in the browser (T031): errors only, with no tracing or session replay.
Sentry.init(sentryOptions());
