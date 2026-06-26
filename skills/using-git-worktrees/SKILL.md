---
name: using-git-worktrees
description: >
  Create a git worktree to check out a branch in a separate folder without
  disturbing the current working tree. Use when the user wants to work on two
  branches at the same time, switch to a hotfix without stashing, review another
  branch while keeping work in progress, set up filesystem isolation for parallel
  agent tasks, or open a branch in a separate directory.
---

# Git Worktree

## When to Use This Skill

- "I need to fix a hotfix but don't want to lose my current work"
- "Can I check out branch X without stashing?"
- "I want to work on two branches at the same time"
- "Set up a separate folder for branch Y"
- "I need to test/run the app on two branches side by side"
- Starting parallel agent work where each agent needs its own branch checkout
- Any workflow (e.g. `kanban-based-development`) that says "create a worktree"

## Overview

Creates a git worktree under `<worktree root>/<branch-slug>` for a given branch.

## Workflow

1. **Use the current branch** as <base-branch>, unless the user specified a <base-branch>

2. **List all branches** and fuzzy-match the user's input:
   ```bash
   git branch -a --format='%(refname:short)'
   ```
   Filter the list to branches whose name contains the user's search term (case-insensitive substring match).
   **Prioritize local branches** — show them first and prefer them over remote equivalents. Strip `origin/` prefixes and
   de-dupe.

3. **If multiple matches**, prompt the user using the `question` tool to pick one. **If exactly one match, proceed
   without prompting.** If no matches, this is a **new branch**.

4. **Switch to the worktree**:

Worktrees use **worktrunk** (`wt`). Always pass `-y` (non-interactive), 
`--no-cd`, and `--format json` (capture the worktree dir from the `path` field).

   - If this is a new branch:
   ```bash
   wt switch --create <branch> --base <base-branch> -y --format json --no-cd
   ```
   - If you found a match in step 2:
   ```bash
   wt switch <branch> --base <base-branch> -y --format json --no-cd
   ```
