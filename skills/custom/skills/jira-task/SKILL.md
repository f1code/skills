---
name: jira-task
description: >
  Implement one Jira ticket as a kanban-workflow leaf, ending with a Bitbucket
  PR. Rerun on a ticket with an open PR to act on its unresolved comments.
argument-hint: "[KEY] [notes]"
allowed-tools:
  - Bash(kanban-md *)
  - Bash(git *)
  - Bash(wt *)
  - Bash(twg *)
  - Bash(uv *)
  - Bash(jq *)
  - Bash(awk *)
  - Bash(date *)
disable-model-invocation: true
---

# Jira Task

`<kw>` = `../kanban-workflow` relative to this file. Jira read-only: never
transition, comment or edit. User owns Jira status and PR comment replies.

Board at project root always exists; kanban-workflow `SKILL.md` "Multi-Agent
Environment" rules apply. Local task = state store; body append-only
(`-a … -t`).

## Steps

1. `kanban-md agent-name` → `<agent>`.
2. Pick task:
   - KEY given → `kanban-md list --property jira=KEY --json`.
   - No KEY → candidates:
     `kanban-md list --sort updated -r --show-property jira --json | jq '[.[] | select(.properties.jira)]'`.
     Exactly one not `done` → confirm with user. Else show all; user picks.

   Found → its id is `<task-id>`. Body lines `Base:`, `Branch:`, `PR:`: read
   the last match (copied description may hold lookalikes). `Base:` →
   `<parent-branch>`, `Branch:` → `<worktree-branch>`.
3. Route:
   - Missing → step 4.
   - Body has `PR:` line → "PR feedback".
   - Status `review`, blocked (leaf handed off "Waiting on user" or round-3
     CHANGES_REQUESTED): no notes → STOP, print its `## Handoff` note. Notes
     = user's answer → resume below, step 7 (leaf Entry records them,
     `--unblock`).
   - Else resume: `kanban-md edit <task-id> --claim <agent>` (nonzero → STOP,
     quote stderr). No `Branch:` line → step 5. Else
     `wt switch <worktree-branch> --no-cd --format json` → `<worktree-path>`;
     status `review` → step 8, else step 7.
4. New task:
   - Fetch
     `twg jira workitem get KEY --fields summary,description,issuetype,subtasks -o json`
     (description may be ADF; render as markdown). Subtasks present → STOP,
     report.
   - `<default>`: `git symbolic-ref refs/remotes/origin/HEAD`, fallback
     `git ls-remote --symref origin HEAD`. `git fetch origin <default>`.
     `<parent-branch>` = `origin/<default>` unless user names one.
   - Create in one call:
     `kanban-md create "<summary>" --set-property jira=KEY --claim <agent> --status in-progress --body …`
     → `<task-id>`. Body: `Ticket: KEY`, `Base: <parent-branch>`, ticket
     URL, description, acceptance criteria. Copy all: reviewers never fetch
     Jira.
5. Plan gate: `<kw>/SKILL.md` Step 2. Grilling wants a split → never create
   children; `kanban-md edit <task-id> --release --status todo`, STOP.
6. Worktree: branch per `<kw>/branch-naming.md` → `<worktree-branch>`. Then
   `<kw>/SKILL.md` leaf step 2 (`wt switch --create <worktree-branch> --base
   <parent-branch>`, record `Branch:`, `EnterWorktree`).
7. Follow `<kw>/kanban-leaf-task.md`. Extra args (`notes`) → `## User
   feedback` at its Entry.
8. Claude Code: `ExitWorktree action: keep`. Follow `<kw>/merge-gate.md`
   with `<target-branch>` = `<parent-branch>`, `<claimant>` = `<agent>`,
   `<finish>` = `pr`. Not approved → re-enter worktree, step 7.

## PR feedback

1. `PR: <id> <url>` line → PR `<id>`.
2. `twg bb prs comment query <id> -o json`; keep unresolved (check field
   name). Show them; user picks which to act on (default all). None picked
   and no extra args → STOP.
3. `kanban-md edit <task-id> --claim <agent> --status in-progress` (nonzero →
   STOP). `wt switch <worktree-branch> --no-cd --format json` →
   `<worktree-path>`. Sync with remote (user may have pushed):
   `git -C <worktree-path> fetch origin <worktree-branch> && git -C <worktree-path> merge --ff-only origin/<worktree-branch>`;
   not fast-forward → STOP, ask user.
4. Record picked comments plus extra args as one `## User feedback` section
   (`-a … -t`): per comment, author and file:line, then text as `> ` lines.
   A raw `## ` line would end the section early in `kanban_review.py`.
5. Implement feedback, commit, then enter `kanban-leaf-task.md` Review loop
   step 1. Skip leaf Entry: it would review the unchanged diff first.
6. Step 8 above (pushes to the open PR).
