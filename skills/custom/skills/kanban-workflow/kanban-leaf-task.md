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

Agent Identity give to you as `<agent>`. Use in all kanban-md command:
`--claim <agent>`.
Parent Branch give to you as `<parent-branch>` (this branch you diff and
merge against — not kanban parent field).
Worktree Branch give to you as `<worktree-branch>`.
Worktree Path give to you as `<worktree-path>`.
Task ID give to you as `<task-id>`.

**STOP** if any param not give.

You no call `wt`. Coordinator already make `<worktree-path>` on
`<worktree-branch>` and own every merge; you only write code and hand off.

**Never fix base.** Coordinator pick it. If history look old or cut from wrong
tip, never `fetch`/`pull`/`rebase`/`merge`/`cherry-pick` to fix — that make
your diff fat and smash final merge. Use what in worktree; if no can, hand off
blocked and say which ref you expect.

# Main Workflow

## Step 1: Implement

Make ALL change on `<worktree-branch>`, in `<worktree-path>`. Make smallest
change that do task, by task type:

- development task: use /implement skill
- prototype task: use /prototype skill
- research task: use /research skill

Add progress note to task body using "Progress notes" section in References.

End every commit subject with `(task <task-id>)`, never `#<task-id>` — GitHub
read `#N` as PR/issue link and squash-merge add `(#PR)` same way.

Your fix point for code review is `git merge-base HEAD <parent-branch>` — not
`<parent-branch>` HEAD, which move as sibling merge and show this task diff
*minus* sibling work already land.

Run self-review per "Self-review" in References. When come back, add whole
verdict block to task body:

```bash
kanban-md edit <task-id> --append-body "<review block>" --timestamp --claim <agent>
```

Fix loop have limit: on `CHANGES_REQUESTED`, fix finding and re-review, up to
3 cycle total. If cycle 3 still give `CHANGES_REQUESTED`, hand off blocked
with last verdict block (see "Blocked / Needs User Input") instead of go
Step 2.

## Step 2: Hand off for merge

Use project "Definition of Done" to check task ready. Hand off for coordinator
to merge — merge never yours to do:

```bash
kanban-md handoff <task-id> --claim <agent> --release \
  --note "Ready for merge. Verdict: <APPROVE|CHANGES_REQUESTED after N cycles>.

## Judgment calls
- <the call, where it lives, and the cheapest way to reverse it>" \
  --timestamp
```

This move task to `review` and drop your claim — that drop tell coordinator
`pick --status todo` this task no longer in flight. Stop here. Coordinator
take merge decision to user and either merge (task end `done`) or send you
feedback by re-prompt you, or move task back to `todo` for fresh pick if you
already gone.

### Judgment calls

End every handoff note with edit reviewer most likely undo, hardest to defend
first. Judgment call is anything you pick, not derive: scope you widen, claim
you take from plan without check against code, test you change instead of add,
file you touch that task no name. Give each one location and cheapest way to
undo.

List them even when review give `APPROVE`. Reviewer share your thinking and
bless call user never make, so those worth show. Name at least one call you
defend least.

# References

## Self-review

Before hand off, run own self-review. Spawn `kanban-reviewer` agent (live in
`~/.claude/agents/`; it pin strong model so review quality no inherit cheaper
implementing model) with cwd set to `<worktree-path>`. If that agent type no
there, fall back to fresh-context general-purpose sub-agent on strongest model
you have. Either way, make it read `reviewing-changes.md` (bundle beside this
file, same skill directory) for full checklist and output contract. Input to
give it:

- Task ID: `<task-id>`
- Plan: whatever link from task body, or "trivial — no plan"
- Base ref: `git merge-base HEAD <parent-branch>` (compute first, pass
  resolved SHA)
- Head ref / branch: `<worktree-branch>`
- Worktree path: `<worktree-path>`

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