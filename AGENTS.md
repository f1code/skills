# General Rules - Projects can override

## Writing rules: docs, PR text, messages.

- Never touch code or technical terms; swap in everyday words only where precision survives.
- Be extremely concise.  Sacrifice grammar for the sake of brevity.
- Never use a metaphor, simile or other figure of speech which you are used to seeing in print.
- If it is possible to cut a word out, always cut it out.
- Never use the passive where you can use the active.
- Never use corrective juxtaposition.
- Break any of these rules sooner than say anything outright barbarous.

Review every prose output against these rules before delivering.

## Shell Commands

- When searching in bash, use `rg` instead of `grep`

## Planning

- Write the plan as a markdown file under the project plan folder named `YYYY-MM-DD-<short-description>.md`
- Do not make any code changes (write/edit/bash) until instructed to proceed
- When a plan is implemented, move the file to the "implemented" subfolder
- Plan should include: goal, proposed changes (with file paths), and open questions

## Git

 - Do not try to use interactive rebase
 - Concise commits.  One-liner are best.  Expand to clarify rationale **when needed**, do not include technical details
   of the changes.

## Standard Project Layout

(project root)
├── main                     (main development dir & git root)
├── worktrees/               (git worktrees container)
│
├── plans/                   (project plans & docs - no git)
└── research/                (research & exploration - no git)
