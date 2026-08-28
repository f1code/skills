# Close child pane on merge

## Goal

When the parent coordinator merges a handed-off child (Step 5, approved
path) in `kanban-parent-task.md`, close that child's pane/window instead of
leaving it running. Rejected/blocked children keep their pane live.

## Proposed changes

### `kanban-parent-task.md`

- **Pane driver op table**: add a sixth op, `close`, alongside
  `resolve-kind`/`spawn`/`focus`/`notify`/`read-output`. Input: child name
  `kb-<id>`. No output.

- **Step 3 (fan out)**: the existing instruction — "Record the returned
  handle (pane id or window id) in the child's body next to `Branch:`" —
  names the field explicitly: record it as `Pane: <handle>`. Required for
  resumability — the coordinator may die and be re-invoked per the existing
  exit contract, so the pane id can't live only in the loop's working
  memory, and `close` in Step 5 needs a concrete field to read back.

- **Step 5 (merge gate, approved branch)**: after merge-gate's merge and
  `--status done` free the fan-out slot, read `Pane: <handle>` from the
  child body (already fetched via `kanban-md show <child-id>` inside
  `merge-gate.md`) and call `close(kb-<child-id>)`. Swallow/log errors from
  this call (pane may already be gone, e.g. user closed it manually) —
  never fail the merge or block freeing the fan-out slot on a close
  failure.

- **Step 5 (rejected path)**: no change — pane stays live for re-prompting.

- **Step 4 (`blocked`)**: no change — pane stays live, coordinator keeps
  polling it.

- Prose tweak: in the "Approved" bullet under Step 5, note that the pane is
  closed before returning to Step 3.

### `drivers/herdr.md`

Add `close` to the op table: `herdr pane close <pane-id>`, using the
`Pane:` handle recorded in Step 3.

### `drivers/kitty.md`

Add `close` alongside `focus`/`notify`/`read-output`:
`kitten @ close-window -m title:kb-<child-id>`.

### `merge-gate.md`

No change — it stays driver-agnostic and knows nothing about panes; the
`close` call happens in `kanban-parent-task.md` after merge-gate returns
"Approved", not inside it.

### `kanban-leaf-task.md`

No change expected — leaves don't own pane lifecycle; the parent that
started them does.

## Open questions

None outstanding — confirmed acceptable that a bad merge or later
inspection needs manual pane resume rather than an automatic grace window.
