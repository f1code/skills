# Reviews

Each review is its own note in `Goals/Reviews/`, never in the daily note:

| Review | File | `type` |
|---|---|---|
| weekly | `Goals/Reviews/Week of YYYY-MM-DD.md` (that week's Monday; not a bare date, which would clash with daily-note links like `[[2026-09-28]]`) | `weekly-review` |
| monthly | `Goals/Reviews/YYYY-MM.md` | `monthly-review` |
| yearly | `Goals/Reviews/YYYY.md` | `yearly-review` |

- Missing → create it with the vault skill's `note.py create "<file>" review --set type=<type> --set period_start=<YYYY-MM-DD> --set period_end=<YYYY-MM-DD>`.
- Exists (e.g. the scheduled prep already wrote it) → merge: `note.py replace` only the sections you are refreshing, and never overwrite what Nic wrote (e.g. `## Reflection`).
- Frontmatter, then `##` sections; no title heading (the filename is the title). Link goals as `[[goal]]` and evidence days as `[[YYYY-MM-DD]]`.
- Grades are proposals until Nic confirms them.

## Weekly review (`/goals review week`; scheduled Friday afternoon)

1. **Load** (`goals.py json`): this week's Week goals, their parent Month goals, and open Month goals with no Week child this week.
   Done when every Week goal covering today is in the list.
2. **Evidence** (read-only):
   - Daily notes Monday → today in `Dev/Progress/`: `## Open` items ticked or not, `## Handoff` sections, decisions, `Outcome:` bullets under `## Prep: …`.
   - Jira: issues Nic resolved or moved this week.
   - Calendar: this week's goal-related meetings (demo, go-live, onboarding…); next week's OOO, trips and key meetings.
   - Slack: Nic's own messages this week on goal topics.
3. **Scorecard**: each Week goal gets `Done` / `Partial` / `Missed` plus one line of linked evidence. Grade `Done` only with evidence; with none, write "no evidence found".
   Done when every Week goal has a grade and an evidence line.
4. **Month pulse**: each open Month goal → `On track` / `At risk` with a one-line reason and the weeks left in the month.
5. **Backlog check**: the readiness test from [BACKLOG.md](BACKLOG.md) on every Backlog goal; at most one proposal for next week (a shaping Week goal if `Needs shaping`, scheduling if `Shaped`).
6. **Draft next week**: 3–5 Week goals from Month goals, in priority order: At risk Month goals, Month goals with no Week child yet, what next week's calendar makes timely (e.g. trip prep), then the backlog proposal (marked 💭). Each with done-looks-like and intended parent, within caps; successors of `Partial`/`Missed` goals named per the roll-over rule in SCHEMA.md.
7. **Write** `Goals/Reviews/Week of <Monday>.md` (create or merge, see above) and sync (`goals: weekly review week of <Monday>`). Sections:
   ```
   ## Scorecard        (first line: _italic — when/how prepared, sources used or skipped_;
                        then table: Goal | Grade | Evidence — goals as [[links]]; then "Score: x/y Done")
   ## Month pulse      (bullets)
   ## Backlog check    (table: Backlog goal | Ready when | Shape | Ready? + reason; then the proposal, or "none this week")
   ## Reflection       (Nic's words: what went well / what to change — two empty bullets until given)
   ## Draft next week  (checklist: - [ ] goal — done looks like — parent)
   ```

**Unattended run ends here**: goal notes and daily notes stay untouched. Reply with the review note path and three lines: score x/y, biggest risk, proposed #1 for next week (plus the backlog proposal, if any).

8. **Interactive: confirm.** One multi-select question round: grades, what to do with each `Partial`/`Missed` goal (roll over or drop), his two-line reflection, unclear backlog conditions, and next week's list including any backlog proposal.
9. **Interactive: apply** exactly what Nic approved:
   - Week goals: `Done` → `Done`; `Partial`/`Missed` → `Rolled over` or `Dropped` as he chose. Append `- YYYY-MM-DD: <grade> — <evidence>` under `## Review notes`.
   - Month goals: status `On track` / `At risk`.
   - Approved next-week goals: new notes (icon, period next Monday → Sunday, parent, area, `status: Active`, empty `## Review notes`).
   - Approved backlog item: its shaping Week goal, or schedule it, per BACKLOG.md. A shaping goal graded Done: update its backlog goal per BACKLOG.md.
   - Review note: his reflection under `## Reflection`; tick approved items in `## Draft next week`.
   - Run `goals.py check`, then sync once for the whole review.
   Done when every approved change is in a note, `check` reports no new flags, and the sync succeeded.

## Monthly review (`/goals review month`; last Friday of the month, after the weekly)

The weekly shape one level up, in `Goals/Reviews/YYYY-MM.md` (commit `goals: monthly review YYYY-MM`):
1. Grade each Month goal from its Week children + evidence; set Year goals `On track` / `At risk`.
2. Run `goals.py check` and propose a fix for every flag; sharpen one TBD `done_looks_like` per review.
3. Ask: "anything to drop?" — dropping is healthy.
4. **Backlog pass**: the readiness test on every item, plus: is each `ready_when` still right; propose one where it's empty; items untouched for ~6 months (last review note or `git log`) → "still want this?"; ideas Nic mentioned this month → offer to add as Backlog. Propose at most one Shaped item to schedule as a Month goal.
5. Draft next month's ~3 goals from Year goals (plus the scheduled backlog item if approved). On approval, create or update them (period = calendar month) and sync.

Unattended: stop after writing the review note, as for the weekly review.

## Yearly review (`/goals review year`; December)

In `Goals/Reviews/YYYY.md`: grade Year goals; re-read Decade goals with Nic (keep, reword, drop, add); set next year's goals with measurable `done_looks_like`; draft January. Apply and sync only what he approves.
