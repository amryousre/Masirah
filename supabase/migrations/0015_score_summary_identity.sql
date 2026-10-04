-- T057: a score's summary is written by a different model from its ratings (AI-05: the cheap
-- tier summarises, the strong tier scores), so AI-02 needs that model's identity too. model_id,
-- provider and prompt_version stay the scoring call's; these three are the summary call's.
-- Nullable only because rows may predate them; the worker always writes all three.

alter table public.score
  add column summary_model_id text,
  add column summary_provider public.model_provider,
  add column summary_prompt_version text,
  add constraint summary_identity_is_whole check (
    (summary_model_id is null) = (summary_provider is null)
    and (summary_provider is null) = (summary_prompt_version is null)
  );
