# Issue tracker: Jira (MAS)

Issues for this repo live in the Jira project **MAS** on `amryousre.atlassian.net`, not in GitHub Issues. The repo's own plan, `specs/001-phase1-core-screening/tasks.md`, holds the task list (T001…), and Jira mirrors it.

## Tools

- **Preferred: the TWG CLI** (`twg`). If it isn't on PATH, run `"$LOCALAPPDATA/Programs/twg/bin/twg.exe"`. Load the `twg` and `twg-jira` skills before any write. To find a command, run `twg help "<terms>"`.
- **Fallback: the `atlassian` MCP** (`mcp__atlassian__*`), cloudId `ff9dcbf8-829a-43f2-9dc8-0f487ce6e523`.
- **Never use the claude.ai Atlassian Rovo connector.** It is signed in to a different company's site and cannot reach MAS.

## Hierarchy

Epic → Story (parent) → Sub-task (parent).

- Sub-task summaries start with their T-number from `tasks.md`, for example `T094 A privacy page for candidates`.
- Story Points (`customfield_10033`) can be set on Epics and Stories only.

## Conventions

- **Read an issue**: `twg jira workitem get <KEY> --agent-fields @compact -o json`. The key is positional; `--id` is rejected.
- **Search**: use JQL, for example `project = MAS AND statusCategory != Done`. With the MCP fallback, call `searchJiraIssuesUsingJql`.
- **Create an issue**: create it under the right parent. A new piece of work that `tasks.md` doesn't cover yet also needs a T-number added there.
- **Comment**: `twg jira workitem comment create --issue-id <KEY> --body "..."`
- **Transition**: `twg jira workitem transition --id <KEY> --transition-id <id> --transition-comment "..."` moves the issue and comments in one call. The transition IDs are 11 To Do, 21 In Progress, 31 In Review and 41 Done.
- **Labels**: the triage roles are applied as Jira labels; see `triage-labels.md`.
- **Roll up after every move.** If all of an issue's children are Done, the parent moves to Done. If any child has started, the parent moves to In Progress. Repeat up to the Epic.

## When a skill says "publish to the issue tracker"

Create a MAS issue under the matching Epic or Story. Don't create GitHub issues.

## When a skill says "fetch the relevant ticket"

Run `twg jira workitem get <KEY> --agent-fields @compact -o json` and read its comments.

## Wayfinding operations

Used by `/wayfinder`.

- **Map**: an Epic or Story whose description holds the Notes, Decisions-so-far and Fog sections.
- **Child ticket**: a Sub-task under the map, or a Story under an Epic map.
- **Blocking**: an "is blocked by" issue link. A ticket is unblocked when every issue blocking it is Done.
- **Frontier query**: list the map's children that are not Done. Drop any child with an open blocker or an assignee. The first remaining child in rank order wins.
- **Claim**: assign the ticket to yourself and move it to In Progress (21). This is the session's first write.
- **Resolve**:
  1. Comment the answer on the ticket.
  2. Move it to Done (41).
  3. Append the gist and the key to the map's Decisions-so-far.
  4. Roll up the parents.
