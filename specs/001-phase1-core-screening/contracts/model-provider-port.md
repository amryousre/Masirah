# Contract: Model provider port

The interface the domain owns and both providers implement. Required by Principle II, which forbids
domain logic from importing provider code, and by decision Q5, which puts Anthropic and OpenAI in
service simultaneously so their Arabic quality and cost can be compared on real CVs.

The port lives in `pipeline/src/masirah_pipeline/ports/`. Implementations live in `adapters/`. No
module under `domain/` may import from `adapters/`.

## Operations

### extract_profile

Turns CV text into a structured profile. Uses the cheaper model tier, per AI-05.

| | |
|---|---|
| **Input** | Document text, source language hint (optional, never required), output schema |
| **Output** | Structured profile, confidence, token counts, model identity, cost |
| **Tier** | Cheap |

### summarise_candidate

Produces the three to five line summary required by FR-016. Cheap tier.

### score_application

Scores a redacted profile against a job specification, producing components and a written
justification citing evidence. Uses the stronger tier, per AI-05.

| | |
|---|---|
| **Input** | Redacted profile, job specification, component weights, output locale, output schema |
| **Output** | Total, components, justification, summary, token counts, model identity, cost |
| **Tier** | Strong |

**The input is already redacted when it reaches this call.** Removing protected attributes is the
domain's job, not the provider adapter's. An adapter never sees a name, gender, age, photograph,
nationality or marital status for a scoring call, which makes FR-017 provable by testing the domain
alone.

### read_document_image

Recovers text from a page image. Implemented by the vision path of the OCR port rather than by the
text providers, but declared here because it is a model call subject to the same cost accounting.

## Universal requirements

Every operation on every implementation must satisfy these. They are contract terms, not
suggestions.

1. **Structured output only.** Every call declares an output schema and the response is parsed
   against it. No implementation may fall back to interpreting free text, per AI-01 and Principle
   III.
2. **Identity is returned, not assumed.** Every response carries the provider, the concrete model
   identifier and the prompt version actually used. The caller stores these, per AI-02.
3. **Cost is returned.** Every response carries token counts and computed cost. A provider that
   cannot report cost cannot satisfy NFR-13 and is not a valid implementation.
4. **Deterministic inputs are hashable.** The exact payload sent is available to the caller for
   fingerprinting, so `input_hash` describes reality rather than intent.
5. **Failures are typed.** Rate limiting, timeout, refusal and malformed output are distinguishable
   by the caller, because they warrant different retry behaviour. A single generic error type is not
   acceptable.
6. **No training on customer data.** Each implementation documents the contractual position with
   its provider, per AI-09. This is a deployment prerequisite, checked before a provider is enabled
   rather than at runtime.

## Provider selection

Selection is configuration, not code. The worker reads which provider serves which tier from
environment configuration, so a comparison run means changing a variable rather than editing logic.

Both providers must produce output conforming to the same schemas. A schema that only one provider
can satisfy is a defect in the schema, not a licence to branch on provider inside the domain.
