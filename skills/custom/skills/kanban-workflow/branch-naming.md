## Branch and worktree naming

Precedence, applied once per task:

1. Project convention documented in `AGENTS.md` / `CONTRIBUTING.md`.
2. External ticket id: a `Ticket: <id>` body line, else `[A-Z]{2,}-\d+`
   matched against the body — never sniffed from arbitrary text (`ADR-0002`,
   `RFC-7231` would produce garbage).
3. Default: `epic/<id>-<slug>` for a task with children, `task/<id>-<slug>`
   for a leaf.

`<slug>`: first 3–4 meaningful words of the title, lowercased, spaces/punct
→ hyphens, max 30 chars.
