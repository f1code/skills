# Bring kanban-based-development closer to kanban-loop-development (worktree + fix/review)

## Goal

Adopt the better **code-interaction mechanics** from `kanban-loop-development`
into `kanban-based-development`, without changing kanban-based's distinct
identity (parallel-safe, claim-centric, plan-approval pause, per-task
user-directed merge to `main`).

Scope is narrow and deliberately conservative ("simplest, cleanest"):

- **Adopt `wt` (worktrunk) worktree mechanics** in place of raw `git worktree add`.
- **Keep implementation and fixes in-session** (no implementation/fix sub-agent
  prompt machinery). Review stays a fresh-context sub-agent (unchanged).
- **Add a persisted `review_cycle:` counter** to the §3.5 autonomous-fix loop so
  cycle count survives context compaction.

## Non-goals

- No single-task mode added to `kanban-loop-development` (rejected Option 1).
- No shared worktree reference file (rejected Option 3 for worktrees: base-ref
  differs — based branches off `main`, loop off the integration branch — so a
  shared file needs parameterization that costs more than the ~10 inline lines
  it would save). `reviewing-changes.md` stays the single shared doc.
- No delegation of implementation/fixes to sub-agents.

## Proposed changes

All edits are in:
`/Users/ngaller@4gclinical.com/.agents/skills/kanban-based-development/SKILL.md`

### 1. §2 "Create a worktree (default)" — switch to `wt`

Replace the `using-git-worktrees` skill + raw `git worktree add` fallback with
worktrunk commands, branching off `main` (based's base ref). Mirror loop's
conventions: `-C <board-home>`, `-y`, `--no-cd`, `--format json`, capture the
`path` field.

- Create: `wt -C <board-home> -y switch --create task/<ID>-<slug> --base main --no-cd --format json`
- Reuse on resume: `wt -C <board-home> -y switch task/<ID>-<slug> --no-cd --format json` (also capture `path` from JSON)
- **Crucial for in-session work:** because based implements in-session (not via
  path-driven sub-agents like loop), `--no-cd` means the agent must then
  `cd <path-from-json>` in the worktree shell to do the work. State this
  explicitly so the two-shell model still holds, and propagate that path to the
  §3.5 reviewer cwd (based already requires this).
- Keep the pre-flight checklist (plan exists, linked, approved, open questions
  answered) — that is based-specific and stays.

### 2. §3.5 autonomous-fix loop — persist `review_cycle:`

- based already states "Repeat up to **3 cycles** (the initial review counts as
  cycle 1)". Align the counter with that — do NOT introduce an off-by-one.
- Persist `review_cycle: 1` **when the first (initial) review block is appended**
  (cycle 1 = the initial review), matching based's existing wording. Do not
  persist on "entering the fix loop" (that would mislabel).
- On each subsequent fix cycle, bump and persist `review_cycle: <k+1>` alongside
  the existing progress note.
- Re-read the latest counter from the task body at the top of each cycle
  (resume-safe); default to 1 if absent.
- Terminal condition unchanged: CHANGES_REQUESTED at `review_cycle = 3` →
  exhausted/blocked handoff. Keep all existing based semantics: defer-to-user
  check each cycle, scope rule (latest review block only), APPROVE → handoff for
  user-directed merge.
- Use loop's exact line format (`review_cycle: <N>`) for cross-skill consistency.

### 3. §7 "Optional cleanup" — use `wt remove`

Replace `git worktree remove --force` + `git branch -d` with:
`wt -C <board-home> -y remove task/<ID>-<slug> --force --foreground`

### 4. Frontmatter `allowed-tools`

Add `Bash(wt *)` and `Bash(date *)` (date is used for slug/branch naming, as in
loop).

### 5. Add a "Slug Derivation" note + reconcile branch-name token

based references `<kebab-description>`/`<slug>` without defining it. Lift loop's
short Slug Derivation paragraph so branch names are consistent.

Reconcile the branch-name token: based uses `task/<ID>-<kebab-description>` in
§2/§4(merge)/§7 but `task/<ID>-<slug>` in §3.5/handoffs. Standardize on
`task/<ID>-<slug>` everywhere — **including §4's `git merge` line** (pull §4 into
edit scope for this one-token change) so the branch name is consistent end to
end.

## Open questions

1. Is `wt` (worktrunk) actually installed/available in the environments where
   kanban-based runs? Loop assumes it; based currently uses plain git. If `wt`
   may be absent, do we want a one-line `git worktree` fallback retained?
   **Proposed answer:** keep a short raw-git fallback note so based degrades
   gracefully (loop does not, but based is the more general-purpose skill).
2. Should the `review_cycle:` marker reuse loop's exact line format for
   cross-skill consistency? **Proposed answer:** yes — identical
   `review_cycle: <N>` line.

## Verification

- After edits, re-read SKILL.md end-to-end for internal consistency (anchors,
  references to §2/§3.5/§7, checklist intact).
- Confirm no broken cross-references and that the defer-to-user / merge-to-main
  identity is untouched.
</content>
</invoke>
