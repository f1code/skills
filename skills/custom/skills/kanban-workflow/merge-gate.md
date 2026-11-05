## Merge gate

Parameters: `<task-id>`, `<worktree-path>`, `<target-branch>`, `<claimant>`
(identity that resumes the work), `<finish>`: `merge` (default) | `pr`.

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

- **Approved, `<finish>` = `pr`** — values: `KEY` from body `Ticket:`,
  `<summary>` = task title, `<dest>` = `<target-branch>` minus `origin/`,
  `<branch>` from body `Branch:`. PR title: project convention
  (`AGENTS.md`/`CONTRIBUTING.md`) first, else `KEY: <summary>`. Approval
  covers notifying PR reviewers.
  - No `PR:` body line → write PR description to a scratchpad `<file>`
    (ticket URL, judgment calls, tests run), then:
    ```bash
    git -C <worktree-path> push -u origin <branch>
    twg bb prs create --source <branch> --dest <dest> \
      --title "<title>" --description-file <file> -o json
    kanban-md edit <task-id> --release --status done -a "PR: <id> <url>" -t
    wt remove --foreground <branch>
    ```
    Check PR id/url field names in output. twg infers workspace/repo from
    the Bitbucket `origin` remote.
  - `PR:` line present:
    ```bash
    git -C <worktree-path> push
    kanban-md edit <task-id> --release --status done -a "pushed <sha> to PR <id>" -t
    wt remove --foreground <branch>
    ```
- **Approved** (`merge`) — merge from board home, one at a time (single writer on
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
