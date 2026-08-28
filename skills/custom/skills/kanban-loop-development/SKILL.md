---
name: kanban-loop-development
description: >
  Autonomous, sequential loop that processes the `todo` children of a required parent task,
  merging each completed child onto a shared integration branch.
  A parent task ID is required.
allowed-tools:
  - Bash(kanban-md *)
  - Bash(kbmd *)
  - Bash(git *)
  - Bash(go *)
  - Bash(golangci-lint *)
  - Bash(awk *)
  - Bash(date *)
disable-model-invocation: true
---
<!-- kanban-md-skill-version: 0.34.0 -->

# Kanban Loop Development

Autonomous, sequential loop that processes the `todo` children of a required
parent task, merging each completed child onto a shared integration branch. The loop does not pause
for plan approval or per-task merge decisions. The only user handoff is at
the very end: final merge of the integration branch into the starting board home
branch.

Tasks are treated as **sequentially dependent** — task B may depend on task A.
A single blocker stops the entire loop. No skipping ahead.

## Multi-Agent Environment

**This board is shared.** Multiple agents and humans may be working on it simultaneously.

- Another agent may claim a task between the time you list it and pick it; availability you saw moments ago may be gone.

The **claim** mechanic is the coordination primitive. **You MUST claim a task before starting any work on it. You MUST only pick unclaimed tasks.**

## Non-Negotiables

- **A parent task ID is required.** Refuse to start without one; never auto-create a parent.
- **Claim the parent at setup and refresh it every iteration.** A live (non-expired) claim by another agent means another loop owns it — stop and surface the conflict.
- **The loop only reads task hierarchy.** It never sets the structural `--parent` field; the `loop-<parentID>` tag is the sole selection mechanism.
- **Claim before you change anything.** No task edits, no code changes.
- **Write a plan before you build.** Plans are for audit — they do NOT require user approval. Auto-proceed after writing and linking.
- **One active task per loop iteration.** Do not pick the next task until the current one is merged or the loop is stopped.
- **Never steal a live claim.** If a task shows a claim by a different agent, stop immediately and surface the conflict to the user.
- **Always leave the board accurate.** Parent task and sub-tasks must reflect actual state at all times.
- **The loop never touches the starting, board-home branch.** All sub-task merges target the integration branch only (loop/*).
- **Review cycle max = 3.** After 3 consecutive CHANGES_REQUESTED on one task, stop the entire loop.
- **Refresh claims to avoid timeout.** For long tasks: `kanban-md edit <ID> --claim <agent>`.
- **On unexpected failure mid-task: release the claim.** If anything between Steps 2–5 fails unrecoverably, run `kanban-md handoff <ID> --claim <agent> --block "<reason>" --timestamp --release` before stopping. Never leave a dead claim on the board.

## Trivial Task

Several rules below relax for trivial tasks. A task is **trivial** only if it is one of:

- a typo fix
- a single-line code change
- a comment- or doc-only edit
- a board-only change

Touching more than one file of tracked code, changing a function signature, API, or schema, or modifying tests as the primary change is **not** trivial. If unsure, it is not trivial.

## Board Home vs Worktrees

- **Always run `kanban-md` from board home** (the canonical repo directory that owns the shared board).
- **Always do code changes in a task worktree.** Never edit code in board home.
- If the board is git-tracked, **commit board changes on starting, board-home branch as a separate commit** after the integration branch is merged.

At the start of the session, capture `<board-home>` as the current working directory.

## Slug Derivation

Several places require a `<slug>`. Derive it from the relevant title or goal:
take the first 3–4 meaningful words, lowercase, replace spaces and punctuation with hyphens, max 30 chars.
Example: "Refactor user auth flow" → `refactor-user-auth`.

## Agent Identity

Generate a unique name at the start of the session:

```bash
kanban-md agent-name
```

Remember this name in your context as `<agent>`. Use it as a literal string in all claim/release commands for the rest of the session.

## Locating the review instructions

Step 5a hands the reviewer sub-agent a review-instructions file that ships
beside this `SKILL.md`. At session start, resolve its path from wherever this
skill is installed (do not hardcode) and remember it:

```
<reviewing-changes-file> = <this-skill-directory>/reviewing-changes.md
```

If the file is missing (partial install), the reviewer falls back to the inline
format in Step 5a.

## Expected Review Block Format

Self-review sub-agents must return a block in this format (the loop parses the `verdict:` line):

```
verdict: APPROVE
counts: critical=0 important=0 suggestion=2
<!-- or -->
verdict: CHANGES_REQUESTED
counts: critical=1 important=2 suggestion=1

## Strengths
- <specific, file:line where possible>

## Findings
1. [CRITICAL]   <description of issue>
2. [IMPORTANT]  <description>
3. [SUGGESTION] <description>
...
```

The verdict is CHANGES_REQUESTED if there is any Critical, any Important, or 3+ Suggestion findings; otherwise APPROVE (see `reviewing-changes.md` for the full rule). The loop acts on the verdict line only; on CHANGES_REQUESTED the fix step addresses the findings listed in the block.

---

## Phase 0: Setup

The loop requires an existing parent task. If the user did not supply a parent
task ID, stop and ask for one — do not invent or auto-create a parent.

1. **Board home.** From `<board-home>`, confirm a clean tree and remember the
   current branch as `<home-branch>`. The integration branch is cut from it and
   the final merge targets it.

2. **Plans dir.** Resolve from project or global conventions, store path relative to <board-home> in
   `<plans-dir>`.

3. **Read the parent.** `kanban-md show <parent-ID>`.

4. **Claim guard (prevents two loops on one parent).** Attempt the claim:
   `kanban-md edit <parent-ID> --claim <agent>`. 
   On error, **STOP** and report that another loop owns parent #<parent-ID>. Do not steal.

   (Claim TTL is 1h, so a prior session's expired claim reclaims cleanly.)

5. **Integration branch.** Scan the parent body for an `Integration branch: <name>` line.
   - Found → use it as `<integration-branch>`; confirm it exists locally, fetching
     if needed. If it exists nowhere, stop and ask.
   - Not found → create `loop/<YYYY-MM-DD>-<slug>` off `<home-branch>` (slug from
     the parent title), return to `<home-branch>`, and backfill the
     `Integration branch:` line into the parent body.

6. **Activate the parent.** Move it to `in-progress` (claimed by `<agent>`) and
   append a timestamped `Loop (re)started by <agent>.` note.

7. **Tag the children (selection scope).** Tag every current `todo` child of the
   parent with `loop-<parent-ID>` — one `edit` call with the comma-separated child
   IDs from `kanban-md list --parent <parent-ID> --status todo`. This tag is what
   the atomic `pick` filters on; re-running it on resume is idempotent.
   - If the parent has **no** `todo` children, report "nothing to do" and stop cleanly.

> The loop never sets the structural `--parent` field — children are already
> parented (that is how they are listed). The tag is purely for atomic selection.
>
> **Known limitation:** children added under the parent *after* setup won't carry
> the tag and won't be picked. The run scope is fixed at setup.

## Main Loop

Repeat the following until `pick` finds nothing in `todo` or the loop stops on a blocker.
Board home must be on `<home-branch>` at the start of every iteration.

### Step 1: Pick a task

From board home, first refresh the parent claim (1h TTL — keeps the parent owned
across long child tasks):

```bash
kanban-md edit <parent-ID> --claim <agent>
```

On error, **stop**, it means another agent started working on it!!

Then pick the next tagged child:

```bash
kanban-md pick --claim <agent> --status todo --tags loop-<parent-ID> --move in-progress
```

If nothing is returned — **no todo children remain → go to [Phase 2: Success End](#phase-2-success-end).**

Note the task ID as `<ID>`. Read the full task:

```bash
kanban-md show <ID>
```

**Verify the claim:** confirm the `claim` field in the output shows `<agent>`. If it shows a different agent name, do NOT proceed — run:

```bash
kanban-md edit <ID> --release   # only if you own the claim; otherwise do nothing
```

Then pick again. If the conflict persists, stop and surface it to the user.

---

### Step 2: Write a plan

If the task already has a linked, detailed implementation plan, **SKIP** this step.  Note the absolute plan path: `<plan-path>`

For any task that touches tracked code or config:

1. Set `<plan-path>` to  `<plans-dir>/YYYY-MM-DD-<slug>.md` (plan path, relative to <board-home>)
2. Spawn a planner sub-agent to write a detailed implementation plan.  Pass
   the following prompt:
   ```
   Review the task at `kanban-md show <ID>`.
   Write a detailed implementation plan at <plan-path>.
   Do not edit code or the board, only the plan file.
   Include: **goal**, **proposed changes** (with file paths), **open questions**
   ```

3. If there are **open question** in the plan, spawn an oracle sub-agent to answer them.  Pass the following prompt:
   ```
    Review the plan at <plan-path>, together with the kanban task at `kanban-md show <ID>`
    Attempt answering open questions unless they genuinely require a user decision
    Do not edit code or the board, only the plan file.
    Return a result block in this exact format:

   status: RESOLVED        # all questions answered/non-blocking, answers appended to plan
   # or
   status: BLOCKED
   blocking-questions:
     - <question>
   ```

   **STOP** and ask user if Oracle returns a BLOCKED status.

3. Link the plan and the parent task in the task body:
   ```bash
   kanban-md edit <ID> \
     --append-body "Plan: <plan-path>" \
     --timestamp --claim <agent>
   ```

Skip for trivial tasks. Append an audit note instead:

```bash
kanban-md edit <ID> \
  --append-body "Skipped plan (trivial: <reason>)." \
  --timestamp --claim <agent>
```

---

### Step 3: Create a worktree (worktrunk `wt`)

Worktrees use **worktrunk** (`wt`). Always pass `-C <board-home>` (run against
board home), `-y` (non-interactive), `--no-cd` (loop drives subagents by path),
and `--format json` (capture the worktree dir from the `path` field).

The branch is always `task/<ID>-<slug>`. Check if a worktree already exists
(possible on resume after a blocker):

```bash
wt -C <board-home> list --format json | grep "task/<ID>"
```

- **Not found** — create it off **integration branch HEAD** (via `--base`):

  ```bash
  wt -C <board-home> -y switch --create task/<ID>-<slug> \
    --base <integration-branch> --no-cd --format json
  ```

  Note the `path` field as `<worktree directory>`.

- **Found, correct branch** — reuse it (omit `--create` to resolve its path):

  ```bash
  wt -C <board-home> -y switch task/<ID>-<slug> --no-cd --format json
  ```

  Note `path` as `<worktree directory>`. Confirm the branch is strictly ahead
  of the **integration branch HEAD** (carries unmerged work to resume); if not,
  treat it as a fresh start.

- **Found with a stale/wrong branch**: STOP and ask user how to proceed.


> **Why integration HEAD, not main?** Tasks are sequentially dependent. Branching off the integration HEAD means each task inherits all prior merged work, minimising conflicts at merge time.

---

### Step 4: Implement

Spawn a fresh-context implementation sub-agent. Pass the following prompt, with its working directory set to
`<worktree directory>`:

```
Change your working directory to <worktree directory> before running any commands.

You are implementing a single kanban task. Do NOT modify the kanban board — the orchestrating agent handles all board updates.

Inputs:
- Task ID: <ID>
- Task title: <title>
- Task description: <full description from task body>
- Plan: <board-home>/<plan-path>, or "trivial — no plan"
- Integration branch: <integration-branch>
- Task branch: task/<ID>-<slug>
- Worktree path: <worktree directory>

Instructions:
1. If a plan path is provided, read it before starting.
2. Implement the smallest change that satisfies the task requirements.
3. Run checks:
   go test ./...
   golangci-lint run ./...
4. If checks pass, commit:
   git add <files>
   git commit -m "feat: <description>"
5. Return a result block in this exact format:

status: SUCCESS
commit: <hash>
files-changed:
  - <file1>
  - <file2>
notes: <any relevant notes>

Or on failure:

status: FAILED
reason: <what went wrong>
notes: <details>
```

After the sub-agent returns:

- **`status: FAILED`** → go to **[Phase 3: Blocker End](#phase-3-blocker-end)** with reason "implementation failed on task #<ID>: <reason>".
- **`status: SUCCESS`** → persist the review cycle counter and append a progress note from board home:

```bash
cd <board-home>
kanban-md edit <ID> \
  --append-body "Implementation complete. Commit: <commit>.
review_cycle: 1" \
  --timestamp --claim <agent>
```

---

### Step 5: Review cycle (up to 3 attempts)

Before spawning the sub-agent, re-read the task body to determine the current cycle number:

```bash
kanban-md show <ID>
```

Look for the most recent `review_cycle: <N>` line in the body. Use that value as `review_cycle`. If no such line exists, default to `1`.

#### 5a — Spawn fresh-context reviewer sub-agent

Pass the following prompt. The sub-agent must run from the worktree (set its working directory to `<absolute-worktree-path>`):

```
Change your working directory to <worktree directory> before running any commands.

Read and follow the review instructions at:
  <reviewing-changes-file>
(Read it directly with the read tool.)
If that path is empty or the file is not available, perform a code review and return a verdict block in this format:
  verdict: APPROVE
  or
  verdict: CHANGES_REQUESTED
  counts: critical=<n> important=<n> suggestion=<n>
  ## Strengths
  - <specific>
  ## Findings
  1. [CRITICAL]   <description>
  2. [IMPORTANT]  <description>
  3. [SUGGESTION] <description>
  (CHANGES_REQUESTED if any Critical, any Important, or 3+ Suggestion findings.)

Inputs:
- Task ID: <ID>
- Plan: <plan path from task body, or "trivial — no plan">
- Base ref: <integration-branch>
- Head ref / branch: task/<ID>-<slug>
- Worktree path: <worktree directory>

Return only the markdown review block (no commentary before or after).
```

Append the returned block to the task body from board home:

```bash
cd <board-home>
kanban-md edit <ID> \
  --append-body "<review block>" \
  --timestamp --claim <agent>
```

#### 5b — Branch on verdict

Read the `verdict:` line from the review block.

---

**APPROVE:**

Merge the worktree to <integration-branch>:

```bash
cd <worktree directory>
wt merge <integration-branch>  # will merge the worktree branch onto integration branch
cd <board-home>
```

Run tests and lint on the integration branch (per project instructions)

**If merge or tests fail:**

```bash
git switch <home-branch>   # restore board-home branch before doing anything else
```

→ Go to **[Phase 3: Blocker End](#phase-3-blocker-end)** with reason "merge/test failure after APPROVE on task #<ID>".

**If clean:**

```bash
git switch <home-branch>
kanban-md edit <ID> --release
kanban-md move <ID> done
kanban-md edit <parent-ID> \
  --append-body "Task #<ID> merged to <integration-branch>." \
  --timestamp --claim <agent>
```

Clean up the worktree and delete the task branch (`--force-delete`: the branch
isn't merged into `<home-branch>`, so a plain delete would fail):

```bash
wt -C <board-home> -y remove task/<ID>-<slug> --force --foreground
```

→ **Continue loop (back to Step 1).**

---

**CHANGES_REQUESTED (review_cycle < 3):**

Spawn a fresh-context fix sub-agent. Pass the following prompt, with its working directory set to `<worktree
directory>`:

```
Change your working directory to <worktree directory> before running any commands.

You are fixing blocking review findings on a kanban task. Do NOT modify the kanban board — the orchestrating agent handles all board updates.

Inputs:
- Task ID: <ID>
- Task title: <title>
- Plan: <plan path, or "trivial — no plan">
- Task branch: task/<ID>-<slug>
- Worktree path: <worktree directory>
- Review cycle: <review_cycle>
- Findings to fix:
<paste all findings from the review block>

Instructions:
1. If a plan path is provided, read it for context.
2. Fix the findings listed above. Stay within the task's existing scope — do not refactor unrelated code or add new functionality.
3. Run checks (project instructions)
4. If checks pass, commit:
   git add <files>
   git commit -m "fix: address review findings (cycle <review_cycle>)"
5. Return a result block in this exact format:

status: SUCCESS
commit: <hash>
files-changed:
  - <file1>
  - <file2>
notes: <summary of fixes applied>

Or on failure:

status: FAILED
reason: <what went wrong>
notes: <details>
```

After the sub-agent returns:

- **`status: FAILED`** → go to **[Phase 3: Blocker End](#phase-3-blocker-end)** with reason "fix implementation failed on task #<ID> cycle <review_cycle>: <reason>".
- **`status: SUCCESS`** → increment `review_cycle`, persist it, and append a progress note from board home:

```bash
cd <board-home>
kanban-md edit <ID> \
  --append-body "Review cycle <review_cycle> CHANGES_REQUESTED — fixes applied. Commit: <commit>.
review_cycle: <review_cycle + 1>" \
  --timestamp --claim <agent>
```

**Loop back to Step 5a** (re-read cycle count from task body at the top of Step 5).

---

**CHANGES_REQUESTED (review_cycle = 3):**

Three cycles exhausted without APPROVE → go to **[Phase 3: Blocker End](#phase-3-blocker-end)** with reason "3 review cycles exhausted on task #<ID>".

---

## Phase 2: Success End

No `todo` children of the parent remain. All have been merged to the integration branch.

From board home, run the full suite on the integration branch (project instructions for definition of done)

Return to `<home-branch>` before touching the board:

```bash
git switch <home-branch>
```

Move the parent task to `review` and release:

```bash
kanban-md handoff <parent-ID> --claim <agent> \
  --note "Loop complete. All todo tasks merged to <integration-branch>.
Tests on integration branch: <pass/fail>.
Ready for final review and merge to <home-branch>." \
  --timestamp --release
```

Present a summary to the user:

```
## Loop Complete ✓

Integration branch: <integration-branch>
Tasks merged:
  - #<ID> — <title>
  ...
Tests on integration branch: <pass / fail + details>
Parent task: #<parent-ID>

Review the integration branch, then say:
  "merge <integration-branch> to <home-branch>"
```

If the board is git-tracked (check with `git -C <board-home> ls-files kanban/` — non-empty output means tracked), commit board changes on `<home-branch>`:

```bash
git add kanban/
git commit -m "chore(board): loop run complete — all tasks done"
```

---

## Phase 3: Blocker End

The loop has stopped due to an unresolvable issue on task `<ID>`.

**Triggers:**
- 3 review cycles exhausted (still CHANGES_REQUESTED)
- Merge into integration branch failed (conflict)
- Tests/lint on integration branch failed after merge

**Ensure board home is on `<home-branch>` before touching the board:**

```bash
cd <board-home>
git switch <home-branch>
```

Hand off the blocked sub-task:

```bash
kanban-md handoff <ID> --claim <agent> \
  --block "<specific reason>" \
  --note "## Blocked
Reason: <reason>
Review cycles attempted: <N>
Latest findings: see review block appended to this task body
Worktree preserved at: <worktree directory>
Branch: task/<ID>-<slug>" \
  --timestamp --release
```

Move the parent task to `review`:

```bash
kanban-md handoff <parent-ID> --claim <agent> \
  --block "Loop blocked on task #<ID>" \
  --note "## Loop Blocked

Stopped at: task #<ID> — <title>
Reason: <reason>
Tasks merged before blocker: <list of #ID — title>
Integration branch: <integration-branch>

To resume: fix task #<ID>, then say:
  'run the kanban loop, parent task #<parent-ID>'" \
  --timestamp --release
```

> **Do NOT remove the worktree** — preserve it for the user to inspect and fix.

Present a summary to the user:

```
## Loop Blocked ✗

Blocked at: task #<ID> — <title>
Reason: <reason>
Tasks merged before blocker: <list>
Worktree preserved: <worktree directory>
Branch: task/<ID>-<slug>

Fix the blocking issue, then resume:
  "run the kanban loop, parent task #<parent-ID>"
```

---

## Resuming After a Blocker

Resume is just Phase 0 re-run against the same `<parent-ID>`:

- The claim guard re-acquires the parent (the prior session's claim has expired or been released).
- Re-tagging the `todo` children is idempotent — the previously blocked task, once unblocked back into `todo`, gets re-tagged and picked.
- The integration branch already holds all previously merged work; new task worktrees branch off its HEAD automatically.
- The parent body's `Task #<ID> merged to …` lines record what already landed.

---

## Status meanings

| Status | Meaning |
|---|---|
| `in-progress` | Actively being worked by an agent |
| `review` | Loop complete (ready for final merge) or loop blocked (needs user intervention) |
| `done` | Merged to integration branch and verified |
