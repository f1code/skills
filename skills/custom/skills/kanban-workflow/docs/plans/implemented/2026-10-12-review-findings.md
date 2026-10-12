# Open review findings — multi-axis review plan

Findings from second Fable review of `2026-10-10-multi-axis-review.md`,
each checked by a separate Opus sub-agent. Already folded: 7 (exit
codes), b (reviewer read-only wording), 3 (prep rerun, HEAD drift).

Each finding: what breaks, a concrete scenario, the proposed fix, what
it costs. Annotate under **Decision**.

---

## 1. Repos without check commands can never pass review

**What the plan says now.** `prep` resolves check commands through a
fallback chain (`## Check commands` block → walk up → `make check` →
`make lint`/`test` → `go.mod`). If nothing matches, `check_source: none`
and `verdict` adds an **Important** finding under a `checks` pseudo-axis.

**What breaks.** The verdict rule turns any Important into
CHANGES_REQUESTED. The leaf can't fix this finding inside the task: the
fix is a project `AGENTS.md` edit, out of scope. Declining doesn't help
either: `verdict` recomputes it every round. Round 1, 2, 3 all fail →
leaf hands off blocked.

**Scenario.** Task on integrations-logics (no Makefile `check`, no
`lint`/`test` target matching, no `go.mod`, no `## Check commands`
yet). Code is fine, reviewers approve all four axes. Verdict still
CHANGES_REQUESTED, three times. Task blocked for a reason nobody can fix
from inside the leaf.

**Who is hit.** integrations-logics, prancer-study-logic, any repo with
neither Makefile targets nor `go.mod`. (gateway is fine: Makefile
`lint`/`test` exist.)

**Proposed fix.**
- Remove the Important finding from `verdict`. `gate` already prints
  `check source: none`, so you still see it at the merge gate.
- Put the pressure in `prep` instead: if `check_source: none` **and**
  `## Tests run` is empty → exit 3 ("no checks and no targeted tests;
  list tests you ran"). No round consumed. Leaf can satisfy it by
  listing targeted tests.

**Cost.** A repo with no checks can pass review on targeted tests alone.
That's the honest state of such a repo; the gate flags it.

**Decision:**
OK

---

## 2. Reviewers and scripts run in the wrong directory

**What the plan says now.** "Run in worktree" for `prep`/`verdict`;
`submit` finds the state dir via `git rev-parse --git-dir`; the reviewer
diffs `base..head`.

**What breaks.** Nothing puts anyone in the worktree.
- Inline leaf (SKILL.md "No children" path) runs from board home and
  creates the worktree with `wt switch --no-cd`. Its cwd stays at
  project root or `main/`.
- Sub-agents inherit the parent session's cwd. The Agent tool has no cwd
  parameter, so today's "spawn with cwd set to `<worktree-path>`" can't
  actually happen.
- Bash calls reset cwd between calls in sub-agents.

**Scenario.** Inline leaf on prancer. Leaf runs `prep` from
`~/prancer/main` → `git rev-parse --git-dir` = `main/.git` → round dir
created under `main/.git/kb-review/`, checks run against `main`'s code,
diff `base..HEAD` is `main`'s HEAD. Reviewers diff the wrong branch.
`submit` writes to `main/.git/kb-review/`. Everything "works" and
reviews the wrong code. From the untracked project root, `rev-parse`
fails loudly instead (better, but still broken).

**Proposed fix.**
- Leaf file writes every script call as
  `cd <worktree-path> && uv run <abs-path>/kanban_review.py …`.
- `prep` writes into each prompt file: the worktree path, the diff
  command as `git -C <worktree-path> diff <scope>`, and the full submit
  line `cd <worktree-path> && uv run <abs-script> submit <axis> <<'JSON'`.
- `submit` exits 3 when no open round exists in its git-dir; never
  creates one.
- `prep` and `verdict` check `git branch --show-current` equals the
  task body's `Branch:` line; mismatch → exit 3. Stops stale rounds in
  the wrong dir at the source.

**Cost.** Longer command lines in prompts. A `--worktree` flag would add
nothing over `cd`.

**Decision:**
OK

---

## 4. Carry-forward can trap a failing axis forever

**What the plan says now.** `prep` step "Scope per axis": round ≥2,
non-APPROVE axis → full diff plus previous findings; APPROVE axis → only
`prev_head..HEAD`. Then: "`prev_head == HEAD` → carry forward, no
reviewer." `verdict`: "Carried-forward axes keep N-1 result."

**What breaks.** The carry-forward sentence sits after both branches, so
it reads as applying to every axis.

**Scenario.** Round 1: complexity axis returns 3 Suggestions →
CHANGES_REQUESTED. Leaf disagrees with all three, writes `declined:
<reason>` for each, commits nothing (dispositions go to the task body,
not git). Round 2: `prev_head == HEAD` → complexity carried forward →
still CHANGES_REQUESTED. Round 3 same. Blocked. Declines can never win.

**Proposed fix.**
- Carry-forward applies only to APPROVE axes (their `prev_head..HEAD`
  scope is empty, nothing to review).
- Non-APPROVE axes always rerun, even when HEAD hasn't moved. The
  reviewer sees its previous findings and decline reasons; per `## Shared`
  it either drops a declined finding (accepts the decline) or re-raises
  it with a rebuttal.
- Same scoping in `verdict`: "Carried-forward (APPROVE) axes keep N-1
  result."

**Cost.** A decline-only round costs one of three rounds. Fair: it's the
leaf asking the reviewer to re-judge. Gate shows all dispositions, so
you see every decline.

**Decision:**
OK

---

## 5. Judgment calls shown twice at the merge gate

**What the plan says now.** Leaf writes `## Judgment calls` to body
before review. Handoff note: "verdict and round count". `gate`
concatenates every same-heading section.

**What breaks.**
- Current leaf file still has a `## Judgment calls` block inside the
  handoff `--note` template, and a `### Judgment calls` section saying
  "End every handoff note with…". The plan doesn't say to remove them.
  `kanban-md handoff --note` appends to the body (verified). An
  implementer keeping both → two `## Judgment calls` sections → gate
  shows every call twice.
- Fix rounds append more `## Judgment calls` sections. Concatenation
  keeps per-section order only, so "hardest to defend first" breaks
  across rounds. Calls a fix reversed stay listed.

**Scenario.** Round 1 leaf lists calls A (hardest), B. Round 2 fix adds
C (harder than A) and reverses B. Gate today would show A, B, C — wrong
order, stale B. Plus a duplicate A, B from the handoff note.

**Proposed fix.**
- Delete `## Judgment calls` from the handoff `--note` template; handoff
  note = `Ready for merge. Verdict: <v>, round <N>`.
- Repoint the leaf's "Judgment calls" prose from "handoff note" to the
  body section.
- Each appended `## Judgment calls` restates the **full current list**,
  hardest first. `prep` and `gate` read only the **last** section with
  that heading. Same rule for `## Tests run`.
- This is one exception to the plan's "concatenate all same-heading
  sections" rule; `## Finding disposition round N` and `## User
  feedback` (see #8) keep concatenating.

**Cost.** Leaf rewrites the list each time (short). Body keeps history.

**Decision:**
Folded as proposed (user: fold all findings).

---

## 6. Reviewer never sees the task body or the JSON shape

**What the plan says now.** Prompt file carries task id, scope, plan
path, standards files, judgment calls, tests, previous findings. Output
contract dropped from `reviewing-changes.md` ("schema owns it").

**What breaks.**
- Goal B promises reviewers get the task body. The prompt only has the
  task id. On trivial tasks with no `Plan:` line, the body **is** the
  spec — the spec axis has nothing to check against.
- The reviewer learns the JSON shape only when `submit` rejects its
  first attempt.

**Scenario.** Task "Fix 504 timeout banner" with a 10-line body of
acceptance criteria, no plan file. Spec reviewer gets task id 43 and a
diff. It could run `kanban-md show 43` itself, but nothing tells it to,
and the raw body also contains progress notes and earlier review blocks.
It writes findings in its own format; `submit` rejects; it guesses again.

**Proposed fix.**
- `prep` embeds task title + body in each prompt file, stripping every
  section the script owns or embeds separately (`Judgment calls`,
  `Tests run`, `Finding disposition round *`, `Review round *`,
  `User feedback`). Add a stripping case to the body-parsing tests.
- `prep` generates one literal JSON example from the **same schema
  constant** `submit` validates against — no hand-written copy to drift.
- `submit` prints that example when it rejects a result.
- Keep today's "not a rubber stamp; a clean non-trivial diff should be
  rare" line in `## Shared`.

**Cost.** Bigger prompt files; body is a snapshot at `prep` time — which
is the right moment (leaf just wrote judgment calls and tests).

**Open detail:** today's rule says `fix` required only on
Critical/Important. Schema should mirror that (`fix` optional on
suggestions) or say it's required everywhere.

**Decision:**
Agreed. `fix` optional on suggestions; plus leaf never edits spec, discoveries → judgment calls.

---

**Amended (round 3, #10):** example is a hand-written `EXAMPLE`
constant; a test asserts it validates. Same no-drift goal, no generator.

## 8. Round cap after you reject at the merge gate

**What the plan says now.** "Review loop, up to 3 rounds"; "third round
still CHANGES_REQUESTED → handoff blocked". Round number comes from the
state dir.

**What breaks.**
- Round dirs persist across a merge-gate "not approved" re-prompt. Next
  `prep` numbers it round 4. Is that round 1 of a new pass, or past the
  cap?
- Numbering drift: a re-prompted leaf counting its own loop writes
  `## Finding disposition round 1`; `prep` for script round 5 looks for
  `round 4`, finds nothing → reviewers never see dispositions.
- Your merge-gate feedback reaches the leaf by re-prompt only. Reviewers
  never see it, so nobody checks it got addressed.

**Scenario.** Rounds 1–2, APPROVE, handoff. You reject at the gate:
"rename X, and the retry logic is wrong". Leaf fixes, runs `prep` →
round 3. Reviewer approves the rename, misses the retry logic because
nobody told it. If round 3 fails, is the leaf blocked (3 total) or does
it get 2 more?

**Proposed fix.**
- Leaf counts the cap: ≤3 rounds per review pass; a pass restarts after
  a merge-gate re-prompt or a fresh pick. Script doesn't count passes
  (that would need handoff markers or timestamp parsing — more code, no
  gain).
- Script keeps global round numbers; `verdict` prints N and the literal
  heading to append: `## Finding disposition round N`. Leaf copies it,
  can't drift.
- Before re-entering the loop after gate feedback, leaf appends
  `## User feedback` with your words. `prep` puts it in every axis
  prompt; `gate` shows it.
- `gate` "Round count" → "rounds total / since last feedback".

**Cost.** One more body section. Leaf tracks pass count in its own
context (it already knows when it was re-prompted).

**Decision:**
Right.  Once there was a human review, reset the count.

---

## 9. `Preconditions:` line — cut, but GradeBee needs a Node step

**What the plan says now.** Check block format allows an optional
`Preconditions: <cmd>` line, run as `bash -c "<precond> && <cmd>"`.
Fable proposed cutting it: "no surveyed repo needs it".

**What the check found.** Fable's reason is wrong. GradeBee's
`AGENTS.md` (DoD step 1, lines 28–43) requires Node 24.13.x from
`.nvmrc`; Homebrew Node 25+ breaks jsdom `localStorage` in frontend
tests. Tested: a clean non-interactive `bash -c` gives Homebrew
`v26.9.0`; `fnm exec -- node -v` gives `v24.13.0`. fnm only
auto-switches through an interactive shell hook. Also the plan's own
example (`fnm use`) fails in `bash -c` without `eval "$(fnm env)"`.

**Proposed fix.**
- Cut the `Preconditions:` syntax anyway: an ordinary command line
  covers it.
- Plan states: environment wrappers go inline, e.g.
  `fnm exec -- make lint`, `fnm exec -- make test`.
- GradeBee needs a real `## Check commands` block: the Makefile fallback
  would run checks on the wrong Node. Update card #212: replace "Node
  version step → Preconditions" with inline `fnm exec --` lines.

**Cost.** None beyond the card edit.

**Investigation (674 sessions, Sep 12 – Oct 12).**
- Agents running `eval "$(fnm env)"; fnm use` always got v24.13.0. No
  deleted-symlink fallthrough, no persistence mistakes.
- Real cause: kitty-launched kanban sessions (`kitten @ launch`) start
  with kitty's environment, no `/opt/homebrew/bin` on PATH. 38 sessions
  (GradeBee, prancer worktrees) hit `command not found` for fnm, node,
  pnpm, npx, kanban-md, docker, uv; 2–4 probe calls each before adding
  `export PATH=/opt/homebrew/bin:$PATH`. One prancer session fell back to
  `zsh -lc` and ran `npm ci`/eslint/`ng test` on Homebrew v26.
- Oct 11: a session added `env.PATH` to `~/.claude/settings.json`
  starting with `/opt/homebrew/bin`. Fixed missing tools, but a fresh
  session then got `/opt/homebrew/bin/node v26.9.0` by default.

**Fixed (2026-10-12).** Prepended
`~/.local/share/fnm/aliases/default/bin` to `env.PATH` in
`~/.claude/settings.json` (backup `settings.json.bak-fnm`). Fresh
session now gets v24.13.0. Stable symlink, never cleaned up like
multishell ones; covers terminal- and kitty-launched sessions.

**Plan impact.** Script still wraps checks in `fnm exec --` when
`.nvmrc`/`.node-version` exists (exact per-project version; v20/v22
projects). No zsh/bash hook needed. kitty `--copy-env` not needed for
PATH.

**Decision:**
OK.  That's probably the case for every project using node.  Would it be possible to hook fnm into non-interactive bash?
It might be only installed for zsh right now
→ Resolved via `settings.json` `env.PATH` (see Fixed above).

---

## a. Reviewer's return line

**What the plan says now.** `kanban-reviewer.md`: "Return one line:
axis, verdict counts."

**What breaks.** The reviewer no longer computes a verdict — `verdict`
does. Asking for "verdict counts" invites it to compute one, possibly
disagreeing with the script. Also the current agent body says "Output
ONLY the review block … starting with the `verdict:` line"; the plan
updates the description but must remove that body rule entirely.

**Proposed fix.** "Return one line: axis, finding count per severity."
Delete the `verdict:`-line output rule from the agent body.

**Cost.** None.

**Decision:**
OK

---

## c. Leaf steps have checkable end conditions

**Finding.** Positive: each loop step ends on something checkable —
`prep` exit 0, `verdict` exit 0 with no missing axes, APPROVE or third
round, a disposition for every finding. Loop is ~6 lines; no sprawl.

**Proposed fix.** None.

**Decision:**
OK
