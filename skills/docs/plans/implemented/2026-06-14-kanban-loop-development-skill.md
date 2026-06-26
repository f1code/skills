# Plan: kanban-loop-development skill (autonomous todo-draining loop)

## Goal

Create a new skill, a variation of `kanban-based-development`, that
**autonomously loops through the entire `todo` column** and implements every
task, integrating each onto a shared integration branch. The only
defer-to-user point is the **final merge to main** at the end of the loop.

Name: `kanban-loop-development`
Location: `kanban-loop-development/SKILL.md` (sibling of `kanban-based-development/`)

## Design (decided with user)

Integration-branch pattern, full per-task autonomy:

1. **Setup (once per loop run):**
   - Generate agent name (`kanban-md agent-name`).
   - Determine `<board-home>`, ensure on `main`, clean tree.
   - Create an **integration branch** off `main`, e.g.
     `loop/<date>-<slug>` (the "master branch for the loop").
   - Create a **parent kanban task** representing the loop run; record the
     integration branch name and intent in its body. Sub-tasks reference it.

2. **Loop body — repeat until `todo` is empty (or blocker encountered):**
   - `pick --claim <agent> --status todo --move in-progress`.
   - Read task; write + link a plan to `docs/plans/` for audit
     (**no approval pause** — auto-proceed).
   - Create a worktree branched off the **integration branch HEAD**
     (so later tasks build on earlier merged work), branch
     `task/<ID>-<slug>`.
   - Implement smallest change; run tests/lint; commit in worktree.
   - **Review cycle** (repeat up to 3 times):
     - Spawn fresh-context sub-agent for self-review via
       `reviewing-changes` skill. Trivial tasks skip review (audit note
       appended).
     - Branch on verdict:
       - **APPROVE** + clean merge + green tests → merge sub-task branch
         into the **integration branch** (not main); move sub-task to `done`;
         append merge note. **Continue to next task.**
       - **CHANGES_REQUESTED** → fix issues **in the same worktree**; run
         tests/lint; commit. **Re-review** (loop back to spawn fresh
         sub-agent).
       - After **3 review cycles** still CHANGES_REQUESTED or unresolvable
         merge conflict → **STOP LOOP.** Handoff entire run to user.
   - Refresh claim if long-running; keep one active task at a time.

3. **Termination / Blocker:**
   - Stop when `pick` reports nothing in `todo` (success).
   - Stop after 3 review cycles on a task without APPROVE (blocker);
     summarize and defer to user.

4. **End of loop — defer to user (final merge or blocker handoff):**
   - If loop completed successfully (all todo merged):
     - Switch board home to integration branch, run full test/lint suite.
     - Produce a summary: tasks merged to integration branch (count + links),
       test status, parent task link.
     - **STOP.** Present to user for review. User directs the final merge of
       the integration branch into `main` (and optional cleanup).
   - If loop stopped on blocker (3 review cycles exhausted):
     - Produce a summary: tasks merged so far, current blocked task + latest
       review findings, what we tried, why autonomous fix stalled.
     - **STOP and handoff.** "This task needs manual intervention; fix and
       re-claim to resume loop."
   - The loop never touches `main`.

## Proposed changes (files)

- **New:** `kanban-loop-development/SKILL.md`
  - Frontmatter: name, description (trigger phrases like "work through all
    todo tasks in a loop", "drain the todo column autonomously"),
    `allowed-tools` mirroring the base skill plus `Bash(date *)`.
  - Reuse base-skill prose for: multi-agent claim mechanic, trivial-task
    definition, board-home vs worktree rule, agent identity, progress
    notes, self-review sub-agent orchestration, status meanings.
  - Replace the base skill's three defer-to-user pauses with loop behavior:
    - plan-approval pause → auto-proceed (write+link plan for audit only)
    - merge-to-main → merge to integration branch; final merge deferred
    - CHANGES_REQUESTED → auto-fix in same worktree, re-review (up to 3 cycles); only stop loop on circuit-breaker (3rd failed cycle)
  - Add: integration-branch + parent-task setup, the loop structure,
    circuit breaker, end-of-loop summary + final-merge handoff.

- **No change** to `kanban-based-development/SKILL.md` (kept as the
  human-in-the-loop default).

## Open questions

1. **Integration branch base for sub-tasks**: branch each sub-task off the
   *integration branch HEAD* (proposed — builds incrementally, fewer final
   conflicts but sequential coupling) vs. off *main* (independent, but more
   conflicts when merging into integration). Proposed: integration HEAD.
2. **Parent task lifecycle**: keep parent in `in-progress` for the whole run
   and move to `review` at the end? (Proposed.)
3. **Versioning header**: base skill carries
   `<!-- kanban-md-skill-version: 0.34.0 -->`. Mirror the same version in
   the new skill?
4. **Naming**: `kanban-loop-development` vs. e.g.
   `kanban-autonomous-loop` — preference?
