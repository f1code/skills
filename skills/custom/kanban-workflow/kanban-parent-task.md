---
name: kanban-parent-task
description: >
  Coordinate the children of a parent task: fan out up to 3 in parallel via
  herdr panes, gate every merge on the user, recurse into sub-epics.
allowed-tools:
  - Bash(kanban-md *)
  - Bash(kbmd *)
  - Bash(git *)
  - Bash(wt *)
  - Bash(herdr *)
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

## Provided parameters

`<parent-id>` and `<agent>` must be provided. `<board-dir>` (only if the board
guard in `SKILL.md` fired) is a third. **STOP** if `<parent-id>` or `<agent>`
is missing.

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
  else the current board-home branch. Create:
  ```bash
  wt switch --create epic/<parent-id>-<slug> --base <parent-branch> --no-cd --format json
  ```
  Record `Integration branch: epic/<parent-id>-<slug>` in the parent body.
  Return board-home to `<parent-branch>` (the coordinator does not work in
  this worktree — children's worktrees branch off its HEAD).

### Branch and worktree naming (used here and by leaves)

Precedence, applied once per task:

1. Project convention documented in `AGENTS.md` / `CONTRIBUTING.md`.
2. External ticket id: a `Ticket: <id>` body line, else `[A-Z]{2,}-\d+`
   matched against the body — never sniffed from arbitrary text (`ADR-0002`,
   `RFC-7231` would produce garbage).
3. Default: `epic/<id>-<slug>` for a task with children, `task/<id>-<slug>`
   for a leaf.

`<slug>`: first 3–4 meaningful words of the title, lowercased, spaces/punct
→ hyphens, max 30 chars.

## Agent kind for children

Resolve once:

```bash
herdr agent get "$HERDR_PANE_ID"
```

Use the returned kind for every child's `herdr agent start --kind <kind>`.
Ask the user only if this is unresolvable.

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

Count current live panes (children you started that haven't exited/handed
off yet). While fewer than 3 live and a pick succeeds:

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

1. Determine its `<branch-name>` (task/epic-<id>-<slug> per the naming
   rules above) and create its worktree **off the integration branch HEAD**,
   so it inherits every sibling merged so far:
   ```bash
   wt switch --create <branch-name> --base <integration-branch> --no-cd --format json
   ```
   Record `Branch: <branch-name>` in the child's body (or
   `Integration branch: <branch-name>` if the child itself has children).
2. Start it in a pane. `herdr pane split` always emits JSON; capture the new
   pane's id (`.result.pane.pane_id`, e.g. `wD:p2` — server-assigned, not
   derivable from `<child-id>`, so it must be read from this output, never
   guessed):
   ```bash
   new_pane_id=$(herdr pane split --direction down --cwd <worktree-path> | jq -r '.result.pane.pane_id')
   herdr agent start kb-<child-id> --kind <agent-kind> --pane "$new_pane_id"
   ```
3. Submit the verbatim prompt template (see below), substituting the six
   parameters — or five if the board is under the standard, out-of-repo
   layout (no `<board-dir>`):
   ```bash
   herdr agent prompt kb-<child-id> "<filled prompt>"
   ```

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
[Board directory: <board-dir>]
```

### Step 4: Wait on live children

```bash
herdr agent wait kb-<child-id> --until idle --until blocked --until done
```

Poll each live child. On each settle:

- **`blocked`** — every `blocked` is user-needed, never auto-answered. Fire
  a notification and focus that pane:
  ```bash
  herdr notification show "kb-<child-id> blocked" --sound request
  herdr agent focus kb-<child-id>
  ```
  This child stops consuming a fan-out slot but is **not** merged; other
  live children keep working. `pick` already withholds anything depending
  on it, so continuing is safe.
- **Handed off to `review`** (child released its claim, moved itself) — go
  to Step 5 (merge gate) for this child. It frees a fan-out slot only after
  the merge decision below.
- **`idle` with no handoff** — the child is between turns on something else
  (e.g. a `needs-user` tag task waiting on the human before its own
  handoff); leave it live and re-wait.

### Step 5: Merge gate (per handed-off child)

```bash
kanban-md show <child-id>
```

Present the user the child's verdict block (appended to its body) plus:

```bash
git -C <worktree-path> diff --stat $(git -C <worktree-path> merge-base HEAD <integration-branch>)..HEAD
```

Wait for explicit go-ahead. Other live children keep working while the user
decides — this is not a blocking gate on the whole coordinator, only on this
child's merge.

- **Approved** — merge from board home, one at a time (single writer on the
  integration branch: every merge validates against the true tip, so no
  non-fast-forward refusals, pre-merge hook contention, or under-tested
  tips):
  ```bash
  wt merge -C <worktree-path> -y <integration-branch>
  kanban-md edit <child-id> --status done
  ```
  This frees the fan-out slot; go back to Step 3.
- **Rejected / changes requested** — relay feedback to the child (re-prompt
  the pane) or, if the pane already exited, re-pick it next pass (it's back
  in `review`... actually it needs to go back to `todo` for `pick` to see
  it — move it explicitly: `kanban-md move <child-id> todo`).

If `wt merge` fails (rebase conflict): stop merging entirely, leave the
conflict open in `<worktree-path>`, keep the parent claim, report the path,
and ask the user. Do not touch other children's merges while this is open.

### Step 6: Needs-user children

A child tagged `needs-user` runs in a pane like any other. When it settles
`blocked` (waiting on the explicit human action the tag calls out), treat it
exactly like Step 4's `blocked` case — notify, focus, leave it live.

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
| `wt merge` fails | Left open per Step 5; report the path, keep the parent claim, ask the user |
| Coordinator dies | Parent claim expires in 1h and is reclaimable; `Integration branch:` and each child's `Branch:` line make the run resumable — re-invoke this file with the same `<parent-id>` |
