# kanban-workflow

Recursive kanban coordinator: works one task tree end to end, fanning out
parallel children into panes with a human gate on every merge. Driver-neutral
— herdr or kitty, selected at setup (see `SKILL.md`). See `SKILL.md` (entry
point), `kanban-parent-task.md` (parent/coordinator logic),
`kanban-leaf-task.md` (child/leaf logic), `branch-naming.md` (shared
branch/worktree naming rules), `merge-gate.md` (shared merge-decision flow),
`reviewing-changes.md` (per-axis reviewer briefs), `kanban_review.py`
(review rounds, checks, verdict, merge-gate report; tests in
`test_kanban_review.py`), `drivers/herdr.md` and `drivers/kitty.md`
(per-driver pane calls and settle detection), and
`docs/plans/implemented/2026-08-15-kanban-workflow-design.md` and
`docs/plans/implemented/2026-08-16-pane-driver-abstraction.md` for the
settled design decisions behind this shape.

Sibling skill `../jira-task` runs one Jira ticket as a leaf of this workflow,
ending in a Bitbucket PR.
