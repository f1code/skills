---
name: kanban-leaf-task
description: >
  Work on a child or standalone task.
allowed-tools:
  - Bash(kanban-md *)
  - Bash(kbmd *)
  - Bash(git *)
  - Bash(go *)
  - Bash(golangci-lint *)
  - Bash(awk *)
  - Bash(date *)
disable-model-invocation: true
---

# Pre-requisites

## Agent Identity

The Agent Identity must be provided to you as <agent>.  Use this in all kanban-md commands: `--claim <agent>`.
**STOP** if the agent identity is not explicitly provided.

## Task ID

The Task ID must be provided to you as <task-id>.
**STOP** if the Task ID is not explicitly provided.

## Task Slug

Several places require a `<slug>`. Derive it from the task title: take the first
3–4 meaningful words, lowercase, replace spaces and punctuation with hyphens,
max 30 chars. Example: "Refactor user auth flow" → `refactor-user-auth`. Use the
same `<slug>` for the branch name (`task/<task-id>-<slug>`) everywhere in the session.

# Main Workflow

## Step 1: Determine integration branch

Check parent task:

```bash
kanban-md show <task-id> --json | jq .parent
```

### If there is a parent task

Read it's body to find the integration branch:

```bash
kanban-md show <parent-task-id> | grep "Integration branch:"
```

If this fails to return an explicit integration branch, **stop** and ask the user.

### If no parent task

The integration branch is the current working branch.

## Step 2: Create or review the plan

Before creating a worktree, confirm:

- [ ] Plan file exists (or plan is included in task body)
- [ ] Plan is linked from the task body, if separate plan file
- [ ] User has explicitly approved (e.g. "proceed", "go ahead", "implement")
- [ ] Open questions in the plan are answered

Otherwise, use /grilling to complete the plan.

Use an Oracle sub-agent to review the plan.  Stop and ask the user if there are open questions.

## Step 3: Create or switch to the worktree

To create the worktree and return its sub-directory:

```bash
wt switch --create task/<task-id>-<slug> -y --no-cd --format json | jq -r .path
```

ALL your changes must be done in the returned directory.

## Step 4: Implement

Ensure ALL changes are made on the worktree branch from step 2.
Implement the smallest change that satisfies the task, depending on the task type:

 - development task: use the /implement skill
 - prototype task: use the /prototype skill
 - research task: use the /research skill

Append progress notes to the task body usin the "Progress Notes" section in References.
Your fixed point for code review is the integration branch determined in the first step.
When running a code review, append the entire returned block to the task body:

```bash
kanban-md edit <task-id> --append-body "<review block>" --timestamp --claim <agent>
```

## Step 5: Hand off for user review

Use the project's "Definition of Done" to ensure the task is ready for review.

Mark the task in review with:

```bash
kanban-md handoff <task-id> --claim <agent>
```

Wait for user's confirmation to proceed.

## Step 6: Merge to integration branch

Ask the user:

 - merge locally to <integration-branch>
 - create a pull request
 - leave unmerged (appropriate for prototype or research tasks)

#### 6.1 Merge locally

If user approves the merge

```bash
cd <worktree directory>
wt merge -y --no-cd <integration-branch>  # will merge the worktree branch onto integration branch
cd <board-home>
```

Then proceed to step 7.

#### 6.2 Pull request

Use the `gh` or `twg` CLI to create a pull request.
Then mark the task as **Blocked**: Waiting for merge.  Use the `Blocked / Needs User Input` reference.

## Step 7: Complete the task

If the task was completed successfully, mark the task as done:

```bash
kanban-md edit <task-id> --release --status done
```

# References 

## Progress notes

While a task is `in-progress`, leave short timestamped notes in the task body from **board home** (especially after major steps or before/after running tests). This makes handoffs and reviews much faster.

```bash
kanban-md edit <task-id> --append-body "Implemented X/Y/Z, now running tests." --timestamp --claim <agent>
```

The `--append-body` (`-a`) flag appends text to the existing body without replacing it. The `--timestamp` (`-t`) flag prefixes a timestamp line like `[[2026-02-10]] Mon 15:04`.

## Blocked / Needs User Input

If you cannot continue without the user (decision, access, environment, or anything outside your control):

From board home:

```bash
kanban-md handoff <ID> --claim <agent> \
  --block "Waiting on user: <what you need>" \
  --note "## Handoff
- Current state:
- Branch (if any):
- Open questions (A/B):
- Next step:" \
  --timestamp --release
```

In your handoff note, include:

- The exact question(s) for the user (prefer A/B options)
- What you already tried and what happened
- The minimal next step after the user responds
