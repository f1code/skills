---
name: kanban-parent-task
description: >
  Launch development tasks for the children of a parent task.
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

## Parent Task

The parent task ID must be provided to you.  **STOP** if the parent task ID is not **explicitly** provided.
You do not need to claim the parent task.

## Workflow

### Step 1: Create Integration Branch

Determine the branch name: use repo convention, or `epic/<ID>-<slug>`.  Save that as <branch-name>.
Create the branch using **worktrunk**:

```bash
wt switch --create task/<task-id>-<slug> -y --no-cd
```

### Step 2: Update Task

Record the branch under the task as a block:

```
Integration branch: <branch-name>
```

### Step 3: Set Child Tasks as Ready

```bash
for task in `kbmd list --status backlog --parent <task-id> --json | jq '.[].id'`; do
    kbmd move $task todo
done
```
