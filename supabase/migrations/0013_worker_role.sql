-- T053: the worker's own database role (contracts/queue-message.md, worker obligation 3).
-- The worker reads, deletes and archives queue messages. It never sends one, so a compromised
-- worker cannot plant work for itself, and it is not the service role, which bypasses row level
-- security on every table. Its access to tenant tables arrives with the consume loop (T054).
--
-- The role cannot log in here. Where the worker is deployed, an operator runs
-- `alter role masirah_worker with login password '...'`, so no password ever sits in git.

create role masirah_worker nologin noinherit;
-- Lets the migration owner act as the role, as the tests do with `set local role`.
grant masirah_worker to postgres;

grant usage on schema pgmq_public to masirah_worker;
grant execute on function pgmq_public.read(text, integer, integer) to masirah_worker;
grant execute on function pgmq_public.delete(text, bigint) to masirah_worker;
grant execute on function pgmq_public.archive(text, bigint) to masirah_worker;

-- pgmq's functions run with the caller's rights, so the role needs the tables underneath. A read
-- locks rows and moves only their visibility timeout and read count; the message is never
-- rewritten. An archive deletes from the queue and inserts into its archive, returning only the
-- message id, which is all of an archived message the worker can see.
grant usage on schema pgmq to masirah_worker;
grant select, delete on pgmq.q_cv_processing, pgmq.q_cv_rescoring to masirah_worker;
grant update (vt, read_ct) on pgmq.q_cv_processing, pgmq.q_cv_rescoring to masirah_worker;
grant insert, select (msg_id) on pgmq.a_cv_processing, pgmq.a_cv_rescoring to masirah_worker;

create policy "the worker takes messages" on pgmq.q_cv_processing
  for all to masirah_worker using (true);
create policy "the worker takes messages" on pgmq.q_cv_rescoring
  for all to masirah_worker using (true);
create policy "the worker archives failed messages" on pgmq.a_cv_processing
  for all to masirah_worker using (true);
create policy "the worker archives failed messages" on pgmq.a_cv_rescoring
  for all to masirah_worker using (true);
