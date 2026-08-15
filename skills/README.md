Agent skills.  Install in ~/.agents/skills.

3rd party skills are specified in skill-lock.json.  Update those using:

    npx skills@latest update -g

This will overwrite without confirmation when there are updates.

Custom skills are in skills/custom.  omp does not scan subdirectories, so it needs:

    omp config set skills.customDirectories '["~/.agents/skills/custom"]'

Set this on every machine.  Without it, skills/custom is invisible.
