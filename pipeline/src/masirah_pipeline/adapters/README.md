# Adapters

Each adapter implements a port in `masirah_pipeline/ports/` against one real system: the
database, storage, the queue, a PDF or Word reader, or a model provider. The domain never imports
them; `main.py` builds them and hands them to the worker.

## Model providers and training (AI-09, FR-025)

Candidates' CVs are sent to a model provider to be read and scored. No provider may train its
models on what Masirah sends. That is a term of the provider's contract, not something the code can
observe, so it is checked before a provider is enabled rather than at runtime
(`contracts/model-provider-port.md`, rule 6).

`tests/unit/test_no_training_position.py` holds this list to the registry. A provider that
`provider_registry.py` can configure fails that test until it has a section here saying whether it
trains on what is sent, when its terms were read, and where they are. A section for a provider the
registry cannot configure fails it too.

## Before a provider is enabled

1. Read the provider's current commercial or API data terms, and update its section below with what
   they say and the date.
2. Make sure the organisation account the key belongs to has no opt-in to share data for training
   or improvement. Every provider below offers one, and it overrides the default.
3. Never send feedback (ratings, flags or "improve the model" reports) about a response. Each
   provider below may train on feedback that is sent.
4. If a provider's position changes to anything but "no", remove its models from `PRICES` and its
   key from `KEY_VARIABLES` in `provider_registry.py`, and its section here, in the same change.
   The worker then refuses to start with any of its models.

Candidates must also be told this in the privacy policy (spec US3, scenario 6). That policy does
not exist yet, and its wording is for the product owner to approve, so the statement is still to be
added (T094 stays open until it is). Once it exists, change it and this file together.

## Each provider's position

### anthropic

- **Trains on what Masirah sends:** no. Anthropic does not use inputs or outputs from its
  commercial products, the API among them, to train its models by default. It may train on
  feedback a customer chooses to send, or where a customer opts in.
- **Kept by the provider:** inputs and outputs are deleted within 30 days. Anything flagged for a
  usage policy breach may be kept for up to 2 years. Zero data retention is available by agreement.
- **What the adapter does:** sends each request through the Messages API and nothing else. It sends
  no feedback and uses no feature that stores files or conversations on Anthropic's side.
- **Checked:** 7 October 2026.
- **Terms:** <https://privacy.claude.com/en/articles/7996868-is-my-data-used-for-model-training> and
  <https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data>

### openai

- **Trains on what Masirah sends:** no. Data sent to the OpenAI API is not used to train or improve
  OpenAI's models unless the customer opts in to share it.
- **Kept by the provider:** abuse monitoring logs are kept for up to 30 days, unless the law
  requires longer. Zero data retention is available to eligible customers with OpenAI's approval.
- **What the adapter does:** sends each request through the Responses API with `store` off, so the
  response is not kept as application state on OpenAI's side. It sends no feedback.
- **Checked:** 7 October 2026.
- **Terms:** <https://developers.openai.com/api/docs/guides/your-data>
