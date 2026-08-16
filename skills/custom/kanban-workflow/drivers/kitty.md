# Driver: kitty

Implements the five pane-driver operations in `kanban-parent-task.md`.

## `resolve-kind`

Precedence:

1. `$KB_AGENT_KIND` if set (propagated by an outer coordinator's `spawn`).
2. `kitten @ ls --self | jq -r '..|.foreground_processes?|arrays|.[].cmdline[0]'`
   → basename matched against the known kind list.
3. Ask the user.

## `spawn`

One call does the whole job. `launch` prints the new window id on stdout:

```bash
win=$(kitten @ launch --type=window --location=hsplit --dont-take-focus \
  --cwd <worktree-path> --title kb-<child-id> \
  --var kb_task=<child-id> \
  --env KB_AGENT_KIND=<kind> \
  <kind-executable> "<filled prompt>")
```

Notes:

- Prompt goes as argv, not `send-text` — every supported kind takes a
  positional prompt, so there is no "wait for the prompt box" step.
- `--title kb-<child-id>` is the addressing key: `-m title:kb-<child-id>`.
  Uniqueness is guaranteed by the `kb-<task-id>` naming rule.
- `--var kb_task=<child-id>` is a second, agent-proof handle
  (`-m var:kb_task=<child-id>`); a child can retitle its own window, it
  cannot clear a user var.
- `--dont-take-focus` keeps the human's cursor where it was during fan-out.
- Record the printed window id in the child's task body next to `Branch:`,
  so a resumed coordinator can re-address panes.

## `focus`, `notify`, `read-output`

`focus` — `kitten @ focus-window -m title:kb-<child-id>`

`notify` — `kitten notify --sound-name system --identifier kb-<child-id> \
  "kb-<child-id> blocked"`. Uses the escape-code channel, so it works even
with remote control off. `--identifier` makes repeat notifications replace
rather than stack.

`read-output` — `kitten @ get-text -m title:kb-<child-id> --extent=screen`

## Settle detection: staleness heuristic

kitty cannot detect a child stalled at a permission prompt — it never writes
to the board and looks alive forever. A child is *suspect* when, across two
successive polls, all three hold:

- its board status has not changed, and
- its last progress note is older than 10 minutes, and
- `read-output` is byte-identical to the previous poll.

The progress-note clause keeps a long `go test` from tripping this: the leaf
already writes timestamped notes around major steps and test runs
(`kanban-leaf-task.md`, "Progress notes"), so recent activity exempts a child
that is simply busy.

On suspect, do exactly two things: `notify` and `focus`. Leave the fan-out
slot occupied and the child's board state untouched — staleness is a guess,
not evidence the child is finished; freeing the slot on a guess would spawn a
4th child alongside a still-live sibling and break the single-writer property
the 3-slot cap protects. The human looks at the focused pane and decides.
Notify once per suspect child, not once per poll — `notify`'s `--identifier`
replaces rather than stacks, but re-focusing every 30s would fight the user's
cursor, so latch it (skip `focus` on repeat suspect polls for the same child).

The leaf's `allowed-tools` allowlist makes permission stalls uncommon; this is
a backstop, not the main path.
