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

  it.each(["storage_path_outside_organisation", "storage_path_for_another_file"])(
    "refuses to produce a message whose file sits outside its own folder (%s)",
    (name) => {
      const example = examples.malformed.find((e) => e.name === name);
      if (example === undefined) throw new Error(`missing example ${name}`);
      expect(() => rebuild(example.message)).toThrow(/storage_path/);
    },
  );
});
