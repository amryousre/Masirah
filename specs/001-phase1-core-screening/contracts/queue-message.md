# Contract: Queue message

The only runtime coupling between the Next.js application and the Python worker. Both sides must
agree on this shape; nothing else crosses the boundary except the database schema.

Transport is Supabase Queues, built on the `pgmq` extension and reached through the `pgmq_public`
schema. The web application calls `send`. The worker calls `read`, then `delete` once the job
succeeds. A message left undeleted returns to the queue after its visibility timeout, which is the
retry mechanism.

## Queue names

| Queue | Producer | Consumer | Purpose |
|---|---|---|---|
| `cv_processing` | Web application | Python worker | Extract, OCR and score one CV file |
| `cv_rescoring` | Web application | Python worker | Rescore an existing profile without re-extraction |

`cv_rescoring` exists in the contract but carries no Phase 1 producer, because weight adjustment is
FR-025 and lands in Phase 2. It is declared now so the worker's routing does not have to change
later.

## Message: cv_processing

```json
{
  "schema_version": 1,
  "job_type": "cv_processing",
  "organisation_id": "uuid",
  "cv_file_id": "uuid",
  "job_id": "uuid",
  "content_hash": "sha256 hex string",
  "storage_path": "organisations/{organisation_id}/cv/{cv_file_id}/{filename}",
  "locale": "ar | en",
  "enqueued_at": "ISO 8601 timestamp"
}
```

**Field rules**

- `schema_version` is mandatory. A worker receiving a version it does not recognise must leave the
  message in the queue and alert rather than guessing. Silent best-effort handling of an unknown
  message shape is how data gets corrupted.
- `organisation_id` is present on every message even though it is derivable from `cv_file_id`. The
  worker uses it to scope every query it makes, so that a bug in the worker cannot reach across
  tenants.
- `content_hash` lets the worker short-circuit. If a current parsed profile already exists for this
  hash within the organisation, extraction is skipped entirely and only scoring runs. This is how
  AI-03 is satisfied.
- `locale` determines the language of the generated justification and summary, per FR-015.
- `job_id` may be null. A CV can be uploaded to the organisation without being scored against a
  specific role yet, in which case extraction runs and scoring does not.

## Message: cv_rescoring

```json
{
  "schema_version": 1,
  "job_type": "cv_rescoring",
  "organisation_id": "uuid",
  "application_id": "uuid",
  "weights_hash": "sha256 hex string",
  "locale": "ar | en",
  "enqueued_at": "ISO 8601 timestamp"
}
```

## Worker obligations

The worker must satisfy all of the following, and each is separately testable.

1. **Idempotence.** Processing the same message twice must not create a second parsed profile for
   the same content hash, nor a second score for the same application and weights hash. Retries are
   normal, not exceptional.
2. **Deletion only on success.** The message is deleted after results are committed. A crash
   mid-processing must leave the message to be retried.
3. **Tenant scoping.** Every database read and write is filtered by the `organisation_id` in the
   message. The worker connects with credentials that row level security still applies to.
4. **Terminal failure is recorded, not swallowed.** After the retry limit, the worker sets the
   `cv_file` status to `failed` with a `failure_reason` and stops retrying. The file remains
   visible to the user. Nothing is ever dropped silently, per SC-006.
5. **Cost is recorded per CV.** Each score row carries its `cost_egp`, so the budget in NFR-13 is
   measured rather than assumed.
6. **Protected attributes never reach the scoring model.** Redaction happens before the model call,
   and `input_hash` is computed over the redacted text, so the audit trail proves what was sent.
