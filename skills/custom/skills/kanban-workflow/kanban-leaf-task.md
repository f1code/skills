---
name: kanban-leaf-task
description: >
  Work on a child or standalone task with no children of its own.
allowed-tools:
  - Bash(kanban-md *)
  - Bash(kbmd *)
  - Bash(git *)
  - Bash(awk *)
  - Bash(date *)
disable-model-invocation: true
---
# Pre-requisites

## Provided Parameters

Agent Identity give to you as `<agent>`. Use in all kanban-md command:
`--claim <agent>`.
Parent Branch give to you as `<parent-branch>` (this branch you diff and
merge against — not kanban parent field).
Worktree Branch give to you as `<worktree-branch>`.
Worktree Path give to you as `<worktree-path>`.
Task ID give to you as `<task-id>`.

**STOP** if any param not give.

`<skill-dir>` = dir holding this file.

You no call `wt`. Coordinator already make `<worktree-path>` on
`<worktree-branch>` and own every merge; you only write code and hand off.

**Never fix base.** Coordinator pick it. If history look old or cut from wrong
tip, never `fetch`/`pull`/`rebase`/`merge`/`cherry-pick` to fix — that make
your diff fat and smash final merge. Use what in worktree; if no can, hand off
blocked and say which ref you expect.

**Task body append-only.** Every write use `-a … -t`; never `--body`. Review
script end body section at next timestamp line, so append without `-t` leak
into section above.

# Main Workflow

## Entry

Run on fresh pick and every re-prompt.

If prompt carry user words not already newest `## User feedback` section in
body, record them first. You write it: parent never see pane input.

```bash
kanban-md edit <task-id> --claim <agent> --status in-progress --unblock \
  -a "$(cat <<'EOF'
## User feedback
<user words>
EOF
)" -t
```

Quoted heredoc keep `'`, `$`, backticks literal; no stdin flag.

Then: body no have `## Review round` → Step 1, go on where you stop. Else →
"Review loop" step 1, as round 1 of new pass.

## Step 1: Implement

Make ALL change on `<worktree-branch>`, in `<worktree-path>`. Make smallest
change that do task, by task type:

- development task: use /implement skill
- prototype task: use /prototype skill
- research task: use /research skill

Add progress note to task body using "Progress notes" section in References.

Commit subject: project convention (`AGENTS.md`/`CONTRIBUTING.md`) first;
else body have `Ticket: KEY` → `KEY: <msg>`; else `<msg> (task <task-id>)`.
Never `#<task-id>` — GitHub read `#N` as PR/issue link and squash-merge add
`(#PR)` same way.

Discovery that change approach = judgment call: record what plan say, what you
find, what you do, cheapest undo. Spec wrong in way you no should decide →
hand off blocked instead.

Before review, add both sections (see "Judgment calls" in References):

````bash
kanban-md edit <task-id> --claim <agent> -a "$(cat <<'EOF'
## Judgment calls
- <the call, where it lives, and the cheapest way to reverse it>

## Tests run
```bash
<targeted test command, one per line>
```
EOF
)" -t
````

`## Tests run` hold narrow tests that hit this change; script replay them every
round with repo checks. Wrap env inline (`fnm exec -- npm test`). Task with
nothing to test (research, prototype) write `none: <reason>` line instead of
fenced block. When fix change either section, add restated one with full list;
last one win.

### Review loop

Max 3 round per pass; pass restart at each new `## User feedback`. You count
rounds; script number them. Any script exit not 0 or 3 → hand off blocked (see
"Blocked / Needs User Input") quoting stderr tail; no retry.

1. Prep round, with Bash tool max timeout (Claude Code `timeout: 600000`):
   ```bash
   cd <worktree-path> && uv run <skill-dir>/kanban_review.py prep <task-id> <parent-branch>
   ```
   Run repo checks and `## Tests run`, then print round number `<N>` and each
   axis to review with prompt path. Exit 3 → fix what it name, rerun: red
   check or dirty tree → fix and commit; `## Tests run` timeout → narrow it,
   add restated section; repo-check timeout → hand off blocked.
2. Progress note, keep kitty staleness check quiet:
   ```bash
   kanban-md edit <task-id> --append-body "review round <N>: <axes>" --timestamp --claim <agent>
   ```
3. Spawn one `kanban-reviewer` sub-agent per listed axis, all in one message,
   prompt "Follow `<prompt-path>`". No such agent type (omp) → general-purpose
   sub-agent on strongest model, prompt also name
   `~/.agents/agents/kanban-reviewer.md`.
4. Get verdict:
   ```bash
   cd <worktree-path> && uv run <skill-dir>/kanban_review.py verdict --claim <agent>
   ```
   Add `## Review round <N>` to body, print it, then print disposition
   heading. Exit 3 name missing axes → respawn those once, rerun; missing
   again → hand off blocked. Exit 3 "rerun prep" → step 1.
5. `APPROVE` → Step 2. `CHANGES_REQUESTED` on round 3 of pass → hand off
   blocked with `--block "review round <N> CHANGES_REQUESTED"`, no fix, no
   disposition. Else fix findings, commit, add printed heading with one line
   per finding on every non-`APPROVE` axis:
   ```bash
   kanban-md edit <task-id> --claim <agent> -a "$(cat <<'EOF'
   ## Finding disposition round <N>
   - spec#1: fixed <sha>
   - standards#2: declined: <reason>
   EOF
   )" -t
   ```
   Then step 1.

## Step 2: Hand off for merge

Use project "Definition of Done" to check task ready; green `prep` part of it.
Hand off for coordinator to merge — merge never yours to do:

```bash
kanban-md handoff <task-id> --claim <agent> --release \
  --note "Ready for merge. Verdict: <verdict>, round <N>." \
  --timestamp
```

This move task to `review` and drop your claim — that drop tell coordinator
`pick --status todo` this task no longer in flight. Stop here. Coordinator
take merge decision to user and either merge (task end `done`) or send you
feedback by re-prompt you (see Entry), or move task back to `todo` for fresh
pick if you already gone.

# References

## Judgment calls

`## Judgment calls` body section list edit reviewer most likely undo, hardest
to defend first. Judgment call is anything you pick, not derive: scope you
widen, claim you take from plan without check against code, test you change
instead of add, file you touch that task no name. Give each one location and
cheapest way to undo.

List them even when nothing look contestable. Spec reviewer challenge each one
and merge gate show them to user, so call user never make show up there. Name
at least one call you defend least.

## Progress notes

While task `in-progress`, leave short timestamp note in task body (most after
big step or before/after run test). This make handoff and review much fast.

```bash
kanban-md edit <task-id> --append-body "Implemented X/Y/Z, now running tests." --timestamp --claim <agent>
```

`--append-body` (`-a`) flag add text to body, no replace. `--timestamp` (`-t`)
flag put timestamp line in front like `[[2026-02-10]] Mon 15:04`.

## Blocked / Needs User Input

If you no can go on without user (decision, access, environment, or anything
outside your control):

```bash
kanban-md handoff <task-id> --claim <agent> \
  --block "Waiting on user: <what you need>" \
  --note "## Handoff
- Current state:
- Branch: <worktree-branch>
- Open questions (A/B):
- Next step:" \
  --timestamp --release
```

In handoff note, put:

- Exact question for user (prefer A/B option)
- What you try already and what happen
- Smallest next step after user answer
