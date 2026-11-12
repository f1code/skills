---
name: daily
description: "Nic's daily work note in his Obsidian vault. Use to start my day (plan + standup, also the scheduled weekday run), to resume or pick up where I left off (/daily), and to save a handoff (/daily save)."
---

# Daily note: start, resume, save

| Command | Mode |
|---|---|
| `/daily start`, "start my day", scheduled weekday run | **Start**: follow [START.md](START.md) step by step |
| `/daily`, "pick up where I left off" | **Resume** (below) |
| `/daily save`, "save a handoff" | **Save** (below) |

Reach the vault, run scripts, edit and sync through the `vault` skill; commit messages are `daily: <date> start` / `daily: <date> handoff`. Goals are read with the `goals` skill's `scripts/goals.py` (format in its `SCHEMA.md`). This skill writes only daily notes: never goal notes or reviews.

## The daily note

- `Dev/Progress/YYYY-MM-DD.md`, one per day; same-day extras `YYYY-MM-DD-2.md`, `-3`… A day that already has a note gets merged into, never a second note.
- Latest note = highest ISO name (older non-ISO names like `Sep 8 2024.md` or `Monthly/…` don't count):
  `ls Dev/Progress | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}(-[0-9]+)?\.md$' | sort | tail -5`
- Frontmatter holds only `tags: [work]` (block list). No `# title`: the filename is the title.
- Create with the vault skill's `note.py create <file> work` and edit section by section with `note.py replace|append`, keeping Nic's content.
- Link goals and other notes as `[[wikilinks]]` (`[[SI demo date set and storyline agreed]]`, `[[2026-09-28]]`).
- Sections, in this order when present: `## Goals this week`, `## Prep: <meeting> (<HH:MM>)`, `## Plan`, `## Standup`, `## Needs reply`, `## Open`, `## Decide`, `## Handoff`.
- `## Open` holds at most 7 items, today's commitments. Everything else lives in `Dev/Backlog.md` (one standing work backlog, sections by area plus `## Inbox` for new overflow); Nic curates it, the skill only appends to `## Inbox`.
- Weekly / monthly reviews don't go here: they live in `Goals/Reviews/` (see the `goals` skill).
- The Notion "Daily Notes" database is a frozen archive up to 2026-09-30 (also migrated into `Dev/Progress/`): read it for history only.

## Resume (`/daily`)

1. Open today's note, else the latest one plus its same-date extras. If today's is missing on the Mac (paths A and C), it may be an unpulled unattended run (see the vault skill); otherwise offer `/daily start`.
2. Read it fully.
3. Reply briefly: which note; open items in priority order (🎯 goal-serving first among equals); decisions already reached, so they aren't re-litigated.
4. Ask which item to start with, and wait for the answer.

## Save (`/daily save`, "save a handoff")

Merge into today's note, then sync:
- `## Handoff`: one `###` per topic worked on in this conversation — link (PR / ticket), verdict or status, terse conclusions (decisions, root causes, what was ruled out); 🎯 `[[goal]]` if it moved a week goal.
- Under a `## Prep: …` item, when Nic shares what came out of that meeting: `Outcome:` nested bullets (the weekly review reads them, e.g. to mark a backlog goal Shaped).
- `## Open`: tick completed items, add next actions (still max 7 unticked; overflow appended to `Dev/Backlog.md` `## Inbox` with a `(since MM-DD)` tag).

Done when every topic from this conversation has a `###` entry and `## Open` reflects what's next. Write terse and scannable, not a transcript. Then name the updated note and say: "Start a new task and type /daily".
