# kanban-workflow — settled design

Outcome of a grilling session. Locked decisions for rewriting `SKILL.md`
(plus `kanban-leaf-task.md`, `kanban-parent-task.md`) in this directory.

## Goal

A fourth, self-contained kanban skill — a new iteration of
`kanban-based-development` and `kanban-loop-development`, which stay untouched.
Its novelty over those two: **arbitrary-depth recursion into a task hierarchy**
and **parallel children in herdr panes**, with a human gate on every merge.

One invocation = one task tree. Recursion is manual per level; no draining of
the board.

## Verified facts (checked against installed tools)

- `pick` flag is `--tags` (plural, OR logic). `--tag` does not exist on `pick`.
- `pick --status` takes **one** status; `backlog,todo` is rejected.
- `pick` with `--tags` and no `--status` picks straight out of `backlog`.
- **`pick` enforces `depends_on` natively**: returns nothing while a dependency
  is unfinished; yields the task once the dependency is terminal. The skill
  needs no dependency logic.
- `wt merge` has **no `--no-cd`** (the current draft passes it — hard error).
  It merges *current* branch into target, so run it from the child worktree or
  with `-C <child-worktree>`.
- Merging into a branch that has its own worktree works; the source worktree and
  branch are auto-removed.
- **Concurrent `kanban-md` writes are safe** — 20 parallel appends to one task
  and 24 across two tasks lost nothing. The `kanban-based-development` warning
  against parallel mutation is obsolete and is not carried forward.
- **`kanban-md` discovers the board by walking upward** — resolved from
  `worktrees/probe/deep/deeper`. Under the standard layout the board is at the
  project root, outside the repo, and untracked (`git ls-files kanban` empty).
- `herdr agent start` needs an existing shell pane; `agent focus`,
  `notification show --sound request`, and `agent wait --until blocked` all exist.
- Board `claim_timeout` = 1h; expired claims are reclaimable.

## Decisions

### Shape

1. **Standalone skill.** No delegation to the older two.
2. **Arbitrary depth.** A task with children is *never* implemented directly;
   its children carry all the work.
3. **Coordinator implements a leaf inline** when the leaf is the task the
   invocation picked. Any leaf reached through recursion runs in a pane.
   (One invocation claims one task, so context pollution is moot.)
4. **No top-level loop.** After the tree is handled, report and exit.

### Concurrency

5. **Per-coordinator cap of 3** live children. No global cap — no atomic global
   counter exists in either tool, so a global cap would be a soft lie.
6. **Chains serialize for free.** `pick` withholds dependency-blocked children,
   so `#55 → #56 → #57 → #58` runs one at a time under the same code path that
   fans out 3-wide on independent children.
7. **Finished-detection:** `pick --parent` returning null is ambiguous
   (all done vs. remaining blocked on in-flight work). Disambiguate with
   `kanban-md list --parent <id>` — the parent is done only when every child is
   terminal.
8. Deferred enhancement: **one herdr tab per coordinator** (`tab create`, split
   inside it) to keep pane geometry sane on deep trees.

### Selection

9. **Status is the gate.** Coordinator promotes the parent's `backlog` children
   to `todo`, then `pick --claim <agent> --parent <id> --status todo --move
   in-progress`. Re-run promotion each pass, which also fixes the loop skill's
   "children added after setup are invisible" limitation.
10. **No `loop-<parent>` tag.** `--parent` scopes natively.
11. **`ready-for-agent` is ignored** by this skill. Filtering on it would
    deadlock the parent, whose completion requires *every* child terminal.
12. A `--status todo` filter is mandatory, not optional: a child that handed off
    to `review` releases its claim, so a tags-only pick would re-pick and
    re-implement work about to be merged.
13. **`needs-user` tag** marks a task needing explicit human action. It runs in
    a pane like any child; the coordinator waits `--until blocked`, then fires a
    notification and `agent focus` to route the user to that pane.

### Branches and worktrees

14. **The coordinator owns `wt` entirely** — creation and merge. Children never
    call `wt`; they receive `<worktree-path>` and only write code.
15. Naming precedence: documented project convention (`AGENTS.md` /
    `CONTRIBUTING.md`) → external ticket id → defaults.
16. Defaults: `epic/<id>-<slug>` for a task with children,
    `task/<id>-<slug>` for a leaf.
17. External ticket id read from a labelled `Ticket: <id>` body line, with
    `[A-Z]{2,}-\d+` as fallback. No sniffing of arbitrary body text — `ADR-0002`
    and `RFC-7231` would produce garbage branch names.
18. **No inference from `git branch` history.** Documented convention or the
    defaults; nothing in between.
19. A task's integration branch is cut from its parent's integration branch if
    there is one, else from the board-home branch. Child worktrees are cut from
    the integration branch **HEAD**, so each child inherits merged siblings.
20. Record `Integration branch: <name>` in the parent body and `Branch: <name>`
    in each child body when its worktree is created. These two lines are what
    make a crashed run resumable.

### Review and merge

21. **Child reviews itself**: reviewer sub-agent, `reviewing-changes.md`,
    verdict block appended to its own task body, bounded fix loop of 3 cycles.
22. **Fixed point is the merge-base**, `git merge-base HEAD <integration-branch>`
    — not integration HEAD, which moves as siblings merge and would show a
    child's diff minus a sibling's work.
23. **Every child merge is gated by the user.** The coordinator presents the
    child's verdict block plus `git diff --stat` against merge-base and waits
    for go-ahead before merging. Other children keep working in panes while the
    user decides.
24. **Children hand off unmerged.** Coordinator merges, one at a time, from
    board home via `-C <child-worktree>`. Single writer per integration branch:
    every merge is validated against the true tip, no non-fast-forward refusals,
    no pre-merge hook contention, no under-tested tips.
25. **No automatic upward merge past the invocation.** The named task's
    integration branch lands in `review` for the user.
26. **Intermediate epics do converge**: a sub-parent child hands off in `review`
    and its *outer* coordinator merges the sub-epic branch like any other child.
    Every coordinator merges its own children; none merges itself.

### Planning gate

27. **The named task is grilled**; recursive children are not. Evidence: the
    children of GradeBee #52 (#55–#58) already carry full specs, per-decision
    rationale, and checkbox acceptance criteria — they were authored through
    grilling. A child interview would only re-litigate settled decisions.
28. A child with no plan gets planner + oracle sub-agents; a genuinely blocking
    question becomes `handoff --block`, which stops that subtree and surfaces to
    the user at the right level.

### Agents and identity

29. **Children run the coordinator's own agent kind**, resolved from
    `herdr agent get "$HERDR_PANE_ID"`; ask only if unresolvable.
30. A **verbatim prompt template** in the skill carries the six child
    parameters. Improvised prompts are where this design leaks.
31. Child agents named `kb-<task-id>` — satisfies herdr uniqueness and makes
    `agent wait kb-56` trivial.
32. **Every `blocked` is treated as user-needed**: notify + focus, never
    auto-answered. An agent silently approving another agent's shell commands is
    an accountability gap. Consequence accepted: routine permission prompts also
    route to the user.

### Board access

33. **Parent task is claimed** by the coordinator, refreshed every poll cycle,
    and released on *every* exit path including errors — otherwise a crash locks
    the epic for an hour. The claim is what enforces one writer on the
    integration branch.
34. Parent sits in `in-progress` while children run; `review` is reserved for
    "waiting on the user".
35. **Children need no `--dir`.** Under the standard layout the board sits at
    the *project root* (`GradeBee/kanban/`), a sibling of `main/` and
    `worktrees/`, and is untracked by git — so it is not inside any worktree and
    cannot diverge per branch. `kanban-md` walks upward to find it, verified
    resolving correctly from three levels below the board. Child parameters stay
    at five.

    Guard, one line at coordinator setup: if the board dir is *inside* the repo,
    every worktree gets its own copy and diverges silently rather than erroring.
    In that case pass `--dir <board-dir>` to children.

## Exit contract

| Ending | Coordinator action |
|---|---|
| All children merged | Test the integration branch, `handoff <parent> --release` to `review` with a summary of merged children, report the branch, exit |
| Child hands off blocked | Notify + focus that pane; other children continue; that child is not merged |
| Child's review loop exhausts 3 cycles | Child hands off blocked with the last verdict block; handled as above |
| `wt merge` fails | Rebase conflict is left open in the child worktree; stop merging, report the path, keep the claim, ask the user |
| Coordinator dies | Claims expire in 1h; `Integration branch:` and `Branch:` body lines make resume possible |

A blocked child does **not** stop new launches: `pick` already withholds
children that depend on the blocked one, so continuing is safe.

## Fixes to the current draft

- `--tag ready-for-agent` → drop entirely (wrong flag name, wrong gate).
- `wt merge … --no-cd` → remove `--no-cd`.
- `epic/` vs `task/` inconsistency between `SKILL.md` and
  `kanban-parent-task.md` → resolve per decision 16.
- Remove `wt` from `kanban-leaf-task.md`; add `<board-dir>` as a sixth
  parameter; replace its self-merge (step 3) with handoff-and-stop.
- Typos: "usin", "it's body".

## Open questions

None.
