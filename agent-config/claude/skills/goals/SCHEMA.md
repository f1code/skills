# Goal notes: format and rules

Shared reference for the `goals` and `daily` skills.

## Files

- Folder `Goals/`, one note per goal. **Filename = goal name**, in Nic's words, unique across the vault.
  Characters Obsidian can't link (`# ^ [ ] |`) or filenames can't hold (`: / \`) are replaced (`#1` → `number 1`, `:` → ` -`), with the original kept in `aliases`.
- `Goals/Reviews/`: one note per weekly / monthly / yearly review (format in REVIEWS.md). `goals.py` doesn't read this subfolder as goals.
- `Goals/Goals.base`: Nic's Obsidian views (Current, Board by horizon, This week, Backlog, All). It shows notes tagged `goal`; its `status_badge` formula shows the status emoji. Change it only on request.
- Renaming a goal = renaming the file **and** every `[[old name]]` in `Goals/` and `Dev/Progress/` (`grep -rl "\[\[old name" Goals Dev/Progress`).

## Frontmatter

Block-style lists, unquoted `YYYY-MM-DD` dates, quoted wikilinks, empty value = unset.

```yaml
---
icon: 📅                      # one emoji that fits the goal; Nic may change it
horizon: Week                 # Decade | Year | Month | Week; empty for Backlog
period_start: 2026-09-28
period_end: 2026-10-04
status: Active                # see Statuses
area:                         # Work | Health | Family | Learning | Projects | Finance
  - Work
parent:                       # ≥1 for every non-Decade goal; several allowed
  - "[[Supply Intelligence demo is a success]]"
done_looks_like: "Demo date on the calendar; storyline agreed in the SI syncs"
discuss_at:                   # recurring meeting names, e.g. EPI Tech Sync; new names allowed
ready_when:                   # Backlog only
shape:                        # Backlog only: Needs shaping | Shaped
tags:
  - goal
---

## Review notes

- 2026-10-02: Partial — date proposed, storyline still open
```

(The `# …` comments above are documentation; don't write them into notes.)

- `## Review notes`: dated one-liners appended at reviews, newest last. Free notes may follow.
- Children aren't stored: a goal's children are the notes whose `parent` contains `[[its name]]` (Obsidian also shows them as backlinks).
- `discuss_at`: on days that meeting is on the calendar, `/daily start` adds a prep section for the goal.
- To change a property, replace just that frontmatter line or list block (read-modify-write in one command), then run `goals.py check` to confirm the note still parses.

## Statuses

| Status | Emoji | Meaning |
|---|---|---|
| Active | 🔵 | committed, not yet graded |
| On track | 🟢 | Month/Year goal, per last review |
| At risk | 🟠 | Month/Year goal, per last review |
| Done | ✅ | achieved |
| Dropped | ⚪ | abandoned on purpose (healthy) |
| Rolled over | ↪️ | unfinished; a successor note carries it into the next period |
| Backlog | 💭 | no period yet, see BACKLOG.md |

**Open** = Active, On track or At risk. **Closed** = Done, Dropped or Rolled over.

## Horizons, periods, caps

| Horizon | Period | Cap (open goals) | Notes |
|---|---|---|---|
| Decade | 2026-09-28 → 2036-09-28 | 3–5 | Fuzzy on purpose; revisited at the yearly review |
| Year | first 2026-09-28 → 2027-12-31, then calendar years | ~3 per Decade goal, ≤6 total | `done_looks_like` becomes measurable (no "TBD") |
| Month | calendar month | ~3 (5 max) | |
| Week | Monday → Sunday | 3–5 | Derived from Month goals |

- A level may be skipped (e.g. Month → Decade) only when nothing fits; flag it.
- **Roll over**, never stretch a period: set the old note `Rolled over`, create a new note for the new period with the same parent. Names would collide, so suffix the new one with its period: "Onboard the new data scientist (Nov 2026)", "… (week of 2026-11-02)".
- Keep the name in Nic's words; `done_looks_like` is one line.

## Loading

`scripts/goals.py` (next to this file) is the one loader; `python3 goals.py --help` lists its commands (`tree`, `check`, `week`, `meetings`, `json`). Dates default to today in Europe/Brussels; pass `--date YYYY-MM-DD` to override. It uses PyYAML when installed and a built-in parser for this flat format otherwise. In Python, `load(vault)` returns `(goals, errors)`: dicts with the frontmatter plus `name`, `path`, and `parent` as plain names.
