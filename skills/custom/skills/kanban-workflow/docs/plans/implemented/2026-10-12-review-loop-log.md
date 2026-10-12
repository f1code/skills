# Review loop log

## Round 4

1. Fable Important → Opus Important; accept. Leaf step 4 exit 3 "rerun prep" → back to step 1, not 2.
2. Fable Important → Opus Important; modify. `verdict` numbers findings per axis (`spec#k`); disposition lines `- <axis>#<k>: fixed <sha>|declined: <reason>`; `prep` pastes disposition sections verbatim, no parser; test render has `spec#1`.
3. Fable Important → Opus Important; accept. kanban-reviewer: exit 3 validation → fix, resubmit; other failure → stop, quote stderr tail.
4. Fable Important → Opus Important; modify. Leaf runs `prep` with max Bash timeout; checks + targeted tests under 10 min.
5. Fable Important → Opus Important; modify. `Branch:` regex ``^\W*Branch:\s*`?([^\s`]+)``, strip trailing `.,;:`; no line → exit 3; shared helper.
6. Fable Important → Opus Important; modify. Standards axis judges `none: <reason>`; Important only when reason fails. Checks section updated to match.
7. Fable Suggestion → Opus Suggestion; modify. Cut fnm auto-wrap; wrappers inline in `## Check commands`; Resolved Node line updated. Card #212 L21 edit noted in plan migration bullet (card outside edit scope).
8. Fable Suggestion → Opus Nit; modify. Drop `Plan:` slot (table row, prompt list); spec axis uses body's plan link, else body.
9. Fable Suggestion → Opus Important; modify. merge-gate `<claimant>` param; not approved = `edit --claim <claimant> --status in-progress -a …`; parent passes `kb-<child-id>`, exited pane `edit --release --status todo`; SKILL.md inline passes `<agent>`.
10. Fable Suggestion → Opus Suggestion; accept. Open-round keep also requires `prep.json.feedback_count` == body count.
11. Fable Suggestion → Opus Suggestion; modify. prep.json `axes` = reviewed only, `carried: {axis: K}`; verdict copies round K result with `carried_from`; scope-table test.
12. Fable Suggestion → Opus Suggestion; accept. Schema `line: int|null`, key required.

## Round 5

1. Fable Important → Opus Important; accept. Leaf re-prompted line (gate rejection or after blocked handoff): write `## User feedback` via `edit --claim --status in-progress --unblock` unless last section; restart pass at round 1. SKILL.md, parent L259 point at it; merge-gate write gains `--unblock`.  Body-section table names leaf as writer.
2. Fable Important → Opus Important; modify. merge-gate approve: `edit --claim <claimant> --status done`; plan names the change; `require_claim` sentence kept.
3. Fable Important → Opus Suggestion; accept. `verdict` sub-headings `###` or lower; disposition heading stdout only; render test checks no `^## ` after first line.
4. Fable Important → Opus Suggestion; modify. Axis table row tagged `ui (phase 2)`; no stub section.
5. Fable Suggestion → Opus Nit; reject. Keep branch serves crash resume (pane exits, child re-picked, HEAD unchanged); saves rerunning submitted reviewers.
6. Fable Suggestion → Opus Nit; modify. Step 6 drops "plus its previous findings and dispositions"; prompt-file spec sole source.
7. Fable Suggestion → Opus Important; modify. `prep` step 4: tree dirty after checks → exit 3, no round; test added; `gate` `DIRTY` header.

## Round 6

1. Fable Important → Opus Important; accept. Section ends at next `^## `, next `[[YYYY-MM-DD]]` stamp line, or EOF (replaces stamp stripping); progress notes after script-read sections carry `-t`; parse test added.
2. Fable Suggestion → Opus Suggestion; modify. `prep` prints only axes lacking `<axis>.json`; keep branch stays; `verdict`, leaf unchanged.
3. Fable Suggestion → Opus Suggestion; modify. Leaf step 6 merged into 5: round 3 CHANGES_REQUESTED → handoff blocked, no fixes, no disposition section.
4. Fable Suggestion → Opus Suggestion; accept. Leaf "on start or re-prompt": last section `## User feedback` → address it; blocked re-prompt writes it first; skip Implement, restart at `prep`, pass round 1.
5. Fable Suggestion → Opus Suggestion; modify. `verdict` indents continuation lines of every reviewer string two spaces, no `#` escaping; render test with `## ` in `fix` and strength.
6. Fable Suggestion → Opus Suggestion; modify. `prep` enforces one 9-min deadline, `start_new_session` + `os.killpg` on timeout, exit 3 `timed out: <cmd> (<source>)`; leaf exit-3 list covers it.
7. Fable Suggestion → Opus Suggestion; modify. `gate` drops branch check (STALE covers it); reads `verdict.json` of highest N that has one.
8. Fable Suggestion → Opus Suggestion; modify. N = max(state dir, body `## Review round N`); no `round-(N-1)/verdict.json` → round-1 scope, no carry; test added.
9. Fable Suggestion → Opus Suggestion; accept. Leaf and merge-gate `## User feedback` writes use quoted heredoc, not `$'…'`.
10. Fable Suggestion → Opus Suggestion; modify. merge-gate approve: `edit --release --status done`.
11. Fable Suggestion → Opus Suggestion; accept. Submit schema drops `axis`; argv only; `verdict` keys by filename.

## Round 7

1. Fable Important → Opus Important; folded (modified). Leaf resume rule keys on unaddressed `## User feedback` (after last `## Review round`); re-prompt in any status records words unless relaying gate feedback; blocked in Step 1 → continue Step 1, else `prep` pass round 1.
2. Fable Important → Opus Important; folded (modified). Prompt passes previous findings only for axes non-APPROVE in N-1; `## Shared` rule covers `fixed <sha>` (verify) and `declined`; test added for APPROVE rerun prompt.
3. Fable Suggestion → Opus Suggestion; folded. Checks deadline uses `Popen` + `communicate(timeout)`, `killpg(p.pid, SIGKILL)` + `wait()` on timeout.
4. Fable Suggestion → Opus Suggestion; folded (modified). Block format: `none: <reason>` in `## Tests run` read only when no fence (fence wins).
