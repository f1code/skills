---
name: kanban-workflow
description: >
  Default workflow for executing tasks tracked on a kanban-md board.
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

## Multi-Agent Environment

**This board is shared.** Multiple agents and humans may be working on it simultaneously.

- Another agent may claim a task between the time you list it and pick it; availability you saw moments ago may be gone.

The **claim** mechanic is the coordination primitive. **You MUST claim a task before starting any work on it. You MUST only pick unclaimed tasks.**

## Agent Identity

Generate a unique name at the start of the session:

```bash
kanban-md agent-name
```

Remember this name in your context as `<agent>`. Use it as a literal string in all claim/release commands for the rest of the session.

## Workflow

### Step 1: Pick a task

```bash
kanban-md pick --claim <agent> --status todo --tag ready-for-agent --move in-progress --json | jq -r .id
```

If you cannot pick a task (result is null), **STOP** and notify user.
Otherwise note the result in your context as `task-id` 

### Step 2: Determine if the task has children

Number of children:

```bash
kanban-md list --parent <task-id> --json | jq '. | length'
```

### Step 3a: IF THE TASK HAS CHILDREN (PARENT TASK)

Execute the instructions in [kanban-parent-task](./kanban-parent-task.md), providing: <task-id> as parent task ID, <agent> as Agent Identity.

### Step 3b: IF THE TASK HAS NO CHILDREN (LEAF TASK)

Execute the instructions in [kanban-leaf-task](./kanban-leaf-task.md), providing: <task-id> as task ID, <agent> as Agent Identity.

### Step 4: Go back to step 1
