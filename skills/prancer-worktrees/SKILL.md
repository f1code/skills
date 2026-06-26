---
name: prancer-worktrees
description: Use when creating a worktree for prancer
---

1. **Determine the branch name** (BRANCH)

The branch name is based on the JIRA ticket which will have the form PRANCER-XXXX.
Determine the slug based on the request (either the sanitized plan name, or a 2-3 word summary)
For a new feature, use feature/PRANCER-XXXX-<slug>
For a bug fix, use fix/PRANCER-XXXX-<slug>
If unsure, use task/PRANCER-XXXX-<slug>

Note both the BRANCH, the TICKET_ID, and the TICKET_NUMBER: numeric part (XXXX) of the TICKET_ID.

2. **Create worktree** (from main repo):
```bash
WORKTREE_DIR="$HOME/prancer/worktrees/$(echo "$BRANCH" | sed 's|.*/||')"
git worktree add -b "$BRANCH" "$WORKTREE_DIR"
```

Note the WORKTREE_DIR.

3. **Determine a stack id**

The currently used stack id are:

```bash
cd ~/prancer
rg --no-filename --no-line-number -g .env 'STACK_ID=.+$' | cut -d = -f 2
```

If our TICKET_NUMBER is not used, keep that as STACK_ID.
Otherwise, suffix a random digit.

Write the STACK_ID to the worktree:

```bash
echo STACK_ID=$STACK_ID > $WORKTREE_DIR/.env
```

4. **Build docker, wait for db, clone test db**
```bash
set -e
cd "$WORKTREE_DIR"

echo "=== Building docker (stack-id: $STACK_ID) ==="
./tools/bin/docker-build.sh -g -d --stack-id "$STACK_ID"

echo "=== Waiting for db-builder container to finish ==="
# The container name includes the stack id in the project name
# Wait indefinitely — db-builder can take a long time
docker wait $(docker ps -aq --filter "name=.*${STACK_ID}.*db-builder.*")

echo "=== Cloning test db ==="
./tools/bin/clone-test-db.sh
```


Substitute `$WORKTREE_DIR`, and `$STACK_ID` with actual values. Use single quotes for the outer bash -c string and
escape/interpolate as needed.
