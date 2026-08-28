# Inline leaf path: drop the subtraction clause, extract shared reference

## Goal

`SKILL.md`'s inline-leaf branch reaches into the bodies of two files written
for a different caller, and patches one of them as it goes ("skip its
worktree-creation precondition — you just did that yourself",
`SKILL.md:142-143`). A pointer with a subtraction clause is unreliable: the
agent must load two files and mentally diff one against the instruction.

Fix the caller relationship rather than the pointer wording. Extract what two
callers share into sibling files, and make the inline-leaf path satisfy
`kanban-leaf-task.md`'s precondition instead of excusing itself from it.

Recursive sub-epic coordinators never read `SKILL.md` — the child prompt
template (`kanban-parent-task.md:205-206`) names only the parent and leaf
files. So shared material goes sideways into siblings, never up into
`SKILL.md`.

## Proposed changes

### New: `branch-naming.md`

Move `kanban-parent-task.md:60-72` verbatim — the ticket-id precedence list
and the `<slug>` derivation rule. Both the parent (per-child branches) and
`SKILL.md` (inline-leaf branch) need it; neither should own it.

Front matter: none needed — it is pointed-at reference, not an invocable
skill.

### New: `merge-gate.md`

Owns the merge decision, currently written twice
(`SKILL.md:144-154` and `kanban-parent-task.md:301-327` are the same four
moves against different target branches):

- Parameters: `<task-id>`, `<worktree-path>`, `<target-branch>`, `<agent>`,
  optional `<board-dir>`.
- Present the task's verdict block (already in its body) plus
  `git -C <worktree-path> diff --stat $(git -C <worktree-path> merge-base HEAD <target-branch>)..HEAD`.
- Wait for explicit go-ahead.
- On approval: `wt merge -C <worktree-path> -y <target-branch>`, then
  `kanban-md edit <task-id> --status done`.
- On `wt merge` failure (rebase conflict): stop merging, leave the conflict
  open in `<worktree-path>`, report the path, ask the user — verbatim from
  `kanban-parent-task.md:325-327`.

### `SKILL.md` — Step 3, leaf branch (currently lines 124-154)

Rewrite as: resolve `<parent-branch>` (unchanged, current step 1), create the
worktree per `branch-naming.md`, then bind the **same parameter block** the
fan-out passes (`<agent>`, `<parent-branch>`, `<worktree-branch>`,
`<worktree-path>`, `<task-id>`, optional `<board-dir>`) and follow
`kanban-leaf-task.md` unmodified — including its Step 2 handoff to `review`.
Then follow `merge-gate.md` with `<target-branch>` = `<parent-branch>`.

No subtraction clause, because the leaf's precondition
(`kanban-leaf-task.md:34-36`, "The coordinator already created
`<worktree-path>`… you only write code and hand off") becomes literally true.
The role switch happens at the file boundary: leaf until `review`,
coordinator after.

Keep the existing "no pane, implement inline" decision note (`:126-130`) —
that is the branch's real content and applies to the leaf portion.

Handing off to yourself is not ceremony: it creates the same resumability
waypoint the fan-out path has. A crash mid-run leaves the task in `review`
with its verdict block in the body — exactly the state Step 4 reports
(`SKILL.md:156-159`) and a re-invocation can resume. The current inline path
has no such waypoint.

### `kanban-parent-task.md`

- Delete `:60-72` (naming rules) → point at `branch-naming.md` from Step 3's
  branch-determination bullet (`:186-188`), and from Setup step 2's
  `epic/<parent-id>-<slug>` creation (`:52-56`).
- Step 5 (`:295-327`): replace the presentation/merge/conflict body with a
  pointer to `merge-gate.md` (`<target-branch>` = `<integration-branch>`).
  Retain only the parent-specific parts: "other live children keep working
  while the user decides" (`:307-309`), freeing the fan-out slot and
  returning to Step 3 (`:319`), and the rejected path — re-prompt the pane,
  or `kanban-md move <child-id> todo` if it already exited (`:320-323`).
- Exit contract row for `wt merge` failure (`:366`): repoint from "Step 5" to
  `merge-gate.md`.

### `kanban-leaf-task.md`

No change in this plan. Its dead `Task Slug` section (`:38-42`) and
duplicated output-contract fallback (`:110-113`) are separate deletions.

### `README.md`

Add `branch-naming.md` and `merge-gate.md` to the file list (`:5-8`).
The "Full-diff escalation at the merge gate" future improvement (`:14-21`)
now targets `merge-gate.md` rather than `kanban-parent-task.md` Step 5 —
update the reference. That extraction makes the improvement a one-place edit,
which is worth noting as the payoff.

## Non-goals

- Splitting driver reference out of `kanban-parent-task.md` (separate plan).
- Deleting the leaf's dead slug section and contract fallback (separate,
  pure deletions).
- Changing any board command, claim mechanic, or fan-out cap.

## Open questions

1. `merge-gate.md` and `branch-naming.md` have no front matter — confirm the
   loader tolerates plain reference files in a skill directory. The precedent
   is `reviewing-changes.md`, which has none and is loaded by path
   (`kanban-leaf-task.md:98-101`), so this should hold.
2. Does the inline-leaf handoff-to-self read as noise in practice? The
   resumability argument says keep it. If a run shows the coordinator
   hesitating at its own `review` gate, collapse it: skip the handoff and go
   straight to `merge-gate.md`, accepting no waypoint.
