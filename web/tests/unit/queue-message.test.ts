import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import {
  QUEUES,
  SCHEMA_VERSION,
  cvProcessingMessage,
  cvRescoringMessage,
  type CvProcessingMessage,
  type QueueMessage,
} from "../../lib/ports/queue-message";

// The examples file is shared with the pipeline tests, so the producer built here and the
// consumer in the worker are held to one definition of the contract.
interface Example<T> {
  name: string;
  message: T;
}

const examples = JSON.parse(
  readFileSync(
    path.resolve(
      import.meta.dirname,
      "../../../specs/001-phase1-core-screening/contracts/queue-message.examples.json",
    ),
    "utf8",
  ),
) as { valid: Example<QueueMessage>[]; malformed: Example<CvProcessingMessage>[] };

function rebuild(message: QueueMessage): QueueMessage {
  const enqueuedAt = new Date(message.enqueued_at);
  if (message.job_type === QUEUES.cvProcessing) {
    return cvProcessingMessage({
      organisationId: message.organisation_id,
      cvFileId: message.cv_file_id,
      jobId: message.job_id,
      contentHash: message.content_hash,
      storagePath: message.storage_path,
      locale: message.locale,
      enqueuedAt,
    });
  }
  return cvRescoringMessage({
    organisationId: message.organisation_id,
    applicationId: message.application_id,
    weightsHash: message.weights_hash,
    locale: message.locale,
    enqueuedAt,
  });
}

describe("queue message contract", () => {
  it("names the two contract queues and version 1", () => {
    expect(QUEUES).toEqual({ cvProcessing: "cv_processing", cvRescoring: "cv_rescoring" });
    expect(SCHEMA_VERSION).toBe(1);
  });

  it.each(examples.valid.map((e) => [e.name, e.message] as const))(
    "produces the %s example exactly",
    (_, message) => {
      expect(rebuild(message)).toEqual(message);
    },
  );

  const storagePathExamples = examples.malformed.filter((e) => e.name.startsWith("storage_path_"));

  it("has storage path examples to refuse", () => {
    expect(storagePathExamples.length).toBeGreaterThanOrEqual(7);
  });

  it.each(storagePathExamples.map((e) => [e.name, e.message] as const))(
    "refuses to produce a message whose storage_path is not a file in its own folder (%s)",
    (_, message) => {
      expect(() => rebuild(message)).toThrow(/storage_path/);
    },
  );
});
