# Resolving an Obsidian Git merge conflict on the Mac (paths A and C)

Only when Nic asks. Obsidian Git has left the repo mid-merge and written `conflict-files-obsidian-git.md`.

1. Path A only: request delete permission for the vault folder (git must unlink its own lock files). For this procedure, plain git commands (no `GIT_OPTIONAL_LOCKS=0`) are fine on both paths.
2. `git status` to list conflicted files; show them to Nic with a one-line summary of each side.
3. Resolve each file as he says, e.g. `git checkout --theirs -- <file>` (remote copy) or `--ours`, or a hand merge keeping both sides.
4. `git add` each resolved file and delete `conflict-files-obsidian-git.md`.
5. `git commit --no-edit` to finish the merge. No push: Obsidian Git does it.

Done when `git status` shows no unmerged paths and no merge in progress.
