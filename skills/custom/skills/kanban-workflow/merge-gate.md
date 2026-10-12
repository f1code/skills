## Merge gate

Parameters: `<task-id>`, `<worktree-path>`, `<target-branch>`, `<claimant>`
(identity that resumes the work).

```bash
uv run <skill-dir>/kanban_review.py gate <task-id> <worktree-path> <target-branch>
```

`<skill-dir>` is the directory holding this file. Present its output to the
user: verdict per axis, finding dispositions, judgment calls, user feedback,
checks, commits. Headers `STALE`, `DIRTY` or `NOT REVIEWED` go first; say
what each means for the merge. Nonzero exit → show stderr tail instead.

On request, also show earlier `## Review round` blocks from
`kanban-md show <task-id>`, or the full patch:

```bash
git -C <worktree-path> diff $(git -C <worktree-path> merge-base HEAD <target-branch>)..HEAD
```

Wait for explicit go-ahead.

- **Approved** — merge from board home, one at a time (single writer on
  `<target-branch>`: every merge validates against the true tip, so no
  non-fast-forward refusals, pre-merge hook contention, or under-tested tips):
  ```bash
  wt merge -C <worktree-path> -y <target-branch>
  kanban-md edit <task-id> --release --status done
  ```
- **Not approved** — do not merge. Record the user's words, then return to
  the caller:
  ```bash
  kanban-md edit <task-id> --claim <claimant> --status in-progress --unblock \
    -a "$(cat <<'EOF'
  ## User feedback
  <words>
  EOF
  )" -t
  ```
  Boards set `require_claim` on `review`/`in-progress`, hence `--claim`. The
  status reset stops the parent poll re-gating a re-prompted child.
- **`wt merge` fails** (rebase conflict): stop merging, leave the conflict
  open in `<worktree-path>`, report the path, and ask the user. Never import
  commits to paper over it — a conflict here usually means a branch was cut
  from the wrong tip, and that is the user's call.
