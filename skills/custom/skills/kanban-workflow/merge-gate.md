## Merge gate

Parameters: `<task-id>`, `<worktree-path>`, `<target-branch>`.

```bash
kanban-md show <task-id>
```

Present the user the task's verdict block (appended to its body) plus:

```bash
git -C <worktree-path> diff --stat $(git -C <worktree-path> merge-base HEAD <target-branch>)..HEAD
```

Wait for explicit go-ahead.

- **Approved** — merge from board home, one at a time (single writer on
  `<target-branch>`: every merge validates against the true tip, so no
  non-fast-forward refusals, pre-merge hook contention, or under-tested tips):
  ```bash
  wt merge -C <worktree-path> -y <target-branch>
  kanban-md edit <task-id> --status done
  ```
- **Not approved** — do not merge. Return to the caller with the user's
  feedback; routing it back into the work is the caller's decision.
- **`wt merge` fails** (rebase conflict): stop merging, leave the conflict
  open in `<worktree-path>`, report the path, and ask the user. Never import
  commits to paper over it — a conflict here usually means a branch was cut
  from the wrong tip, and that is the user's call.
