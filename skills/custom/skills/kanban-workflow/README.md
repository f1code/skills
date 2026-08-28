# kanban-workflow

Recursive kanban coordinator: works one task tree end to end, fanning out
parallel children into panes with a human gate on every merge. Driver-neutral
— herdr or kitty, selected at setup (see `SKILL.md`). See `SKILL.md` (entry
point), `kanban-parent-task.md` (parent/coordinator logic),
`kanban-leaf-task.md` (child/leaf logic), `branch-naming.md` (shared
branch/worktree naming rules) and `merge-gate.md` (shared merge-decision
flow), `drivers/herdr.md` and `drivers/kitty.md` (per-driver pane calls and
settle detection), and
`docs/plans/implemented/2026-08-15-kanban-workflow-design.md` and
`docs/plans/implemented/2026-08-16-pane-driver-abstraction.md` for the
settled design decisions behind this shape.

## Possible future improvements

- **Full-diff escalation at the merge gate.** The merge gate
  (`merge-gate.md`) only presents `git diff --stat` against the merge-base —
  a file-list-and-line-count summary, not the actual patch. That's enough to
  skim size and shape, but hides renames-with-logic-changes and other
  content the user might want to inspect before approving. Add an explicit
  escalation path: on request, the coordinator runs
  `git -C <worktree-path> diff <merge-base-sha>..HEAD` (full patch, no
  `--stat`) and shares that instead of/alongside the summary. Because the
  merge gate is now a single shared file, this is a one-place edit that
  benefits every caller.
