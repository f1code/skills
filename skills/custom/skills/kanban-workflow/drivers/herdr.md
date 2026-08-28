# Driver: herdr

Implements the five pane-driver operations in `kanban-parent-task.md`.

| Op | Call |
|---|---|
| `resolve-kind` | `herdr agent get "$HERDR_PANE_ID"` |
| `spawn` | `new_pane_id=$(herdr pane split --direction down --cwd <worktree-path> \| jq -r '.result.pane.pane_id')`, then `herdr agent start kb-<child-id> --kind <kind> --pane "$new_pane_id"`, then `herdr agent prompt kb-<child-id> "<filled prompt>"` |
| `focus` | `herdr agent focus kb-<child-id>` |
| `notify` | `herdr notification show "<title>" --sound request` |
| `read-output` | not used by this driver — herdr reports real lifecycle state instead |

## Settle detection: bounded fast path

The board poll in Step 4 stays authoritative. Compose it with this so the
coordinator can settle sooner than the next 30s tick, without blocking past it:

```bash
herdr agent wait kb-<child-id> --until idle --until blocked --until done --timeout 30000 || true
```

The `--timeout` is required — an unbounded wait would block the coordinator
past its poll tick and stall the parent-claim refresh. The `|| true` is
required because a timeout exits nonzero, which here is the ordinary case, not
an error. Its return is a hint to re-read the board, never a verdict:
`--until idle` also fires on the ordinary "idle, no handoff yet" case, so the
board is always what decides whether a child settled.

herdr detects a child stalled at a permission prompt directly, as `blocked`.
