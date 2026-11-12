---
name: goals
description: "Nic's goals as notes in his Obsidian vault (Decade → Year → Month → Week, plus Backlog). Use for /goals, a goal check, weekly/monthly/yearly reviews, adding a goal, or a someday idea."
---

# Goals: view, review, add

Nic tracks work **and** personal goals at four horizons, each linked to the one above. **Nic decides**: Claude gathers evidence and *drafts*; a goal note changes only after Nic approves that change in this conversation. Unattended runs draft only.

Before touching any goal, read [SCHEMA.md](SCHEMA.md) (note format, horizons, caps, statuses) and load goals with `scripts/goals.py`. Reach the vault, run the scripts, edit and sync through the `vault` skill (its section 2 says how to run scripts on each path); commit messages start with `goals:`.

Writes go only to `Goals/`: goal notes and review notes in `Goals/Reviews/`. Never write reviews into daily notes. Evidence sources are **read-only**: Jira (4gclinical.atlassian.net), Google Calendar, Slack, Gmail, and the daily notes in `Dev/Progress/`. Skip an unavailable source and say which. Keep replies terse and scannable, with linked evidence; no lectures on goal-setting. Personal goals (family, gym, trips) often have evidence only in Nic's words: ask him rather than infer.

The Notion "Goals" and "Daily Notes" databases are a frozen archive (history up to 2026-09-30): read them for history only.

## Modes

| Command | What | Where |
|---|---|---|
| `/goals` | view + health check | below |
| `/goals add <text>` | add a goal | below |
| `/goals review week` (also scheduled Friday afternoon) | weekly review | [REVIEWS.md](REVIEWS.md) |
| `/goals review month` (last Friday of the month, after the weekly) | monthly review | [REVIEWS.md](REVIEWS.md) |
| `/goals review year` (December) | yearly review | [REVIEWS.md](REVIEWS.md) |

Anything touching a Backlog goal (adding, shaping, scheduling, readiness) follows [BACKLOG.md](BACKLOG.md).

## View (`/goals`)

1. `goals.py tree <vault>`: open goals (Active / On track / At risk, period covering today) as a tree, Backlog goals as 💭 under their parent with `ready_when` + `shape`.
2. `goals.py check <vault>`: the **health check** (YAML errors, orphans, broken parents, missing periods, over cap, stale, Year goals with TBD `done_looks_like`).
3. Reply with the tree and every health-check flag, then ask which flag he wants to act on. Change nothing unprompted.

Done when every flag from `check` appears in the reply. (Nic can also open `Goals/Goals.base` in Obsidian.)

## Add (`/goals add <text>`)

1. Infer horizon, period, area and parent from the text and the current tree. If parent or horizon is ambiguous, ask once, listing candidate parents.
2. No timing given and none obvious ("someday", "not sure when") → a Backlog goal, per [BACKLOG.md](BACKLOG.md).
3. Work goal with an obviously matching recurring meeting (e.g. EPI items → `EPI Tech Sync`) → offer it as `discuss_at`.
4. Pick an `icon` emoji that fits.
5. Warn if the level would go over cap.
6. Show the draft (name, icon, frontmatter) so Nic can adjust; on his OK create the note, run `goals.py check`, and sync (`goals: add "<name>"`).
