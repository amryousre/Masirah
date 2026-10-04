# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Masirah (مسيرة) is a bilingual Arabic/English AI CV-screening product for Egyptian SMEs. A recruiter describes a job, uploads CVs, and gets a ranked list where each score carries a component breakdown and a written justification. `CONTEXT.md` defines the domain vocabulary (for example: a *CV* is the document, a *parsed_profile* is its extraction). `PRODUCT.md` and `DESIGN.md` hold the product and interface decisions.

Work follows Spec Kit. The active feature is `specs/001-phase1-core-screening/`:

- `spec.md` holds the requirements (FR-, SC-, AI-, NFR- ids).
- `plan.md` and `research.md` hold the decisions, with dated amendments.
- `tasks.md` is the ordered task list (T001…), ticked as work merges.
- `contracts/` holds the cross-runtime contracts.

Architecture decisions are in `Docs/adr/`. The constitution, `.specify/memory/constitution.md`, is binding: test-first, enforced boundaries, strict typing, bilingual UI, cost budgets and fairness.

## Layout

One repository with three parts and no monorepo tooling.

**`web/`** is a Next.js 16 App Router app in TypeScript (React 19, next-intl, Supabase SSR auth, CSS Modules).

- It is not the Next.js of most training data: it uses `proxy.ts` (not `middleware.ts`), the `PageProps`/`LayoutProps` globals and `next typegen`. Read `web/node_modules/next/dist/docs/` before relying on an API.
- Routes live under `app/[lang]/`, where the locale decides the document direction in one place.
- Every user-visible string lives in `messages/{ar,en}.json`. A lint rule fails on hard-coded strings and on physical `left`/`right` in styles; use logical properties.

**`pipeline/`** is the Python 3.12 worker that extracts and scores CVs. It consumes the `cv_processing` queue.

**`supabase/`** holds the migrations (PostgreSQL 17, row level security on every table, pgmq queues and a private storage bucket) and `config.toml`.

**Both runtimes use ports and adapters.**

- `lib/domain` (web) and `masirah_pipeline/domain` (pipeline) must not import adapters, the database, HTTP, model SDKs or PDF libraries. `ports/` must not import `adapters/`.
- In the pipeline, import-linter enforces this from the contracts in `pipeline/pyproject.toml`, and `tests/unit/test_import_boundaries.py` checks the contracts themselves.

**The queue message is the only runtime coupling between web and pipeline.** It is defined in `contracts/queue-message.md` and mirrored in `web/lib/ports/queue-message.ts` and `pipeline/src/masirah_pipeline/ports/queue_message.py`. `schema_version` is mandatory, and the worker refuses a version it doesn't recognise. Change all three together.

**Tenancy.** Every table carries `organisation_id` with an RLS policy. The organisation always comes from the session, never from a request body. `pipeline/tests/unit/test_rls_isolation.py` proves the isolation.

**Text extraction** is `pipeline/src/masirah_pipeline/adapters/native_text.py`.

- It uses pdfminer.six, not PyMuPDF, because PyMuPDF is AGPL. PyMuPDF and Pillow are dev-only, for the corpus tools under `pipeline/tools/`.
- `reading_order.py` reads multi-column pages column by column.
- `visual_order.py` repairs Arabic that Chromium-made PDFs store in visual order.

**Model calls** go through a provider port with Anthropic and OpenAI adapters (decision Q5).

- Responses come back as structured output only, never parsed from free text (AI-01).
- Identity, cost and prompt version are returned with every call and stored (AI-02).
- Extraction and summaries use the cheap tier and scoring uses the strong tier (AI-05).
- Protected attributes are removed by the domain before any scoring call (FR-017/FR-029).

## Commands

### Local Supabase

Run from the repo root. Docker is required. The local stack uses ports 1432x (API on 14321).

```sh
npx --yes supabase@2.117.0 start
npx --yes supabase@2.117.0 gen types --local --schema public > web/lib/adapters/database.types.ts
```

The Supabase CLI reads the Google sign-in variables from the gitignored root `.env`.

### Web

Run from `web/`. It reads `web/.env.local` (copied from `.env.example`). The e2e tests also need `SUPABASE_SECRET_KEY` in `web/.env.test.local`.

```sh
npm run dev
npm run lint          # next typegen + eslint, zero warnings
npm run typecheck     # next typegen + tsc --noEmit
npm run format:check
npm test              # vitest unit tests
npx vitest run tests/unit/session.test.ts
npm run build && npm run test:e2e   # Playwright against the production build, with axe checks
npx playwright test tests/e2e/sign-in.spec.ts
```

### Pipeline

Run from `pipeline/` with uv. On Windows, Arabic output and `lint-imports` fail under cp1252 unless `PYTHONUTF8` is set first:

- Git Bash: prefix the command, as in `PYTHONUTF8=1 uv run pytest`.
- PowerShell: run `$env:PYTHONUTF8 = "1"` once per session.
- cmd: run `set PYTHONUTF8=1`.

```sh
uv sync
uv run ruff format --check && uv run ruff check
uv run mypy                 # strict
uv run lint-imports         # architecture contracts
uv run pytest               # unit and integration suites; database-marked tests need local Supabase
uv run pytest -m "not database"
uv run pytest tests/unit/test_native_text.py -k docx
uv run --env-file .env python -m masirah_pipeline   # the worker; settings in .env.example
```

### The release gate (SC-002 / SC-003)

The accuracy suite is not part of `pytest`'s default paths. It runs an extractor over the labelled corpus in `pipeline/tests/fixtures/cvs/` and needs at least 95% field accuracy on native PDFs and at least 85% on scans and photos. Only real documents count (`origin` real, `simulated` false).

```sh
MASIRAH_EXTRACTOR=package.module:function uv run pytest tests/accuracy
MASIRAH_EXTRACTOR=tests.accuracy.field_accuracy:oracle uv run pytest tests/accuracy   # harness self-check
MASIRAH_EXTRACTOR=tests.accuracy.extractors:cheap_model uv run --env-file .env pytest tests/accuracy
MASIRAH_CHEAP_MODEL=openai:gpt-5.6-luna MASIRAH_EXTRACTOR=tests.accuracy.extractors:cheap_model uv run --env-file .env pytest tests/accuracy
```

The last two make real model calls through the provider configured for the cheap tier, and print the spend with the report. The model settings and keys live in the gitignored `pipeline/.env`; `pipeline/.env.example` lists them.

The scoring rules and the label format are in `pipeline/tests/fixtures/cvs/README.md`.

The corpus holds anonymised real CVs, synthetic CVs (`syn-*`) and captures:

- Add a real scan or photo with `uv run python -m tools.add_capture`, which strips the camera metadata.
- Never commit an original, non-anonymised CV or a photo of one.

CI is `.github/workflows/ci.yml`. It runs exactly the checks above for web, pipeline and database. The database job starts Supabase.

## Working conventions

- **Test first.** Write the test, watch it fail for the intended reason, then implement. Every extraction or scoring behaviour needs a test backed by a committed fixture.
- **Never push to `main`.** Work on a branch, open a PR and let CodeRabbit review it. Fix or answer every comment, including outside-diff and nitpick findings in the review body. Merge only when all of these hold:
  - CI is green;
  - CodeRabbit's check succeeds on the head;
  - every thread is resolved, and every reply has a CodeRabbit answer;
  - CodeRabbit has been quiet for about two minutes.
- **Push credentials.** Git's credential manager may hold a GitHub account that can't see the repo. Push with `git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push` and give `gh` the repo owner's token if needed.
- **Supabase cloud.** Never `config push` the repo's `supabase/config.toml` to the hosted project. Change hosted Auth settings through a scoped config in a scratch directory, after a `config diff`.
- **Line endings.** `.gitattributes` forces LF. On Windows, Python's `write_text` writes CRLF, so pass `newline="\n"` when a script writes repo files.
