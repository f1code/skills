---
name: kanban-leaf-task
description: >
  Work on a child or standalone task with no children of its own.
allowed-tools:
  - Bash(kanban-md *)
  - Bash(kbmd *)
  - Bash(git *)
  - Bash(go *)
  - Bash(golangci-lint *)
  - Bash(awk *)
  - Bash(date *)
disable-model-invocation: true
---

# Pre-requisites

## Provided Parameters

The Agent Identity must be provided to you as `<agent>`. Use this in all
kanban-md commands: `--claim <agent>`.
The Parent Branch must be provided to you as `<parent-branch>` (this is the
integration branch you diff and eventually merge against — not the
structural kanban parent field).
The Worktree Branch must be provided to you as `<worktree-branch>`.
The Worktree Path must be provided to you as `<worktree-path>`.
The Task ID must be provided to you as `<task-id>`.

**STOP** if any of these parameters is not explicitly provided.

You do not call `wt` at all. The coordinator already created
`<worktree-path>` on `<worktree-branch>` and owns every merge; you only write
code and hand off.

**Never repair the base.** The coordinator chose it. If history looks stale or
cut from the wrong tip, never `fetch`/`pull`/`rebase`/`merge`/`cherry-pick` to
fix it — that inflates your diff and wrecks the final merge. Work with what is
in the worktree; if you can't, hand off blocked saying which ref you expected.

# Main Workflow

## Step 1: Implement

Ensure ALL changes are made on `<worktree-branch>`, in `<worktree-path>`.
Implement the smallest change that satisfies the task, depending on the task
type:

- development task: use the /implement skill
- prototype task: use the /prototype skill
- research task: use the /research skill

Append progress notes to the task body using the "Progress notes" section in
References.

Your fixed point for code review is `git merge-base HEAD <parent-branch>` —
not `<parent-branch>` HEAD itself, which moves as siblings merge and would
show this task's diff *minus* a sibling's already-landed work.

Run the self-review per "Self-review" in References. When it returns, append
the entire verdict block to the task body:

```bash
kanban-md edit <task-id> --append-body "<review block>" --timestamp --claim <agent>
```

Bounded fix loop: on `CHANGES_REQUESTED`, fix the findings and re-review, up
to 3 cycles total. If cycle 3 still returns `CHANGES_REQUESTED`, hand off
blocked with the last verdict block (see "Blocked / Needs User Input") instead
of proceeding to Step 2.

## Step 2: Hand off for merge

Use the project's "Definition of Done" to confirm the task is ready. Hand off
for the coordinator to merge — merging is never yours to do:

```bash
kanban-md handoff <task-id> --claim <agent> --release \
  --note "Ready for merge. Verdict: <APPROVE|CHANGES_REQUESTED after N cycles>." \
  --timestamp
```

This moves the task to `review` and releases your claim — that release is
what tells the coordinator's `pick --status todo` this task is no longer
in flight. Stop here. The coordinator picks up the merge decision with the
user and either merges (task ends `done`) or sends you feedback by
re-prompting you, or moves the task back to `todo` for a fresh pick if you
already exited.

# References

## Self-review

Before handing off, run an independent self-review. Spawn a fresh-context
sub-agent with cwd set to `<worktree-path>`, and have it read
`reviewing-changes.md` (bundled beside this file, in the same skill
directory) for the full checklist and output contract. Inputs to give it:

- Task ID: `<task-id>`
- Plan: whatever is linked from the task body, or "trivial — no plan"
- Base ref: `git merge-base HEAD <parent-branch>` (compute this first, pass
  the resolved SHA)
- Head ref / branch: `<worktree-branch>`
- Worktree path: `<worktree-path>`

## Progress notes

While a task is `in-progress`, leave short timestamped notes in the task body
(especially after major steps or before/after running tests). This makes
handoffs and reviews much faster.

```bash
kanban-md edit <task-id> --append-body "Implemented X/Y/Z, now running tests." --timestamp --claim <agent>
```

The `--append-body` (`-a`) flag appends text to the existing body without
replacing it. The `--timestamp` (`-t`) flag prefixes a timestamp line like
`[[2026-02-10]] Mon 15:04`.

## Blocked / Needs User Input

If you cannot continue without the user (decision, access, environment, or
anything outside your control):

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

In your handoff note, include:

- The exact question(s) for the user (prefer A/B options)
- What you already tried and what happened
- The minimal next step after the user responds
