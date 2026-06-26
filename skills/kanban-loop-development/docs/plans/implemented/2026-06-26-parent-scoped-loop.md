# Parent-Scoped Kanban Loop

## Goal

Change the loop from "drain the whole `todo` column" to "process the `todo`
children of a **required, existing** parent task." Eliminate the Mode A/B
split and the synthetic "Loop run:" task. Keep selection atomic and keep the
shared-board safety story intact.

## Decisions (locked)

- **Parent is mandatory.** No standalone mode, no auto-create. If the user does
  not supply a parent task ID, stop and ask for one.
- **Tag-then-pick.** At setup, tag the parent's `todo` children with a per-run
  tag, then keep using the atomic `kanban-md pick --status todo --tags <tag>`.
  This preserves race-free claiming (the reason we don't switch to
  `list --parent` + manual claim).
- **Claim the parent at setup** to prevent two loops running on the same parent.
- **Never set the structural `--parent` field.** Children are *already*
  structurally parented (that is how they are discovered). The loop only reads
  the hierarchy; the tag is purely a selection mechanism.

## Naming

- Run tag: `loop-<parentID>` (unique per parent, idempotent to re-apply on resume).
- Integration branch: unchanged — `loop/<YYYY-MM-DD>-<slug>`, slug derived from
  the **parent task title**.

## Proposed changes (all in `SKILL.md`)

### 1. Frontmatter / description / triggers
- Reword triggers away from "drain the todo column" / "process all todo tasks"
  toward "process the todo children of task X" / "run the kanban loop on a parent
  task". Keep a note that a parent ID is required.

### 2. Non-Negotiables
- Add: "A parent task ID is required. Refuse to start without one."
- Add: "Claim the parent before tagging or picking. If the parent carries a
  live (non-expired) claim by another agent, stop — another loop owns it."
- Add: "The loop never sets the structural parent field; it only reads it and
  applies the `loop-<parentID>` selection tag."

### 3. Phase 0: Setup (rewrite — replaces Mode A/B entirely)
New linear flow:
1. Resolve `<parent-ID>` from the user request. If absent → stop and ask.
2. `cd <board-home>`; confirm clean tree; capture `<home-branch>`.
3. `kanban-md show <parent-ID> --json` — read it.
4. **Claim guard** on the parent (see liveness rule below):
   - claim empty / expired / equals `<agent>` → `edit <parent-ID> --claim <agent>`.
   - claim present, not expired, not us → **STOP**, surface "another loop owns
     parent #<ID>."
5. Locate or create the integration branch:
   - Scan parent body for `Integration branch: <name>` → use it.
   - Not found → create `loop/<DATE>-<slug>` off `<home-branch>`, switch back,
     backfill the line into the parent body.
   - Verify it exists locally; else `git fetch`; else stop and ask.
6. `move <parent-ID> in-progress --claim <agent>`; append a
   "Loop (re)started by <agent>" timestamped note.
7. **Tag children** (idempotent; safe on resume):
   ```bash
   IDS=$(kanban-md list --parent <parent-ID> --status todo --json | <extract ids, comma-join>)
   kanban-md edit "$IDS" --add-tag loop-<parent-ID> --claim <agent>
   ```
   If there are no todo children at all → report "nothing to do" and stop
   cleanly (do not error).

**Claim liveness rule (used in step 4 and on resume):** treat an *expired*
claim as reclaimable (kanban-md surfaces expired claims as unclaimed via
`list --unclaimed`). Treat a present, non-expired claim by a different agent as
live → stop. This replaces the vague "is the agent still alive" heuristic with
a deterministic expiry check.

### 4. Main Loop — Step 1 (pick)
Replace the pick command with the tag-scoped form:
```bash
kanban-md pick --claim <agent> --status todo --tags loop-<parent-ID> --move in-progress
```
- Nothing returned → **Phase 2**.
- Keep the existing claim-verification + re-pick-on-conflict block unchanged.
- **Refresh the parent claim at the top of every iteration** (claim TTL is 1h;
  a long child task could otherwise let the parent claim expire and allow
  another loop to grab the parent):
  ```bash
  kanban-md edit <parent-ID> --claim <agent>
  ```
  Keep the existing per-child claim-refresh guidance for long-running tasks.

### 5. Main Loop — Step 2 (plan)
- Drop the `Parent: #<parent-ID>` body annotation (now redundant with the real
  structural parent). Keep the plan-link append and the trivial-task audit note.

### 6. Main Loop — Step 5b (APPROVE merge path)
- `<parent-ID>` always exists now, so remove the conditional language. After a
  clean merge, append `Task #<ID> merged to <integration-branch>.` to the parent
  as today.

### 7. Phase 2: Success End
- Trigger wording: "no todo children of #<parent-ID> remain" (not "todo empty").
- Otherwise unchanged: tests on integration branch, restore `<home-branch>`,
  `handoff <parent-ID> ... --release` to `review`, summary, optional board commit.
- (Open question below) optionally strip `loop-<parent-ID>` from done children.

### 8. Phase 3: Blocker End
- Unchanged in substance. Parent is already claimed by us; handoff the blocked
  child, append the blocker note to the parent, `handoff <parent-ID> --release`.
  Releasing the parent is what lets a later session re-acquire it via the claim
  guard.

### 9. "Resuming After a Blocker" section
- Collapse to the single Phase 0 path: re-run Phase 0 against the same
  `<parent-ID>`. The claim guard re-acquires the parent; child re-tagging is
  idempotent; the integration branch is read from the parent body. Remove the
  Mode B reference.

### 10. Status meanings table
- No change needed.

## Resolved decisions

1. **Tag cleanup at success — LEAVE.** `loop-<parentID>` stays on done children
   as run provenance. Re-running the same parent reuses the tag harmlessly.
2. **Children added mid-run — ACCEPT.** Tag-at-start defines the run scope.
   New todo children appearing after setup won't be picked. Document this as a
   known limitation in the skill (no per-iteration re-tagging).
3. **Claim TTL = 1h.** Liveness-via-expiry guard is valid. To keep the parent
   owned across long child tasks, re-claim the parent at the top of every loop
   iteration (see Step 1).
