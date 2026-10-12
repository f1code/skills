# Multi-axis self-review and richer merge gate

## Goal

Make leaf self-review more thorough and give the user enough at the merge
gate to decide without opening the diff.

- **A.** Parallel reviewers, one per axis: spec, standards, complexity, ui.
- **B.** Reviewers get task body, linked plan, repo standards and the
  implementer's judgment calls.
- **C.** Check commands come from the project, not a hardcoded Go list.
- **F.** Merge gate shows verdict per axis, finding dispositions, judgment
  calls, check results, commits.
- Everything with one right answer runs as code: one Python script (run
  with `uv`) for git, checks, axis choice, result validation, verdict math
  and merge-gate report. Leaf agent spawns reviewers as its own sub-agents,
  so user can watch them. Agents keep implementing, reviewing, fixing and
  judging.

Out of scope: proving new tests fail without the change.

## Phases

1. Script, spec/standards/complexity axes, leaf rewiring, merge gate.
2. `ui` axis, static checks only.
3. `ui` screenshots via headless browser: split to board card #2
   (`~/.agents/kanban`).

## Design

### Split

| File (skill dir) | Kind | Job |
|---|---|---|
| `kanban_review.py` | Python, `uv run --script` | `prep`, `submit`, `verdict`, `gate` subcommands |
| `test_kanban_review.py` | pytest | verdict math, block and section parsing, schema, plus each rule marked *(test)* below |
| `reviewing-changes.md` | prose | `## Shared` + one `## Axis: <axis>` section each; severity model |
| `kanban-leaf-task.md` | prose | loop: implement → `prep` → spawn reviewers → `verdict` → fix + dispositions → repeat ≤3 → handoff |

Leaf spawns reviewers, not the script: they show as sub-agents in the
harness UI, and omp leaves use their own sub-agent tool. Script enforces:
`submit` validates each result, `verdict` refuses a round missing an axis.

State dir: `$(git rev-parse --git-dir)/kb-review/round-N/`: per worktree,
untracked, survives crashes. N = max(highest `round-N` in state dir,
highest `## Review round N` in body); open if `round-N` lacks
`verdict.json`, else N+1. Body term keeps N unique after worktree
recreation *(test: body round 2, empty state dir → round 3)*.

**Pass.** A pass = rounds sharing one `feedback_count` (number of
`## User feedback` sections in body). Previous round is *usable* when
`round-(N-1)/verdict.json` exists and its `feedback_count` equals the
body's; else the round runs as round 1 (full scope, no carry, no previous
findings), so gate feedback always gets a full review and a lost state
dir degrades safely *(test: both cases)*.

Exit codes, all subcommands: 0 ok; 3 expected failure the leaf can act on
(checks red, dirty tree, HEAD moved, missing axes, invalid submit). Any
other nonzero (1 traceback, 2 argparse, 127 no `uv`) → leaf hands off
blocked quoting stderr tail, no retry.

Header: `#!/usr/bin/env -S uv run --script` with PEP 723 block; stdlib
only, schema check by hand. Import-safe; tests run with `uv run --with
pytest pytest test_kanban_review.py`.

### Task body sections

Script reads `kanban-md show <task-id> --json` → `body`. A section ends
at next `^## `, next `^\[\[\d{4}-\d{2}-\d{2}\]\]` stamp line, or EOF. A
`-t` append puts its stamp before its heading, so every body append
(progress notes included) carries `-t` *(test: stamped note after
`## Judgment calls` and after `## User feedback` stays out of both)*.

- **Last wins:** `## Judgment calls`, `## Tests run`. Each new section
  restates the full list (judgment calls hardest to defend first).
- **Concatenate** in body order: `## Finding disposition round N`,
  `## User feedback`.

| Heading | Written by | Read by |
|---|---|---|
| `## Judgment calls` | leaf, before review | `prep` (prompts), `gate` |
| `## Tests run` | leaf, before review | `prep` (replays) |
| `## Finding disposition round N` | leaf, after fixes (heading copied from `verdict` output) | `prep` (prompts), `gate` |
| `## User feedback` | merge gate on not approved; leaf on re-prompt | `prep` (every prompt, pass), `gate` |
| `## Review round N` | `verdict` | user; `gate` reads JSON instead |

Fenced block format (`## Check commands`, `## Tests run`): first fenced
bash block in the section, one command per line, text before `#` is the
command. `## Tests run` with no fence may instead hold a `none: <reason>`
line (research/prototype tasks). Environment wrappers go inline:
`fnm exec -- make lint`, `cd prancer_frontend && fnm exec -- npm test`.

### `kanban_review.py prep <task-id> <parent-branch>`

Leaf runs it as `cd <worktree-path> && uv run <skill-dir>/kanban_review.py
prep …`: sessions and sub-agents don't start in the worktree.

1. Branch: `git branch --show-current` ≠ body `Branch:` (first line
   matching ``^\W*Branch:\s*`?([^\s`]+)``, trailing `.,;:` stripped), or
   no such line → exit 3. Helper shared with `verdict`.
2. Dirty tree (`git status --porcelain`, untracked included) → exit 3.
3. Open round: keep submitted `<axis>.json` when stored `prep.json` has
   same `head` and `feedback_count` as now (crash resume); else wipe the
   round dir.
4. `base = git merge-base HEAD <parent-branch>`; `files = git diff
   --name-only base..HEAD`.
5. Run checks (below). Failure, or tree dirty afterwards ("checks modified
   files: <list>; commit or gitignore them") → exit 3, no round dir
   *(test)*.
6. Axes:

   | Axis | Runs when |
   |---|---|
   | spec | always |
   | standards | always |
   | complexity | always |
   | ui (phase 2) | any file matches `*.css *.scss *.less *.html *.tsx *.jsx *.vue *.svelte`, excluding `*.test.*`, `*.spec.*` |

7. Scope: `base..HEAD`, except with a usable previous round an axis it
   approved gets `prev_head..HEAD` (`prev_head` = its `head`); if that
   scope fails the axis trigger (always for empty diff) the axis carries,
   no reviewer. Non-APPROVE axes always rerun, even on unchanged HEAD:
   reviewer re-judges declines *(test: carry chain keeps K; non-APPROVE
   on `base..HEAD`; feedback with same HEAD schedules all)*.
8. Write `round-N/prep.json` `{task_id, round, base, head, prev_head,
   feedback_count, axes, carried, scopes, checks, check_source}` (`axes` =
   reviewed axes only; `carried` = `{axis: K}`, K = round whose reviewer
   approved) and `<axis>.prompt.md` per axis in `axes`. Print round
   number, then axes lacking `<axis>.json` with prompt paths.

**Checks**, every round, cwd = worktree. One 9-min deadline over all:
`Popen(..., start_new_session=True)` + `communicate(timeout=remaining)`;
on timeout `os.killpg(p.pid, SIGKILL)` + `p.wait()` (`shell=True`
children like `npm` survive otherwise), exit 3 `timed out: <cmd>
(<source>)`. Failure print: exit code and last 50 lines.

- Repo checks, first source wins:
  1. `## Check commands` block in worktree `AGENTS.md`, else `CLAUDE.md`.
  2. Same, walking up to `$HOME` (untracked project-root `CLAUDE.md`,
     prancer).
  3. `Makefile` `check` → `make check`.
  4. `Makefile` `lint`/`test`.
  5. `go.mod` → `go test ./...` + `golangci-lint run ./...`.
  6. None → `check_source: none`, no finding (leaf can't fix it; `gate`
     shows it). Also no `## Tests run` → exit 3 "no checks and no
     targeted tests".
- Targeted tests: every `## Tests run` command. Docker compose keys on
  directory, so `docker-compose exec` from the worktree hits that
  branch's container.

Repo checks hold cheap whole-repo commands; slow suites go in
`## Tests run` as a narrower subset.

**Prompt file** `<axis>.prompt.md`:
- axis, task id, title, body minus script-read sections;
- worktree path; diff command `git -C <worktree-path> diff <scope>`;
- standards file paths: existing of `AGENTS.md`, `CLAUDE.md`,
  `CONTRIBUTING.md`, `CODING_STANDARDS.md`, `docs/agents/*.md`, plus
  `CLAUDE.md` walked up;
- user feedback, judgment calls, checks and tests run (or `none:
  <reason>`);
- this axis's findings from round N-1 only if it was non-APPROVE there,
  plus every `## Finding disposition round *` section verbatim (reviewer
  matches `<axis>#<k>`; no parsing) *(test: APPROVE rerun gets none)*;
- "Read `## Shared` and `## Axis: <axis>` in
  `<skill-dir>/reviewing-changes.md`";
- submit line `cd <worktree-path> && uv run <skill-dir>/kanban_review.py
  submit <axis> <<'JSON'` and `EXAMPLE` (one important finding with
  `fix`, one suggestion without) *(test: validates; fails without `fix`)*.

### `kanban_review.py submit <axis>`

Reviewer pipes JSON on stdin. Schema `{strengths: [str], findings:
[{severity: critical|important|suggestion, file, line: int|null, what,
why, fix}]}`; `line` key required; `fix` required on critical/important.
Axis from argv only. Writes `round-N/<axis>.json`. Invalid → exit 3 with
errors and `EXAMPLE`. No open round → exit 3; never creates one.

### `kanban_review.py verdict --claim <agent>`

`cd <worktree-path> && uv run …`. Same branch check as `prep`.

- `HEAD != prep.json.head` → exit 3 "rerun prep".
- Axis in `axes` with no result → exit 3 naming them.
- Per axis: ≥1 Critical, ≥1 Important or ≥3 Suggestion →
  CHANGES_REQUESTED. Combined = worst. Carried axes copy round K's result
  with `carried_from: K`.
- Writes `round-N/verdict.json` `{round, verdict, head, feedback_count,
  axes: {<axis>: {verdict, counts, scope, strengths, findings,
  carried_from?}}, checks, check_source}`.
- Appends `## Review round N` block (`kanban-md edit <id> -a … -t
  --claim <agent>`) and prints it. Findings numbered per axis (`spec#1`);
  carried axes show `APPROVE (round K, not rerun)`. No line after the
  first may start `## `: sub-headings `###`, reviewer strings render with
  continuation lines indented two spaces, no escaping *(test: `fix`
  containing `\n## User feedback\nx`, strength containing `\n## x`)*.
- Prints the heading for the leaf: `## Finding disposition round N`.

### `kanban_review.py gate <task-id> <worktree-path> <target-branch>`

Path arg: orchestrator calls it, worktree may be gone.

Reads `verdict.json` of highest N (numeric sort) that has one. Headers:
`STALE: verdict at <sha>, HEAD <sha>` when they differ (covers open later
round, commits after approval, wrong branch); `DIRTY` when worktree has
uncommitted changes (`wt merge` would commit them unreviewed); `NOT
REVIEWED` when no `verdict.json` (body sections only, exit 0). Git lines
skipped if worktree gone. Prints:

- Combined and per-axis verdict with scope, findings.
- Finding dispositions, judgment calls, user feedback.
- Checks and tests run (or `none: <reason>`), check source.
- Rounds: total, and in current pass.
- `git log --oneline <merge-base>..HEAD` and `diff --stat`.

### `reviewing-changes.md`

Restructure as `## Shared` plus `## Axis: <axis>` sections.

- `## Shared`: read prompt file inputs; diff for the given scope; severity
  model. Read-only: Read/Grep/Glob, `git diff`/`log`/`show`; only write
  is `submit`; never fetch/rebase/edit. Previous findings: `fixed <sha>`
  → verify, re-raise if not fixed; `declined` → omit, or re-raise
  rebutting the reason. Keep "not a rubber stamp; a clean non-trivial
  diff should be rare". Drop output contract, "run the checks" step,
  "failing tests/lint" from Critical, "All tests passing?" from Testing
  checklist.
- `## Axis: spec`: brief from `~/.agents/skills/code-review/SKILL.md`
  Spec sub-agent: missing/partial requirements, unasked behaviour, wrong
  implementation; quote task/plan line. Plan = body's link, else body.
  Challenge each judgment call.
- `## Axis: standards`: brief from `code-review` Standards sub-agent;
  smell baseline: read its step 3 (no copy). Repo standards override.
  Keep current checklist (error handling, locks across I/O, test names vs
  assertions, new public surface covered). Changed behaviour no test
  exercises → Important. `none: <reason>` → Important only when the
  reason doesn't hold (e.g. production code labelled prototype).
- `## Axis: complexity`: ponytail-review rubric. Important only for new
  dependency, unused abstraction/parameter, reimplemented stdlib/helper.
- `## Axis: ui` (phase 2): hardcoded colors/sizes vs tokens, dark mode,
  contrast, focus/keyboard, semantic HTML, labels/alt, phone width,
  layout shift, consistency with neighbours.

### `~/.agents/agents/kanban-reviewer.md`

(`~/.claude/agents` symlinks here.) Tools, model unchanged. Replace body:

> Prompt names a prompt file; read it. Read-only: Read/Grep/Glob,
> `git -C <worktree> diff/log/show`; only write is `submit`. Never
> fetch/pull/rebase/merge/cherry-pick or edit files; wrong-looking base
> is a finding. Exit 3 → fix JSON, resubmit. Other failure → stop, quote
> stderr tail. Return one line: axis, finding count per severity.

Update `description:` to match.

### `kanban-leaf-task.md`

Edit pre-compression source (`git show b4b3eb5^:…/kanban-leaf-task.md` in
`~/.agents`), then rerun `/caveman-compress`.

- Drop `go`/`golangci-lint` from `allowed-tools` (no effect when passed
  as prompt).
- Body append-only (`-a … -t`), never `--body`. Approach-changing
  discovery → judgment call: plan said, found, did, cheapest undo. Spec
  wrong in a way the leaf shouldn't decide → handoff blocked.
- Before review, append `## Judgment calls` and `## Tests run`; when
  fixes change either, append a restated one.
- Delete `## Judgment calls` from handoff `--note` template; repoint
  "End every handoff note with…" to the body section.
- Step 2 Definition of Done includes `prep` green.
- **Entry** (fresh pick or any re-prompt). New user words not already the
  newest `## User feedback` → record them first:

  ```bash
  kanban-md edit <task-id> --claim <agent> --status in-progress --unblock \
    -a "$(cat <<'EOF'
  ## User feedback
  <user words>
  EOF
  )" -t
  ```

  (quoted heredoc keeps `'`, `$`, backticks literal; no stdin flag.) Leaf
  writes it: parent never sees pane input. Then: body has no `## Review
  round` → Step 1 (continue where stopped); else review loop step 1,
  pass round 1.
- Review loop, ≤3 rounds per pass; leaf counts, script numbers.
  Any script exit other than 0/3 → handoff blocked with stderr tail.
  1. `prep` with the Bash tool's max timeout (Claude Code `timeout:
     600000`). Exit 3 → fix what it names (`## Tests run` timeout →
     narrow it; repo-check timeout → handoff blocked), rerun.
  2. Progress note `review round <N>: <axes>` (keeps kitty staleness
     check quiet).
  3. Spawn one `kanban-reviewer` per listed axis in one message, prompt
     "Follow `<prompt-path>`". No such type (omp) → general-purpose on
     strongest model, prompt also names `~/.agents/agents/kanban-reviewer.md`.
  4. `verdict --claim <agent>`. Missing axes → respawn once, rerun; again
     → handoff blocked. "rerun prep" → step 1.
  5. APPROVE → handoff. Round 3 of pass → handoff blocked `--block
     "review round N CHANGES_REQUESTED"`, no fixes or dispositions. Else
     fix, append printed disposition heading, one line per finding on
     non-APPROVE axes: `- <axis>#<k>: fixed <sha>` or `- <axis>#<k>:
     declined: <reason>`; next round. Drop "with the last verdict block"
     from current bounded-fix-loop text.
- Handoff note: `Ready for merge. Verdict: <v>, round <N>.` only.

### `SKILL.md`, `kanban-parent-task.md`

- `SKILL.md`: drop `go`/`golangci-lint` from `allowed-tools`.
- `SKILL.md` inline path (Step 3, no children): merge gate `<claimant>` =
  `<agent>`; "Not approved → follow `kanban-leaf-task.md` Entry."
- `kanban-parent-task.md` Step 5: merge gate `<claimant>` =
  `kb-<child-id>`. Exited-pane branch: `kanban-md edit <child-id>
  --release --status todo` (`move` fails on a claimed task).
- `kanban-parent-task.md` line 259: "Child hands off blocked after 3
  review rounds; verdict in body; handle as any `blocked` child;
  re-prompt follows leaf Entry."

### `drivers/kitty.md`

- Line 74: remove claim that leaf `allowed-tools` prevents permission
  stalls; panes run in auto mode.

### `merge-gate.md`

Runs `kanban_review.py gate …`, presents output, offers earlier rounds
and full patch on request. New `<claimant>` parameter (identity that
resumes the work). Not approved, one write, then return to caller:

```bash
kanban-md edit <task-id> --claim <claimant> --status in-progress --unblock \
  -a "$(cat <<'EOF'
## User feedback
<words>
EOF
)" -t
```

Boards set `require_claim` on `review`/`in-progress`; status reset stops
parent poll re-gating a re-prompted child. Approved: `kanban-md edit
<task-id> --release --status done`. Rest unchanged.

### `README.md`

- Drop "Full-diff escalation" future item; list new files.

### Project `AGENTS.md` convention (per-project edits, not this repo)

Survey of 10 recent projects: check commands in 7 under 6 headings; no
start command; DoD in 5. Every Python repo wraps checks in `make`.

````markdown
## Check commands

Run from repo root. All must pass.

```bash
make lint        # lint
make typecheck   # typecheck
make test        # test
```


## Start command

```bash
make dev         # http://localhost:5173
```

## Definition of Done

- All check commands pass
````

Makefile `check` only in edw, data-hub; `lint`/`test` in GradeBee,
prancer-integrations, gateway. prancer has neither, so its block goes in
untracked `~/prancer/CLAUDE.md` (Claude Code loads parent `CLAUDE.md`,
not `AGENTS.md`). Makefile fallback covers the rest meanwhile.

## Resolved

- Panes run in auto mode; no allowlist work.
- Reviewer results via `submit`, not Write tool.
- Red checks block `prep`; review starts only on green.
- Node: `~/.claude/settings.json` `env.PATH` starts with fnm default
  alias bin (done 2026-10-12); other pins inline `fnm exec -- …`.
- Review rounds 2-7: all folded except loop round 5 #5 (rejected); see
  `2026-10-12-review-findings.md`, `2026-10-12-review-loop-log.md`.
  Hand-written `EXAMPLE` + test replaces example-from-schema.
- Simplification pass after review loop: 529 → 412 lines; merged
  pass reset + lost state dir + previous-findings gating into one
  "usable previous round" rule; leaf resume paths (fresh pick, gate
  rejection, blocked, round-3 block, exited pane, inline) into one Entry
  rule keyed on body `## Review round`; `verdict` heading/indent rules
  into one "no `## ` after first line" invariant; two dirty-tree exits
  into prep step 5; test list into *(test)* marks; review-round bullets.
- Cut: nested per-directory `## Check commands`, per-axis model override,
  copied Fowler list, gate parsing review blocks from body, Workflow tool
  and `claude -p` fan-out.
- Browser axis: own card (#2).
- Tests: repo checks (cheap, whole repo) plus targeted tests chosen by
  implementer, replayed by script.
- Project `AGENTS.md` migration: one card per project, own board
  (`agents-md` tag): GradeBee #212 (block lines `fnm exec -- make lint`,
  `fnm exec -- make test`; card L21 still says script auto-wraps, fix
  it), edw #19, data-hub #93, prancer-integrations #31, shared-packages
  #14 (root block with `cd <pkg> && …` lines), prancer #45. No board yet:
  gateway, integrations-logics, prancer-study-logic.

## Open questions

None.
