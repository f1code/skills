Agent skills.  Install in ~/.agents/skills.

3rd party skills are specified in .skill-lock.json.  Update those using:

    npx skills@latest update -g

This will overwrite without confirmation when there are updates, so the top
level of this directory is the updater's blast radius.  Nothing hand-written
belongs here.

Custom skills live in skills/custom, which is a Claude Code "skills-dir plugin"
(.claude-plugin/plugin.json + skills/<name>/SKILL.md).  Claude Code only scans
one level under ~/.claude/skills, so a plain subdirectory would be invisible;
the manifest is what makes the folder load.  No per-machine config is needed.

    custom/
    ├── .claude-plugin/plugin.json
    └── skills/
        └── <skill-name>/SKILL.md

Custom skills are namespaced: invoke them as /custom:<skill-name>.
Verify with `claude plugin details custom@skills-dir`.

Note: omp does not scan subdirectories and needs its own pointer:

    omp config set skills.customDirectories '["~/.agents/skills/custom/skills"]'
