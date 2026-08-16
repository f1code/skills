# kanban-workflow

Recursive kanban coordinator: works one task tree end to end, fanning out
parallel children into panes with a human gate on every merge. Driver-neutral
— herdr or kitty, selected at setup (see `SKILL.md`). See `SKILL.md` (entry
point), `kanban-parent-task.md` (parent/coordinator logic, including the
pane driver contract), `kanban-leaf-task.md` (child/leaf logic), and
`docs/plans/implemented/2026-08-15-kanban-workflow-design.md` and
`docs/plans/implemented/2026-08-16-pane-driver-abstraction.md` for the
settled design decisions behind this shape.

## Possible future improvements

- **Full-diff escalation at the merge gate.** The merge gate
  (`kanban-parent-task.md`, Step 5) only presents `git diff --stat` against
  the merge-base — a file-list-and-line-count summary, not the actual patch.
  That's enough to skim size and shape, but hides renames-with-logic-changes
  and other content the user might want to inspect before approving. Add an
  explicit escalation path: on request, the coordinator runs
  `git -C <worktree-path> diff <merge-base-sha>..HEAD` (full patch, no
  `--stat`) and shares that instead of/alongside the summary.
