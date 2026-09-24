-- storage_path_inside_tenant_folder (0004) checks only the prefix, so the folder itself or a path
-- through "..", "." or an empty segment was accepted. A stored path must name a file, by the same
-- rule the queue message contract applies (contracts/queue-message.md): the web application copies
-- storage_path into cv_processing messages, and a row refused here never strands one in the queue.

alter table public.cv_file
  add constraint storage_path_names_a_file check (
    storage_path !~ '(^|/)\.{0,2}(/|$)'
    and strpos(storage_path, '\') = 0
  );
