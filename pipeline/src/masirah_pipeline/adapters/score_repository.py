"""Jobs and scores in Postgres, as the masirah_worker role (T057, migrations 0014 and 0015).

Scores are immutable: the worker only inserts them, and an insert for an application and weights
already scored does nothing, since the table holds one score per pair.
"""

from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from masirah_pipeline.adapters.tenant_transaction import acting_for
from masirah_pipeline.domain.justification import JobSpec
from masirah_pipeline.domain.scoring import weights_from
from masirah_pipeline.ports.score_repository import ScoreRecord

# The web stores a job's language requirement as a code (T059); the model reads it in words.
LANGUAGE_REQUIREMENTS = {"ar": "Arabic", "en": "English", "both": "Arabic and English"}


class PostgresScoreRepository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def job(self, organisation_id: UUID, job_id: UUID) -> JobSpec | None:
        with acting_for(self._connection, organisation_id) as cur:
            row = cur.execute(
                "select title, description, required_skills, preferred_skills,"
                " minimum_experience_years, location, language_requirement, weights"
                " from public.job where id = %s",
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        title, description, required, preferred, minimum, location, language, weights = row
        return JobSpec(
            title=title,
            description=description,
            required_skills=tuple(required),
            preferred_skills=tuple(preferred),
            minimum_experience_years=minimum,
            location=location,
            language_requirement=LANGUAGE_REQUIREMENTS.get(language, language),
            weights=weights_from(weights),
        )

    def has_score(self, organisation_id: UUID, application_id: UUID, weights_hash: str) -> bool:
        with acting_for(self._connection, organisation_id) as cur:
            row = cur.execute(
                "select exists (select 1 from public.score"
                " where application_id = %s and weights_hash = %s)",
                (application_id, weights_hash),
            ).fetchone()
        return bool(row and row[0])

    def record_score(self, organisation_id: UUID, score: ScoreRecord) -> None:
        with acting_for(self._connection, organisation_id) as cur:
            cur.execute(
                "insert into public.score (organisation_id, application_id, total, components,"
                " justification, summary, model_id, provider, prompt_version, summary_model_id,"
                " summary_provider, summary_prompt_version, input_hash, weights_hash, cost_egp)"
                " values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                " on conflict (application_id, weights_hash) do nothing",
                (
                    organisation_id,
                    score.application_id,
                    score.total,
                    Jsonb(score.components),
                    score.justification,
                    score.summary,
                    score.scoring.model_id,
                    score.scoring.provider,
                    score.scoring.prompt_version,
                    score.summarising.model_id,
                    score.summarising.provider,
                    score.summarising.prompt_version,
                    score.input_hash,
                    score.weights_hash,
                    score.cost_egp,
                ),
            )
