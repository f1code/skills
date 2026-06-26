# General Rules - Projects can override

## Reviewing, giving feedback, commenting code

- Be extremely concise.  Sacrifice grammar for the sake of brevity.

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

 - project root
     - develop -- main working branch
     - kanban -- kanban board
     - worktrees -- git worktrees (use worktrunk)
     - plans -- plan folder - not committed
