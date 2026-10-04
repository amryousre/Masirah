// Whether CV processing is flowing (T030). The worker records a heartbeat before each batch and
// after every message; the queue says how long the oldest message has waited. A stopped worker
// fails nothing, so these two figures are what make it visible.

/** The worker beats after every message; one CV's model calls can take a few minutes. */
export const SILENT_SECONDS = 10 * 60;

/** Longer than this, an uploaded CV has waited past what a recruiter would accept. */
export const BACKLOG_SECONDS = 30 * 60;

export interface HealthFigures {
  queueDepth: number;
  /** Null when the queue is empty. */
  oldestMessageSeconds: number | null;
  /** Null when no worker has ever recorded a heartbeat. */
  heartbeatAgeSeconds: number | null;
}

export type HealthProblem = "worker-silent" | "queue-backlog";

export interface ServiceHealth {
  status: "ok" | "degraded";
  problems: HealthProblem[];
}

export function serviceHealth(figures: HealthFigures): ServiceHealth {
  const problems: HealthProblem[] = [];
  if (figures.heartbeatAgeSeconds === null || figures.heartbeatAgeSeconds > SILENT_SECONDS) {
    problems.push("worker-silent");
  }
  if (figures.oldestMessageSeconds !== null && figures.oldestMessageSeconds > BACKLOG_SECONDS) {
    problems.push("queue-backlog");
  }
  return { status: problems.length === 0 ? "ok" : "degraded", problems };
}
