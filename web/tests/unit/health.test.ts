import { describe, expect, it } from "vitest";

import {
  BACKLOG_SECONDS,
  type HealthFigures,
  SILENT_SECONDS,
  serviceHealth,
} from "@/lib/domain/health";

// What /api/health reports from the queue and the worker's heartbeat (T030). A stopped worker
// fails nothing: messages simply wait. These two signals are how that gets noticed.
const healthy: HealthFigures = {
  queueDepth: 2,
  oldestMessageSeconds: 30,
  heartbeatAgeSeconds: 4,
};

describe("service health", () => {
  it("is ok while the worker beats and nothing waits long", () => {
    expect(serviceHealth(healthy)).toEqual({ status: "ok", problems: [] });
  });

  it("is ok with an empty queue", () => {
    expect(serviceHealth({ ...healthy, queueDepth: 0, oldestMessageSeconds: null })).toEqual({
      status: "ok",
      problems: [],
    });
  });

  it("is degraded when the worker has gone quiet", () => {
    const quiet = { ...healthy, heartbeatAgeSeconds: SILENT_SECONDS + 1 };
    expect(serviceHealth(quiet)).toEqual({ status: "degraded", problems: ["worker-silent"] });
  });

  it("counts a worker silent for exactly the threshold as silent", () => {
    const atThreshold = { ...healthy, heartbeatAgeSeconds: SILENT_SECONDS };
    expect(serviceHealth(atThreshold).problems).toEqual(["worker-silent"]);
  });

  it("is degraded when no worker has ever beaten", () => {
    expect(serviceHealth({ ...healthy, heartbeatAgeSeconds: null }).problems).toEqual([
      "worker-silent",
    ]);
  });

  it("is degraded when a message has waited too long, even with a worker beating", () => {
    const stuck = { ...healthy, oldestMessageSeconds: BACKLOG_SECONDS + 1 };
    expect(serviceHealth(stuck)).toEqual({ status: "degraded", problems: ["queue-backlog"] });
  });

  it("names every problem at once", () => {
    const both = {
      queueDepth: 40,
      oldestMessageSeconds: BACKLOG_SECONDS + 1,
      heartbeatAgeSeconds: null,
    };
    expect(serviceHealth(both).problems).toEqual(["worker-silent", "queue-backlog"]);
  });

  it("allows the worker a long batch before calling it silent", () => {
    // The worker beats after every message, and one CV's model calls can take a few minutes.
    expect(SILENT_SECONDS).toBeGreaterThanOrEqual(5 * 60);
  });
});
