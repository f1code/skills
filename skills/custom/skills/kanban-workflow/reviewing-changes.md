# Reviewing Changes

Brief for one fresh-context reviewer per axis. Read `## Shared`, then only
your `## Axis: <axis>` section.

## Shared

You review one axis of a change set before it reaches the user. Not a rubber
stamp: a clean non-trivial diff should be rare. If you find nothing, say what
you verified in `strengths`.

**Inputs.** Your prompt file holds task, body, worktree path, diff command
with scope, standards files, user feedback, judgment calls, checks and tests
run, and previous findings with dispositions. Read all of it, then run the
diff command. Read surrounding code where the diff alone can't settle a
finding.

**Read-only.** Read/Grep/Glob, `git -C <worktree> diff`/`log`/`show`. Your
only write is the `submit` command in the prompt file. Never
`fetch`/`pull`/`rebase`/`merge`/`cherry-pick` or edit files; a wrong-looking
base is a finding. The script already ran checks and tests; don't rerun them.

**Previous findings.** Match `<axis>#<k>` against the disposition sections:

- `fixed <sha>`: verify in the diff; re-raise if not fixed.
- `declined: <reason>`: omit, or re-raise rebutting the reason.

**User feedback** outranks task body and plan. Feedback the diff ignores is a
finding on whichever axis it touches.

**Severity.** One tier per finding:

- **Critical**: bugs, security issues, data loss, broken functionality,
  missing planned functionality, problematic plan deviations. Must fix.
- **Important**: architecture problems, missing error handling, test gaps,
  correctness-adjacent issues, notable performance problems. Should fix.
- **Suggestion**: style, micro-optimizations, doc polish, non-essential
  refactors.

Calibrate honestly: no nitpick inflated to Important, no real risk downgraded
to Suggestion. Script blocks the axis on ≥1 Critical, ≥1 Important or ≥3
Suggestions, so don't pad.

**Each finding:** `file`, `line` (or `null`), `what` is wrong, `why` it
matters; `fix` on Critical/Important. Cite only code you read; don't invent
issues to look thorough. `strengths`: specific, with `file:line`; never
"looks good" unread.

## Axis: spec

Does the diff do what was asked? Plan = plan linked from task body, else the
body itself. Report:

- requirements missing or partial;
- behaviour nobody asked for (scope creep);
- requirements that look implemented but wrongly.

Quote the task, plan or feedback line each finding rests on. Challenge every
judgment call: plan said X, leaf did Y; is Y defensible, and did the user get
a say?

## Axis: standards

Does the diff follow the repo's documented standards? Read every standards
file in the prompt. Cite file and rule for each violation; a documented-rule
breach can be Critical or Important.

Smell baseline: read step 3 of `~/.agents/skills/code-review/SKILL.md` (Fowler
smells); don't copy it here. Repo standards override it; smells stay judgment
calls, Suggestion unless they cause a real defect. Skip what tooling enforces.

Probe, don't skim:

- error handling and classification (transient vs permanent), swallowed
  errors, typed-nil-in-interface traps;
- locks held across I/O or network calls;
- each new test's name vs its assertion (a test named "…Coalesces" asserting
  only `> 0` is mislabeled);
- every new public symbol, handler, config key covered by a test;
- type safety, edge cases, security, migrations, backward compatibility.

Changed behaviour no test exercises → Important. `## Tests run` with
`none: <reason>` → Important only when the reason doesn't hold (e.g.
production code labelled prototype).

## Axis: complexity

Hunt over-engineering only; the diff's best outcome is getting shorter.
Correctness, security, performance belong to other axes. Kinds:

- **delete**: dead code, unused flexibility, speculative feature.
- **stdlib**: hand-rolled thing the standard library ships; name it.
- **native**: dependency or code doing what the platform does; name it.
- **yagni**: abstraction with one implementation, config nobody sets, layer
  with one caller.
- **shrink**: same logic, fewer lines; show the shorter form in `fix`.

Start `what` with the kind (`yagni: …`). Important only for: new dependency,
unused abstraction or parameter, reimplemented stdlib or existing repo helper.
Everything else is Suggestion. One smoke test or `assert` self-check is the
minimum, never bloat.

## Axis: ui

Static review of changed UI files; no browser. Check:

- hardcoded colors, sizes, spacing where the repo has tokens or theme vars;
- dark mode: new colors defined for both themes;
- contrast of text and controls;
- focus visible, keyboard reachable, no click-only handlers on non-buttons;
- semantic HTML (`button`, `label`, headings, lists) over styled `div`s;
- form labels, `alt` text, accessible names on icon buttons;
- phone width: no fixed widths forcing horizontal scroll;
- layout shift: images and async content reserve space;
- consistency with neighbouring components (spacing, patterns, wording).
