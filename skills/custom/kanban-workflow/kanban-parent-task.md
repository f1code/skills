---
name: kanban-parent-task
description: >
  Coordinate the children of a parent task: fan out up to 3 in parallel via
  a pane driver (herdr or kitty), gate every merge on the user, recurse into
  sub-epics.
allowed-tools:
  - Bash(kanban-md *)
  - Bash(kbmd *)
  - Bash(git *)
  - Bash(wt *)
  - Bash(herdr *)
  - Bash(kitten *)
  - Bash(go *)
  - Bash(golangci-lint *)
  - Bash(awk *)
  - Bash(date *)
disable-model-invocation: true
---

# Kanban Parent Task

Coordinates one parent task's children to completion, then hands the parent
to the user in `review`. Never implements a child itself — a parent's work is
entirely its children's. Never merges itself into anything past this
invocation; that is the outer coordinator's job if this parent is itself a
child (see "Recursing into a sub-epic" below).

`<parent-id>`, `<agent>`, and `<driver>` (`herdr` or `kitty`) must be
provided. **STOP** if any is missing.

## Setup

### 1. Claim the parent

```bash
kanban-md edit <parent-id> --claim <agent> --status in-progress
```

On error (already claimed by a live, non-expired claim), **STOP** — another
coordinator owns this subtree. The claim is what enforces a single writer on
the integration branch; refresh it every poll cycle in the main loop below.

### 2. Integration branch

Read the parent body for `Integration branch: <name>`.

- **Found** — use it as `<integration-branch>`.
- **Not found** — determine `<parent-branch>` (the branch to cut from): the
  *grandparent's* `Integration branch:` line if `<parent-id>` has a parent,
  else the current board-home branch. Name the new branch per
  **`branch-naming.md`** (in this skill's directory — the naming rules used
  here and by leaves), then create it:
  ```bash
  wt switch --create epic/<parent-id>-<slug> --base <parent-branch> --no-cd --format json
  ```
  Record `Integration branch: epic/<parent-id>-<slug>` in the parent body.
  Return board-home to `<parent-branch>` (the coordinator does not work in
  this worktree — children's worktrees branch off its HEAD).

### 3. Base refs are fixed once chosen

`wt merge` at the merge gate is the only history-moving command you run. Never
`fetch`/`pull`/`rebase`/`merge` a branch to "catch it up", least of all a
child's. If a branch was cut from the wrong tip, **STOP and ask the user** —
moving it rewrites diffs under children still working on it.

## Pane driver

All child-spawning and settle-detection goes through five driver operations.
Everything else in this file is driver-agnostic.

| Op | Inputs | Output |
|---|---|---|
| `resolve-kind` | — | agent kind for children |
| `spawn` | worktree path, child name `kb-<id>`, kind, prompt | handle (pane/window id) |
| `focus` | child name | — |
| `notify` | title | — |
| `read-output` | child name | recent terminal text |

There is no `wait` operation — see Step 4.

Each driver's calls and its settle-detection specifics live in its own file,
beside this one: **`drivers/herdr.md`** or **`drivers/kitty.md`**. Read the one
matching the `<driver>` you were passed, now, and resolve `resolve-kind` once
from it — the returned kind is used for every child's `spawn` below. Ask the
user only if that is unresolvable.

## Main loop

Repeat until every child is terminal (`done`, or handed off in `review`/
`blocked` and accounted for in the exit contract).

### Step 1: Refresh the parent claim

```bash
kanban-md edit <parent-id> --claim <agent>
```

On error, **STOP** — someone else took it.

### Step 2: Promote backlog children to todo

Re-run every pass — this also covers children added to the parent after
setup:

```bash
kanban-md list --parent <parent-id> --status backlog --json | jq -r '.[].id' \
  | xargs -r -I{} kanban-md move {} todo
```

### Step 3: Fan out, up to 3 live children

Count current live children (children you started that haven't
exited/handed off yet). While fewer than 3 live and a pick succeeds:

```bash
kanban-md pick --claim <agent> --parent <parent-id> --status todo --move in-progress
```

`--status todo` is mandatory, not a convenience filter: a child that already
handed off to `review` has released its claim, and a tags-only pick would
re-pick and re-implement work about to be merged. `pick` also natively
withholds any child still blocked on an unfinished `depends_on` — a
dependency chain like `#55 → #56 → #57 → #58` serializes for free through
this same loop that fans 3-wide on independent children.

For each newly picked child `<child-id>`:

1. Determine its `<branch-name>` (task/epic-<id>-<slug> per
   `branch-naming.md`) and create its worktree **off the integration branch
   HEAD**, so it inherits every sibling merged so far:
   ```bash
   wt switch --create <branch-name> --base <integration-branch> --no-cd --format json
   ```
   Record `Branch: <branch-name>` in the child's body (or
   `Integration branch: <branch-name>` if the child itself has children).
2. `spawn` it with worktree path, `kb-<child-id>`, the resolved kind, and the
   filled prompt template below — exact call in your `<driver>` file. Record
   the returned handle (pane id or window id) in the child's body next to
   `Branch:`.

If `pick` returns nothing and fewer than 3 are live, there is nothing more
to fan out this pass — fall through to Step 4.

#### Child prompt template

```
Follow the instructions in kanban-leaf-task.md (or kanban-parent-task.md if
this task itself has children), found in <this-skill-directory>.

Agent identity: kb-<child-id>
Task ID: <child-id>
Parent branch: <integration-branch>
Worktree branch: <branch-name>
Worktree path: <worktree-path>
Driver: <driver>
```

### Step 4: Wait on live children — poll the board, not the panes

No driver exposes lifecycle state that both drivers can rely on (kitty has
none at all), so settle detection polls the board directly:

```bash
kanban-md list --parent <parent-id> --json
```

Every state the coordinator acts on is already written to the board by the
child itself:

- `handoff` → `review` = ready for the merge gate
- `handoff --block` → `blocked` = needs the human
- still `in-progress` = keep waiting

Poll every 30s. Combine with Step 1's claim refresh, which already runs once
per pass.

Your `<driver>` file adds one settle-detection mechanism on top of this poll —
a bounded fast path on herdr, a staleness heuristic on kitty. Apply it as
written there; the board above always decides whether a child settled.

On each settle (from the board, on either driver):

- **`blocked`** — every `blocked` is user-needed, never auto-answered.
  `notify` and `focus` that child:
  ```
  notify("kb-<child-id> blocked")
  focus(kb-<child-id>)
  ```
  This child stops consuming a fan-out slot but is **not** merged; other
  live children keep working. `pick` already withholds anything depending
  on it, so continuing is safe.
- **Handed off to `review`** (child released its claim, moved itself) — go
  to Step 5 (merge gate) for this child. It frees a fan-out slot only after
  the merge decision below.
- **Still `in-progress`** — leave it live and re-poll.

### Step 5: Merge gate (per handed-off child)

Follow **`merge-gate.md`** (in this skill's directory) with `<target-branch>`
= `<integration-branch>`. Other live children keep working while the user
decides — this is not a blocking gate on the whole coordinator, only on this
child's merge.

- **Approved** — merge-gate's merge and `--status done` free the fan-out
  slot; go back to Step 3.
- **Not approved** — the feedback comes back to you: relay it to the child by
  re-prompting the pane. If the pane already exited, move the child back to
  `todo` (`kanban-md move <child-id> todo`) so the next pass's `pick` sees it.
- **`wt merge` fails** — per `merge-gate.md`, additionally keep the parent
  claim. Do not touch other children's merges while this is open.

### Step 6: Needs-user children

A child tagged `needs-user` runs like any other. When it settles `blocked`
(waiting on the explicit human action the tag calls out), treat it exactly
like Step 4's `blocked` case — notify, focus, leave it live.

## Finished detection

`pick --parent <parent-id>` returning null is ambiguous — it means either
"all children done" or "remaining children are blocked on in-flight work."
Disambiguate explicitly:

```bash
kanban-md list --parent <parent-id> --json
```

The parent is done only when **every** child's status is terminal (`done`;
a `blocked` child left unresolved means the parent is *not* done — surface
it in the exit report instead of looping forever).

## Recursing into a sub-epic

If `<parent-id>` is itself a child of an outer coordinator: this coordinator
runs exactly as above, and when every child here is `done`, it hands off
`<parent-id>` in `review` per the exit contract — it does **not** merge its
own integration branch anywhere. The *outer* coordinator picks it up like
any other handed-off child in its own Step 5 and merges the sub-epic branch
onto the outer integration branch. Every coordinator merges its children;
none merges itself.

## Exit contract

| Ending | Action |
|---|---|
| All children merged | Test the integration branch, `kanban-md handoff <parent-id> --claim <agent> --release --note "<summary of merged children>"` to move it to `review`, report the branch, exit |
| A child is `blocked` | Already notified + focused; report it as outstanding, do not treat the parent as done |
| A child's review loop exhausts 3 cycles | Child hands off blocked with its last verdict block; handled identically to a `blocked` child |
| `wt merge` fails | Left open per `merge-gate.md`; report the path, keep the parent claim, ask the user |
| Coordinator dies | Parent claim expires in 1h and is reclaimable; `Integration branch:` and each child's `Branch:` line make the run resumable — re-invoke this file with the same `<parent-id>` |
