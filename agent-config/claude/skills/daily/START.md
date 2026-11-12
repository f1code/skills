# Start the day (`/daily start`)

Read-only on Calendar, Jira, Slack, Gmail and goal notes: the only write is today's daily note. Never send messages, post to Slack, change Jira or reply to email. In an unattended run, decide instead of asking and record assumptions in the note.

1. **Carry over.** From the latest previous note, collect the unchecked `- [ ]` items under Open / Decide / Plan / TODO / Roll over (not Needs reply: step 3 rebuilds it). Keep each item's `(since MM-DD)` tag; add one with the previous note's date if missing. Drop items confirmed done in the sources (ticket Done, reply already sent) and items for a meeting or deadline already past; name them in one line of the note.
   Triage: an item carried 3+ workdays goes to `## Decide`. The rest, plus new actionable items from step 3, are candidates for `## Open`.
   Done when each item is in Open, Decide, `Dev/Backlog.md`, or named as dropped.
2. **Week goals.** `goals.py week <vault>`. It prints the open Week goals with their parents, or "No week goals set — run /goals review week" plus a link to the latest weekly review draft in `Goals/Reviews/`.
3. **Gather.** Skip any source whose connector is unavailable and name it in the note.
   - Google Calendar: today 00:00–24:00 Europe/Brussels; out-of-office blocks mean unavailable.
   - Jira (4gclinical.atlassian.net): issues assigned to Nic not Done/Closed; issues he reported or was mentioned on updated in the last 24h; status changes since yesterday.
   - Bitbucket (via Atlassian): open PRs where he's a reviewer.
   - Slack: his own messages since the previous workday (for the standup); mentions, DMs and threads waiting on his reply.
   - Gmail: unread or starred from the last 24h that look actionable (newsletters and notifications excluded).
4. **Meeting prep.** `goals.py meetings <vault>` maps each `discuss_at` name to its open or Backlog goals. For each of today's events whose title contains one of those names (case-insensitive), take each goal: status (Backlog: `shape` + `ready_when`), parent, the latest `## Review notes` line, and mentions in the last week's daily notes. Draft 1–3 discussion points per goal:
   - Backlog, `Needs shaping` → shaping questions: problem or pain solved, in and out of scope, what done looks like, owner, rough size.
   - Backlog, `Shaped` → "ready to schedule? what's the first slice?"
   - Open goal → progress since last meeting, blockers, decisions needed from the group.
   No matching event → no prep section.
5. **Plan.** Priority order: (a) anything flagged P1 / first priority in the previous note, (b) blockers others wait on (reviews, replies), (c) work advancing a week goal, (d) in-progress tickets, (e) the rest. Time-block around meetings, keep a lunch slot, end at his first out-of-office block. If no block serves a week goal, say so in one line and suggest the smallest step that would.
6. **Standup.** Yesterday / Today / Blockers, terse, ticket keys linked.
7. **Write today's note** (create or merge), then sync:
   - `## Goals this week` — the step 2 output, ≤5 lines.
   - `## Prep: <meeting> (<HH:MM>)` — per matched meeting: a bullet per goal (`[[goal]]` + status or shape) with its points nested; ~10 lines each.
   - `## Plan` — `| Time | What |` table, 🎯 on blocks serving a week goal.
   - `## Standup` — the draft.
   - `## Needs reply` — Slack/email items with links (only if any).
   - `## Open` — `- [ ]` checklist, **max 7**, each with its `(since MM-DD)` tag: P1s first, then blockers others wait on, then week-goal work (🎯). A Jira ticket becomes an item only when there's a concrete next action today; other in-progress tickets go on one `In flight:` line of linked keys above the checklist. Overflow is appended to `Dev/Backlog.md` under `## Inbox` (`note.py append`), never dropped. End with `More: [[Dev/Backlog|Backlog]]`.
   - `## Decide` — stale items (3+ workdays), each ending "→ today / backlog / drop?" (only if any), max 5: the oldest beyond that go to `Dev/Backlog.md` `## Inbox`. Never drop these or pick "today" for Nic, even unattended.
   Done when every section above with content is in the note, `## Open` has at most 7 items, and the sync succeeded.
8. **Reply**: the note path (`Dev/Progress/<date>.md`; on path B also `https://git.f1code.com/nic/vault/src/branch/main/Dev/Progress/<date>.md`) and three lines: top priority, first meeting, anything urgent; mention prep sections ("EPI Tech Sync prep: 1 item"). On Fridays add: "Weekly review prep lands this afternoon in Goals/Reviews — /goals review week".
