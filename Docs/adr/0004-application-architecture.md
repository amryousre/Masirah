# Next.js application with a queued Python processing worker

The CV pipeline must preserve reading order across multi-column layouts, OCR phone photographs,
normalise Arabic name variants and convert Hijri dates, all of which have markedly stronger
library support in Python than in JavaScript, and parsing quality is the highest rated risk in the
project (R-03). So the pipeline is Python and the application is TypeScript.

The application framework is Next.js, chosen over Angular and over a static Vite build for two
reasons: it provides server-side routes to hold model API keys and to receive the Phase 2 email
and WhatsApp webhooks (FR-002, FR-005), and Supabase documents Next.js as a first-class target
while publishing no official Angular guide, which matters when a solo part-time builder would
otherwise spend time translating examples.

Heavy processing runs in a long-lived Python worker consuming a job queue rather than inside
request handlers, because NFR-02 requires a batch of 100 CVs to finish within 10 minutes and no
serverless function lives that long. Next.js receives the upload and enqueues; the worker parses,
runs OCR, scores and writes results back.

Both components live in one repository, a web folder and a pipeline folder, with no monorepo
tooling, which is the simplest arrangement that works for one developer.

Model access goes through a provider interface with both Anthropic and OpenAI implemented from the
start, so that cost and Arabic output quality can be compared on real CVs early. OCR uses a vision
model as the primary path with Tesseract as fallback, because Tesseract is weak on Arabic and
weaker still on phone photographs, which is exactly the 85 percent accuracy target in section 15.

## Consequences

Migrating off Netlify before Phase 3 (ADR 0002) is heavier than it would have been for static
files, because a Node runtime now has to be hosted rather than a folder of assets.

More immediately: **the queue and the Python worker need somewhere to run from Phase 1 onward, and
Netlify does not host either.** A second hosting target is therefore required at the start of
Phase 1, not at Phase 3 as the hosting decision assumed.

That target is a managed background-worker host, with the queue living in the existing Supabase
Postgres rather than a separate Redis, so no additional datastore has to be operated and jobs stay
transactional with the data they act on. Either Render or Railway satisfies this; the pick between
them is a small, reversible choice to make at signup, and Render is the marginal preference
because it treats a background worker as a first-class service type.
