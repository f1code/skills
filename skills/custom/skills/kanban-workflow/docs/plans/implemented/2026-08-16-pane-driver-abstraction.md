# Pane driver abstraction: kitty as an alternative to herdr

## Goal

Let the kanban workflow run under plain kitty, not only herdr. Today six herdr
calls are hardcoded into `kanban-parent-task.md`; that file is the only place
in the skill that touches a multiplexer. Factor them behind a named "pane
driver" contract, implement a kitty driver, and replace the one operation kitty
cannot supply (`agent wait`) with board polling — which is better for both
drivers, because it survives a dead coordinator.

Non-goal: dropping herdr. herdr keeps real agent-lifecycle detection; kitty
does not. Both stay supported.

## Current herdr surface

All in `kanban-parent-task.md`:

| Line | Call | Purpose |
|---|---|---|
| 79 | `herdr agent get "$HERDR_PANE_ID"` | resolve coordinator's own agent kind |
| 139 | `herdr pane split --direction down --cwd <wt>` | create child pane |
| 140 | `herdr agent start kb-<id> --kind K --pane P` | launch agent in it |
| 146 | `herdr agent prompt kb-<id> "<text>"` | submit child prompt |
| 169 | `herdr agent wait kb-<id> --until idle --until blocked --until done` | settle signal |
| 177-178 | `herdr notification show … --sound request` + `herdr agent focus kb-<id>` | pull the human in |

`SKILL.md` and `kanban-leaf-task.md` reference herdr only in frontmatter
`allowed-tools` and prose; the leaf never calls it.

## Design

### 1. Driver contract

Five operations. Everything else in the skill stays multiplexer-agnostic.

| Op | Inputs | Output |
|---|---|---|
| `resolve-kind` | — | agent kind for children |
| `spawn` | worktree path, child name `kb-<id>`, kind, prompt | handle (pane/window id) |
| `focus` | child name | — |
| `notify` | title | — |
| `read-output` | child name | recent terminal text |

`wait` is deliberately absent. See §3.

### 2. kitty driver

`resolve-kind` — precedence:

1. `$KB_AGENT_KIND` if set (propagated by an outer coordinator, see `spawn`).
2. `kitten @ ls --self | jq -r '..|.foreground_processes?|arrays|.[].cmdline[0]'`
   → basename matched against the known kind list.
3. Ask the user.

`spawn` — one call replaces herdr's split+start+prompt. `launch` prints the new
window id on stdout:

```bash
win=$(kitten @ launch --type=window --location=hsplit --dont-take-focus \
  --cwd <worktree-path> --title kb-<child-id> \
  --var kb_task=<child-id> \
  --env KB_AGENT_KIND=<kind> \
  <kind-executable> "<filled prompt>")
```

Notes:

- Prompt goes as argv, not `send-text`. Removes the readiness race that
  `herdr agent start --timeout` exists to close — there is no "wait for the
  agent's prompt box" step because the agent is started *with* the prompt.
  Every supported kind takes a positional prompt.
- `--title kb-<child-id>` is the addressing key: `-m title:kb-<child-id>`.
  Uniqueness is already guaranteed by the `kb-<task-id>` naming rule.
- `--var kb_task=<child-id>` gives a second, agent-proof handle
  (`-m var:kb_task=<child-id>`); a child agent can retitle its own window,
  it cannot clear a user var.
- `--dont-take-focus` keeps the human's cursor where it was during fan-out.
- Record the printed window id in the child's task body next to `Branch:`, so a
  resumed coordinator can re-address panes.

`focus` — `kitten @ focus-window -m title:kb-<child-id>`

`notify` — `kitten notify --sound-name system --identifier kb-<child-id> \
  "kb-<child-id> blocked"`. Uses the escape-code channel, so it works even with
remote control off. `--identifier` makes repeat notifications replace rather
than stack.

`read-output` — `kitten @ get-text -m title:kb-<child-id> --extent=screen`

### 3. Settle detection: poll the board, not the terminal

kitty has no agent lifecycle state, and nothing in `kitten @` reports "waiting
on the human." So Step 4 of `kanban-parent-task.md` stops waiting on the pane
and waits on the board instead:

```bash
kanban-md list --parent <parent-id> --json
```

Every child state the coordinator acts on is already written to the board by
the child itself:

- `handoff` → `review` = ready for the merge gate
- `handoff --block` → `blocked` = needs the human
- still `in-progress` = keep waiting

Poll every 30s. Combine with the existing Step 1 claim refresh, which already
runs once per pass.

Why this is an improvement for herdr too: `herdr agent wait` is bound to a live
pane, so a coordinator restart loses every child. Board state is durable, so
re-invoking with the same `<parent-id>` reattaches.

What is genuinely lost under kitty: a child stalled at a shell permission
prompt never writes to the board and looks alive forever. herdr detects this
as `blocked`. Mitigation — a staleness heuristic, kitty only. A child is
*suspect* when all three hold:

- its board status has not changed, and
- its last progress note is older than 10 minutes, and
- `read-output` is byte-identical to the previous poll.

The progress-note clause is what keeps a long `go test` from tripping this:
the leaf already writes timestamped notes around major steps and test runs
(`kanban-leaf-task.md`, "Progress notes"), so recent activity exempts a child
that is simply busy.

On suspect, the coordinator does exactly two things: `notify` and `focus`. It
does **not** free the fan-out slot and does **not** touch the child's board
state. Staleness is a guess, not evidence the child is finished — freeing the
slot on a guess would spawn a 4th child alongside a still-live sibling and
break the single-writer property the 3-slot cap protects. The human looks at
the focused pane and decides. Notify once per suspect child, not once per poll:
`kitten notify --identifier kb-<child-id>` replaces rather than stacks, but
re-focusing every 30s would fight the user's cursor, so latch it.

The leaf's `allowed-tools` allowlist makes permission stalls uncommon; this is
a backstop, not the main path.

Board polling is a filesystem read, so it is identical under both drivers —
nothing in it depends on a pane existing. Under herdr it *composes* with
`agent wait`, kept as a fast path because it returns sooner than the next poll
tick. Two requirements for that composition:

- The wait must be bounded, or the coordinator blocks past its poll tick and
  never refreshes the parent claim: `herdr agent wait kb-<child-id> --until
  idle --until blocked --until done --timeout 30000 || true`. The current file
  passes no `--timeout`, i.e. waits forever. The `|| true` is required because
  a timeout exits nonzero, which here is the ordinary case, not an error.
- Its return is a *hint to re-read the board*, never a verdict. `--until idle`
  fires on Step 4's "idle with no handoff" case too, so the board is always
  what decides whether a child settled.

### 4. Driver selection

Once, in `SKILL.md` setup, alongside the existing board guard:

```bash
if [ -n "$HERDR_PANE_ID" ]; then driver=herdr
elif [ -n "$KITTY_LISTEN_ON" ]; then driver=kitty
else STOP — report that neither herdr nor kitty remote control is available
fi
```

No third driver. A serial in-context fallback was considered and rejected: it
is a third path to keep correct for no gain over the existing hard STOP, and
`SKILL.md` Step 3 already handles the one case that genuinely needs no pane
(a leaf invocation, implemented inline because one invocation claims one task).

If `KITTY_LISTEN_ON` is set but `kitten @ ls --self` fails, STOP with the
config fix below rather than falling through — a half-configured kitty should
not look like a missing one.

Pass `<driver>` to every recursive child as a parameter, next to `<agent>`.

## kitty config prerequisite

Currently unmet. `~/.config/kitty/kitty.conf` has remote control commented
out; `kitten @ ls` returns "RC_DISABLED" today. The escape-code channel is not
a fallback here — an agent's shell runs with `TERM=dumb` and no controlling
tty, so `kitten @` must reach kitty over a socket.

Add to `~/.config/kitty/kitty.conf`:

```
allow_remote_control socket-only
listen_on unix:/tmp/kitty
```

- `socket-only` refuses control over the tty escape channel, so a program that
  merely *prints* to a terminal cannot drive kitty. Only holders of the socket
  path can. Strictly tighter than `yes`.
- `listen_on unix:/tmp/kitty` — kitty appends the PID, giving one socket per
  instance. Children inherit `KITTY_LISTEN_ON`, which is what makes `kitten @`
  work from inside the agent and what §4 uses to detect the driver.

Requires a full kitty restart; `load-config` does not pick up `listen_on`.

Verify:

```bash
kitten @ ls --self >/dev/null && echo ok
```

Optional hardening, if the socket's default permissions are ever a concern on
a shared machine: add `remote_control_password "<pass>" launch focus-window
get-text ls` and pass `--password`. Skipped by default — the socket is already
mode 0600 and single-user.

## Proposed changes

| File | Change |
|---|---|
| `SKILL.md` | Add driver detection to setup (§4); pass `<driver>` to children; frontmatter `allowed-tools` gains `Bash(kitten *)`; description drops "herdr panes" for "parallel panes" |
| `kanban-parent-task.md` | New "Pane driver" section holding the three driver tables (§1-2); Step 3 fan-out calls driver ops, not herdr verbs; Step 4 rewritten to board polling (§3) + kitty staleness timer; Step 6 unchanged in intent, retargeted at driver `notify`/`focus`; `allowed-tools` gains `Bash(kitten *)` |
| `kanban-leaf-task.md` | Prose only: the coordinator "re-prompts this same pane" becomes driver-neutral. No behavior change — the leaf already calls no multiplexer |
| `README.md` | One line: driver-neutral, herdr or kitty |
| `docs/plans/implemented/2026-08-15-kanban-workflow-design.md` | Untouched. It is the record of a settled decision; this plan supersedes points 8, 29, 31 and is the new record |

## Resolved

1. **Fan-out cap stays 3** under both drivers. The limit is the human
   reviewing 3 merge gates, not pane geometry.
2. **No third driver.** Missing multiplexer stays a hard STOP (§4).
3. **Staleness gated on progress-note recency**, not a longer timer, and it
   only notifies + focuses — it never frees the slot or edits board state
   (§3).
