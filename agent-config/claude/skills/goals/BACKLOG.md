# Backlog goals

Goals Nic wants but can't place in time yet (e.g. "Better observability in EPI").

## Format
- `status: Backlog`, empty `horizon` and period, but a `parent` (usually a Year goal) so they stay aligned. Outside caps; never graded.
- `ready_when`: a window or condition ("H1 2027", "after EDW is live", "once the new data scientist is onboarded"). Empty = whenever there's room.
- `shape`: `Needs shaping` (scope or done-looks-like unclear) | `Shaped` (clear enough to schedule).

## Adding one (`/goals add` with no timing)
Ask once for `ready_when` (may stay empty). Set `shape: Shaped` only if Nic already knows what done looks like; otherwise `Needs shaping`.

## Life cycle
**One** backlog item started per week at most (shaping or scheduling), so the backlog never crowds out committed goals. Each start is a proposal Nic approves.

1. *Needs shaping* → picked: create a **shaping Week goal** named "Shape - <backlog goal>", parent = the backlog goal, `done_looks_like: "one-page scope + done looks like agreed (with the team if work)"`, inheriting the backlog goal's `discuss_at` so it lands in that meeting's prep. When the shaping goal is graded Done: set the backlog goal `shape: Shaped` and fill its `done_looks_like` from Nic's answer (or the `Outcome:` bullets in the daily note). It stays in Backlog.
2. *Shaped* → picked: **schedule** it: set horizon (usually Month), period, `status: Active`, and draft its first Week goal.

## Readiness test
Used by the weekly and monthly reviews. For **every** Backlog goal, decide `Ready` / `Not yet` with a one-line reason:
- **Condition met?** Check `ready_when` against evidence: a window that has arrived; a referenced goal now `Done`; Jira, Calendar or daily notes showing the condition happened. Unconfirmable → `Not yet (can't confirm: …)`; in an interactive run, ask Nic.
- **Capacity next period?** Next week has ≤4 committed Week goals, no trip or OOO covering most of it, and no `At risk` Month goal needing the slot.
- **Parent pull**: prefer items whose parent Year goal is `At risk` or has no open Month child.

Propose at most one `Ready` item and say in one line why each other item waits.
