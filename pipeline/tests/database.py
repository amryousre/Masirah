"""Shared helpers for tests that run against the local Supabase database."""

import json
import os
import uuid
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

DATABASE_URL = os.environ.get(
    "MASIRAH_TEST_DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:14322/postgres"
)
CV_BUCKET = "cv-originals"
TENANT_TABLES = [
    "app_user",
    "job",
    "candidate",
    "cv_file",
    "parsed_profile",
    "application",
    "score",
    "activity",
    "deletion_request",
]
WEIGHTS = {
    "skills_match": 30,
    "experience_relevance": 25,
    "education": 15,
    "tenure_stability": 10,
    "language": 10,
    "location": 10,
}

Cursor = psycopg.Cursor[tuple[Any, ...]]


@dataclass(frozen=True)
class Tenant:
    organisation_id: uuid.UUID
    user_id: uuid.UUID
    row_ids: dict[str, uuid.UUID]
    storage_path: str


def seed_tenant(cur: Cursor, name: str) -> Tenant:
    """Create one organisation with a user and one row in every tenant table."""
    org, user = uuid.uuid4(), uuid.uuid4()
    ids = {table: uuid.uuid4() for table in TENANT_TABLES} | {"app_user": user}
    path = f"organisations/{org}/cv/{ids['cv_file']}/cv.pdf"
    statements: list[tuple[str, tuple[object, ...]]] = [
        ("insert into auth.users (id, email) values (%s, %s)", (user, f"{name}@example.test")),
        (
            "insert into public.organisation (id, name, locale) values (%s, %s, 'ar')",
            (org, name),
        ),
        (
            "insert into public.app_user (id, organisation_id, email) values (%s, %s, %s)",
            (user, org, f"{name}@example.test"),
        ),
        (
            "insert into public.job (id, organisation_id, title, weights) values (%s, %s, %s, %s)",
            (ids["job"], org, "Accountant", Jsonb(WEIGHTS)),
        ),
        (
            "insert into public.candidate (id, organisation_id, full_name) values (%s, %s, %s)",
            (ids["candidate"], org, f"{name} candidate"),
        ),
        (
            "insert into public.cv_file (id, organisation_id, candidate_id, storage_path,"
            " original_filename, mime_type, byte_size, content_hash)"
            " values (%s, %s, %s, %s, 'cv.pdf', 'application/pdf', 1024, %s)",
            (ids["cv_file"], org, ids["candidate"], path, "a" * 64),
        ),
        (
            "insert into public.parsed_profile (id, organisation_id, cv_file_id, version,"
            " is_current, extraction_source, confidence, profile)"
            " values (%s, %s, %s, 1, true, 'native_text', 0.97, %s)",
            (ids["parsed_profile"], org, ids["cv_file"], Jsonb({"full_name": name})),
        ),
        (
            "insert into public.application (id, organisation_id, candidate_id, job_id)"
            " values (%s, %s, %s, %s)",
            (ids["application"], org, ids["candidate"], ids["job"]),
        ),
        (
            "insert into public.score (id, organisation_id, application_id, total, components,"
            " justification, summary, model_id, provider, prompt_version, input_hash,"
            " weights_hash, cost_egp)"
            " values (%s, %s, %s, 72, %s, 'Cites evidence.', 'Summary.', 'model-x',"
            " 'anthropic', 'v1', %s, %s, 1.2)",
            (ids["score"], org, ids["application"], Jsonb(WEIGHTS), "b" * 64, "c" * 64),
        ),
        (
            "insert into public.activity (id, organisation_id, actor_id, action, subject_type,"
            " subject_id) values (%s, %s, %s, 'candidate.viewed', 'candidate', %s)",
            (ids["activity"], org, user, ids["candidate"]),
        ),
        (
            # Completed, so the seeded candidate is not waiting to be purged.
            "insert into public.deletion_request (id, organisation_id, candidate_id, requested_by,"
            " completed_at) values (%s, %s, %s, %s, now())",
            (ids["deletion_request"], org, ids["candidate"], user),
        ),
        (
            "insert into storage.objects (bucket_id, name) values (%s, %s)",
            (CV_BUCKET, path),
        ),
    ]
    for statement, params in statements:
        cur.execute(statement, params)
    return Tenant(org, user, ids, path)


def act_as(cur: Cursor, user_id: uuid.UUID | None) -> None:
    """Switch the transaction to the role and identity an API request would carry."""
    if user_id is None:
        cur.execute("set local role anon")
        return
    claims = json.dumps({"sub": str(user_id), "role": "authenticated"})
    cur.execute("select set_config('request.jwt.claims', %s, true)", (claims,))
    cur.execute("set local role authenticated")
