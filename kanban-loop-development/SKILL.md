---
name: kanban-loop-development
description: >
  Autonomous loop that drains the entire `todo` column onto a shared integration
  branch, one task at a time. Each task is implemented, self-reviewed, and
  auto-fixed if needed (up to 3 review cycles). The loop stops when todo is
  empty (success) or a task exhausts its review cycles (blocker). Final merge
  to main is deferred to the user.
  Use when asked to "work through all todo tasks", "drain the todo column",
  "loop through all tasks autonomously", "run the kanban loop", or
  "process all todo tasks".
allowed-tools:
  - Bash(kanban-md *)
  - Bash(kbmd *)
  - Bash(git *)
  - Bash(go *)
  - Bash(golangci-lint *)
  - Bash(awk *)
  - Bash(date *)
---
<!-- kanban-md-skill-version: 0.34.0 -->

# Kanban Loop Development

Autonomous, sequential loop that processes the entire `todo` column, merging
each completed task onto a shared integration branch. The loop does not pause
for plan approval or per-task merge decisions. The only user handoff is at
the very end: final merge of the integration branch into `main`.

Tasks are treated as **sequentially dependent** — task B may depend on task A.
A single blocker stops the entire loop. No skipping ahead.

## Multi-Agent Environment

**This board is shared.** Multiple agents and humans may be working on it simultaneously.

- Another agent may claim a task between the time you list it and try to pick it.
- Tasks you saw as available moments ago may no longer be available.

The **claim** mechanic is the coordination primitive. **You MUST claim a task before starting any work on it. You MUST only pick unclaimed tasks.**

## Non-Negotiables

- **Claim before you change anything.** No task edits, no code changes.
- **Write a plan before you build.** Plans are for audit — they do NOT require user approval. Auto-proceed after writing and linking.
- **One active task per loop iteration.** Do not pick the next task until the current one is merged or the loop is stopped.
- **Never steal a live claim.** If a task shows a claim by a different agent, stop immediately and surface the conflict to the user.
- **Always leave the board accurate.** Parent task and sub-tasks must reflect actual state at all times.
- **The loop never touches `main`.** All sub-task merges target the integration branch only.
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
- Board home must be on `main` except for the brief moment it switches to `<integration-branch>` to run checks at the end of the loop. Always `git switch main` when done with that step.
- If the board is git-tracked, **commit board changes on `main` as a separate commit** after the integration branch is merged.

At the start of the session, determine and remember `<board-home>`:

```bash
cd <the canonical repo directory that owns the shared board>
pwd   # remember this path as <board-home>
```

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

The review step (Step 5a) hands a fresh sub-agent a review-instructions file
that ships **inside this skill's own directory**: `reviewing-changes.md`,
beside the `SKILL.md` you loaded for this skill.

At the start of the session, determine the absolute path to this skill's
directory (the folder you read this `SKILL.md` from) and remember the file path:

```
<reviewing-changes-file> = <this-skill-directory>/reviewing-changes.md
```

Do NOT hardcode a machine-specific absolute path. Derive it from wherever this
skill is installed so it stays portable across machines. If the file is missing
(e.g. a partial install), the review sub-agent falls back to the inline format
described in Step 5a.

## Expected Review Block Format

Self-review sub-agents must return a block in this format (the loop parses the `verdict:` line):

```
verdict: APPROVE
<!-- or -->
verdict: CHANGES_REQUESTED

## Findings
1. [BLOCKING] <description of issue>
2. [ADVISORY] <description>
...
```

Only findings marked `[BLOCKING]` must be addressed before re-review. `[ADVISORY]` findings are informational. The loop acts on the verdict line only; findings guide the auto-fix step.

---

## Phase 0: Setup

Before picking any tasks, establish the integration branch and parent task.

### Determining setup mode

Check the user's request for an existing parent task ID (e.g. "use task #42 as parent", "parent is task 7", "resume from #12"):

- **Parent task ID explicitly provided** → **Mode B** (use existing parent task)
- **User says "resume" but no ID detectable** → run `kanban-md list --status in-progress --compact` to find candidate parent tasks whose title starts with "Loop run:"; confirm the correct one with the user before proceeding
- **No parent task ID mentioned** → **Mode A** (create fresh)

---

### Mode A: Fresh run

Confirm board home is on `main` with a clean working tree:

```bash
cd <board-home>
git switch main
git status          # must be clean — stop and report if unexpected changes
```

Create the integration branch off `main`. Derive `<slug>` from the user's stated goal (see Slug Derivation):

```bash
DATE=$(date +%Y-%m-%d)
git switch -c loop/${DATE}-<slug>
git switch main     # return to main immediately; worktrees branch off the integration branch
```

Remember: `<integration-branch>` = `loop/<YYYY-MM-DD>-<slug>`.

Create the parent kanban task and claim it:

```bash
kanban-md add "Loop run: <slug>" \
  --body "Integration branch: loop/${DATE}-<slug>

Goal: <user's stated goal>
Started: ${DATE}
Agent: <agent>" \
  --status in-progress
```

The `add` command prints the new task ID. Remember it as `<parent-ID>`. Then claim it:

```bash
kanban-md edit <parent-ID> --claim <agent>
```

---

### Mode B: Use existing parent task

Read the parent task in full:

```bash
kanban-md show <parent-ID>
```

**Locate or create the integration branch:**

Scan the task body for a line matching `Integration branch: <name>`.

- **Found**: use that name as `<integration-branch>`.
- **Not found** (task was created manually without a branch line): create a branch now and backfill the task body. Derive `<slug>` from the parent task title:

  ```bash
  DATE=$(date +%Y-%m-%d)
  git switch main
  git switch -c loop/${DATE}-<slug>
  git switch main
  kanban-md edit <parent-ID> \
    --append-body "Integration branch: loop/${DATE}-<slug>" \
    --timestamp --claim <agent>
  ```

**Verify the branch exists locally:**

```bash
git branch --list "<integration-branch>"
```

If the output is empty, fetch it:

```bash
git fetch origin <integration-branch>
git branch --list "<integration-branch>"
```

If still not found locally or remotely, stop and ask the user before proceeding.

**Handle stale claims from a prior session:**

If the parent task or any in-progress sub-task shows a claim by a different agent name (from a prior crashed session), check whether that session is still alive. If it is clearly dead (the agent name is not active), you may re-claim:

```bash
kanban-md edit <parent-ID> --claim <agent>   # overwrites stale claim
```

Apply the same logic to any sub-task stuck `in-progress` with a stale claim.

**Claim and activate the parent task:**

The parent task may be in any status. Move it to `in-progress` and claim it:

```bash
kanban-md edit <parent-ID> --claim <agent>
kanban-md move <parent-ID> in-progress --claim <agent>
kanban-md edit <parent-ID> \
  --append-body "Loop (re)started by <agent>." \
  --timestamp --claim <agent>
```

---

## Main Loop

Repeat the following until `pick` finds nothing in `todo` or the loop stops on a blocker.
Board home must be on `main` at the start of every iteration.

### Step 1: Pick a task

From board home:

```bash
cd <board-home>
git branch --show-current     # confirm: must show "main"
kanban-md pick --claim <agent> --status todo --move in-progress
```

If nothing is returned — **todo is empty → go to [Phase 2: Success End](#phase-2-success-end).**

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

### Step 2: Write a plan (auto-proceed — no approval pause)

For any task that touches tracked code or config:

1. Write the plan to `docs/plans/YYYY-MM-DD-<short-description>.md`.
   - Include: **goal**, **proposed changes** (with file paths), **open questions** (note them; do not block the loop to resolve them).
2. Link the plan and the parent task in the task body:
   ```bash
   kanban-md edit <ID> \
     --append-body "Plan: docs/plans/YYYY-MM-DD-<slug>.md
   Parent: #<parent-ID>" \
     --timestamp --claim <agent>
   ```

Skip for trivial tasks. Append an audit note instead:

```bash
kanban-md edit <ID> \
  --append-body "Skipped plan (trivial: <reason>). Parent: #<parent-ID>" \
  --timestamp --claim <agent>
```

---

### Step 3: Create a worktree

Before creating a worktree, check whether one already exists for this task ID (possible on resume after a blocker):

```bash
git worktree list | grep "kanban-loop-task-<ID>"
```

- **Not found**: create it, branched off **the integration branch HEAD** (not `main`):

  ```bash
  git worktree add ../kanban-loop-task-<ID> \
    -b task/<ID>-<slug> \
    <integration-branch>
  ```

- **Found with the correct branch**: reuse it — just note the path.
- **Found with a stale/wrong branch**: remove and recreate:

  ```bash
  git worktree remove --force ../kanban-loop-task-<ID>
  git branch -D task/<ID>-<slug>   # force-delete; it will be recreated
  git worktree add ../kanban-loop-task-<ID> \
    -b task/<ID>-<slug> \
    <integration-branch>
  ```

> **Why integration HEAD, not main?** Tasks are sequentially dependent. Branching off the integration HEAD means each task inherits all prior merged work, minimising conflicts at merge time.

---

### Step 4: Implement

Spawn a fresh-context implementation sub-agent. Pass the following prompt, with its working directory set to `<absolute path to ../kanban-loop-task-<ID>>`:

```
Change your working directory to <absolute path to ../kanban-loop-task-<ID>> before running any commands.

You are implementing a single kanban task. Do NOT modify the kanban board — the orchestrating agent handles all board updates.

Inputs:
- Task ID: <ID>
- Task title: <title>
- Task description: <full description from task body>
- Plan: <plan path, or "trivial — no plan">
- Integration branch: <integration-branch>
- Task branch: task/<ID>-<slug>
- Worktree path: <absolute path to ../kanban-loop-task-<ID>>

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

#### 5a — Spawn fresh-context self-review sub-agent

Pass the following prompt. The sub-agent must run from the worktree (set its working directory to `<absolute-worktree-path>`):

```
Change your working directory to <absolute path to ../kanban-loop-task-<ID>> before running any commands.

Read and follow the review instructions at:
  <reviewing-changes-file>
(Read it directly with the read tool.)
If that path is empty or the file is not available, perform a code review and return a verdict block in this format:
  verdict: APPROVE
  or
  verdict: CHANGES_REQUESTED
  ## Findings
  1. [BLOCKING] <description>
  2. [ADVISORY] <description>

Inputs:
- Task ID: <ID>
- Plan: <plan path from task body, or "trivial — no plan">
- Base ref: <integration-branch>
- Head ref / branch: task/<ID>-<slug>
- Worktree path: <absolute path to ../kanban-loop-task-<ID>>

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

Switch board home to the integration branch and merge:

```bash
cd <board-home>
git switch <integration-branch>
git merge task/<ID>-<slug> --no-ff -m "feat: task #<ID> <description>"
```

Run checks on the integration branch:

```bash
go test ./...
golangci-lint run ./...
```

**If merge or tests fail:**

```bash
git switch main   # restore board-home branch before doing anything else
```

→ Go to **[Phase 3: Blocker End](#phase-3-blocker-end)** with reason "merge/test failure after APPROVE on task #<ID>".

**If clean:**

```bash
git switch main
kanban-md edit <ID> --release
kanban-md move <ID> done
kanban-md edit <parent-ID> \
  --append-body "Task #<ID> merged to <integration-branch>." \
  --timestamp --claim <agent>
```

Clean up worktree and force-delete the task branch (it was merged into the integration branch, not main, so `-d` would fail):

```bash
git worktree remove --force ../kanban-loop-task-<ID>
git branch -D task/<ID>-<slug>
```

→ **Continue loop (back to Step 1).**

---

**CHANGES_REQUESTED (review_cycle < 3):**

Spawn a fresh-context fix sub-agent. Pass the following prompt, with its working directory set to `<absolute path to ../kanban-loop-task-<ID>>`:

```
Change your working directory to <absolute path to ../kanban-loop-task-<ID>> before running any commands.

You are fixing blocking review findings on a kanban task. Do NOT modify the kanban board — the orchestrating agent handles all board updates.

Inputs:
- Task ID: <ID>
- Task title: <title>
- Plan: <plan path, or "trivial — no plan">
- Task branch: task/<ID>-<slug>
- Worktree path: <absolute path to ../kanban-loop-task-<ID>>
- Review cycle: <review_cycle>
- Blocking findings to fix:
<paste all [BLOCKING] findings from the review block>

Instructions:
1. If a plan path is provided, read it for context.
2. Fix each [BLOCKING] finding. Do not address [ADVISORY] findings.
3. Run checks:
   go test ./...
   golangci-lint run ./...
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
- **`status: SUCCESS`** → compute the next cycle number (e.g. if review_cycle is 2, next is 3). Persist it and append a progress note from board home:

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

`todo` is empty. All tasks have been merged to the integration branch.

From board home, run the full suite on the integration branch:

```bash
git switch <integration-branch>
go test ./...
golangci-lint run ./...
```

Return to `main` before touching the board:

```bash
git switch main
```

Move the parent task to `review` and release:

```bash
kanban-md handoff <parent-ID> --claim <agent> \
  --note "Loop complete. All todo tasks merged to <integration-branch>.
Tests on integration branch: <pass/fail>.
Ready for final review and merge to main." \
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
  "merge <integration-branch> to main"
```

If the board is git-tracked (check with `git -C <board-home> ls-files kanban/` — non-empty output means tracked), commit board changes on `main`:

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

**Ensure board home is on `main` before touching the board:**

```bash
cd <board-home>
git switch main
```

Hand off the blocked sub-task:

```bash
kanban-md handoff <ID> --claim <agent> \
  --block "<specific reason>" \
  --note "## Blocked
Reason: <reason>
Review cycles attempted: <N>
Latest findings: see review block appended to this task body
Worktree preserved at: <absolute path to ../kanban-loop-task-<ID>>
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
Worktree preserved: ../kanban-loop-task-<ID>
Branch: task/<ID>-<slug>

Fix the blocking issue, then resume:
  "run the kanban loop, parent task #<parent-ID>"
```

---

## Resuming After a Blocker

When the user has resolved the blocked task and says something like
"resume the loop" or "continue from parent task #<parent-ID>":

1. Use **Mode B** in Phase 0.
2. Read the parent task body to identify which tasks were already merged (look for "Task #<ID> merged to …" lines).
3. The previously blocked task should be back in `todo` (unblocked by the user) or already `done` if the user resolved it manually.
4. The integration branch already contains all previously merged work — sub-task worktrees will branch off its HEAD automatically.
5. Pick the next unclaimed `todo` task and proceed from Step 1.

---

## Status meanings

| Status | Meaning |
|---|---|
| `in-progress` | Actively being worked by an agent |
| `review` | Loop complete (ready for final merge) or loop blocked (needs user intervention) |
| `done` | Merged to integration branch and verified |
