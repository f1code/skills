---
name: kanban-workflow
description: >
  Default workflow for executing a kanban-md task tree: recurse into children,
  fan out parallel leaves into parallel panes, gate every merge on the user.
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

# Kanban Workflow

One invocation handles one task tree, to whatever depth it has. Recursion is
manual per level — the coordinator at each level launches its own children and
waits on them; there is no top-level loop draining the board. After the named
task's tree is fully handled, report and exit.

## Multi-Agent Environment

**This board is shared.** Multiple agents and humans may be working on it
simultaneously. Availability seen a moment ago may be gone. The **claim**
mechanic is the coordination primitive: claim before touching a task, and only
touch tasks you hold the claim on.

## Board Directory

The board sits at the project root (a sibling of `main/` and `worktrees/`),
untracked by git. `kanban-md` finds it by walking upward from the current
directory, so every worktree shares the one board and no `--dir` flag is ever
needed. A board tracked inside the repo would give each worktree its own
diverging copy — move it to the project root before running this skill.

**Driver guard, once at setup:**

```bash
if [ -n "$HERDR_PANE_ID" ]; then driver=herdr
elif [ -n "$KITTY_LISTEN_ON" ]; then
  kitten @ ls --self >/dev/null 2>&1 || { echo "STOP: KITTY_LISTEN_ON is set but kitten @ ls --self failed — fix kitty remote control (see README.md) rather than falling through"; exit 1; }
  driver=kitty
else
  echo "STOP: neither herdr (\$HERDR_PANE_ID) nor kitty remote control (\$KITTY_LISTEN_ON) is available"; exit 1
fi
```

Pass `<driver>` to every recursive child, next to `<agent>`.

## Agent Identity

```bash
kanban-md agent-name
```

Remember this as `<agent>`. Use it literally in every `--claim`/`--release`
for the rest of the session.

## Step 1: Pick the invocation task

If the user gave a task id, claim it directly:

```bash
kanban-md edit <task-id> --claim <agent> --status in-progress
```

Otherwise:

```bash
kanban-md pick --claim <agent> --status todo --move in-progress
```

If nothing is returned, **STOP** and notify the user. Note the id as
`<task-id>` and read it:

```bash
kanban-md show <task-id>
```

## Step 2: Plan gate (named task only)

This gate applies **only** to `<task-id>` itself — never to a recursive
child, which was authored with its own full spec, rationale, and acceptance
criteria at grilling time (re-interviewing it would just re-litigate settled
decisions).

Confirm:

- [ ] A plan is linked from the task body, or the body is itself a complete spec
- [ ] User has explicitly approved (e.g. "proceed", "go ahead", "implement")
- [ ] Open questions are answered

If not, run `/grilling` on `<task-id>` now. Do not create any worktree or
branch before this gate passes.

## Step 3: Does it have children?

```bash
kanban-md list --parent <task-id> --json | jq 'length'
```

### Children exist → this task is a parent

Follow **`kanban-parent-task.md`** (in this skill's directory) with
`<task-id>` as the parent. It drives the whole subtree: branch creation,
fan-out, review gating, and merges.

### No children → this task is a leaf, and it is the invocation itself

Decision: the coordinator implements this one leaf **inline**, in its own
context — no pane, because one invocation claims one task, so there is no
context-pollution risk. It still owns `wt` itself (leaves reached via
recursion never do; this is the one exception, since here the coordinator
*is* the leaf).

1. Determine `<parent-branch>`: if `<task-id>` has a parent, read
   `Integration branch: <name>` from the parent's body; otherwise it's the
   current board-home branch.
2. Create or reuse the worktree (see `branch-naming.md` for slug/naming
   rules):
   ```bash
   wt switch --create task/<task-id>-<slug> --base <parent-branch> --no-cd --format json
   ```
   Record `Branch: task/<task-id>-<slug>` in the task body. This is
   `<worktree-branch>`; the created path is `<worktree-path>`.
3. Bind `<agent>`, `<parent-branch>`, `<worktree-branch>`, `<worktree-path>`
   and `<task-id>`, and follow **`kanban-leaf-task.md`**
   unmodified — including its Step 2 handoff to `review`. Its precondition
   ("the coordinator already created `<worktree-path>`… you only write code
   and hand off") is satisfied by step 2 above.
4. Follow **`merge-gate.md`** with `<target-branch>` = `<parent-branch>`,
   which also marks the task `done` on approval.

Handing off to yourself is not ceremony: it creates the same resumability
waypoint the fan-out path has. A crash mid-run leaves the task in `review`
with its verdict block in the body — exactly the state Step 4 below reports,
and a re-invocation can resume from it.

## Step 4: Report and exit

No draining loop. Report what merged, what's in `review` waiting on the
user, and what's `blocked`. Exit.
