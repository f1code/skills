#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Leaf self-review plumbing: prep, submit, verdict, gate. Exit 3 = leaf can act."""

import argparse
import fnmatch
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
AXES = ("spec", "standards", "complexity", "ui")
ALWAYS_AXES = ("spec", "standards", "complexity")
UI_GLOBS = ("*.css", "*.scss", "*.less", "*.html", "*.tsx", "*.jsx", "*.vue", "*.svelte")
UI_EXCLUDE = ("*.test.*", "*.spec.*")
SEVERITIES = ("critical", "important", "suggestion")
CHECK_DEADLINE = 540
STANDARDS_FILES = ("AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", "CODING_STANDARDS.md")
SCRIPT_SECTIONS = re.compile(
    r"## (Judgment calls|Tests run|User feedback|Finding disposition round \d+|Review round \d+)\s*$"
)
STAMP = re.compile(r"^\[\[\d{4}-\d{2}-\d{2}\]\]")

EXAMPLE = """{
  "strengths": ["Retry loop reuses the existing backoff helper"],
  "findings": [
    {
      "severity": "important",
      "file": "internal/sync/client.go",
      "line": 42,
      "what": "Lock held across HTTP call",
      "why": "Blocks every other sync for the request duration",
      "fix": "Copy the state under the lock, release, then call"
    },
    {
      "severity": "suggestion",
      "file": "internal/sync/client_test.go",
      "line": null,
      "what": "Test name says 'retries' but asserts only the final error",
      "why": "Name promises more than the test checks"
    }
  ]
}"""


class Fail(Exception):
    pass


def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if p.returncode:
        raise subprocess.CalledProcessError(p.returncode, cmd, p.stdout, p.stderr)
    return p.stdout.rstrip("\n")


def git(*args, cwd=None):
    return run(["git", *args], cwd=cwd)


# --- body sections ---------------------------------------------------------


def sections(text):
    """[(heading, content)] for every `## ` heading; ends at next heading, stamp line or EOF."""
    out, cur = [], None
    for line in text.splitlines():
        if line.startswith("## ") or STAMP.match(line):
            if cur:
                out.append(cur)
            cur = (line.rstrip(), []) if line.startswith("## ") else None
        elif cur:
            cur[1].append(line)
    if cur:
        out.append(cur)
    return [(h, "\n".join(c).strip()) for h, c in out]


def last_section(text, name):
    found = [c for h, c in sections(text) if h == f"## {name}"]
    return found[-1] if found else None


def all_sections(text, pattern):
    return [(h, c) for h, c in sections(text) if re.fullmatch(f"## {pattern}", h)]


def feedback_count(body):
    return len(all_sections(body, "User feedback"))


def body_rounds(body):
    return [int(h.rsplit(" ", 1)[1]) for h, _ in all_sections(body, r"Review round \d+")]


def strip_script_sections(body):
    out, skip = [], False
    for line in body.splitlines():
        if line.startswith("## "):
            skip = bool(SCRIPT_SECTIONS.fullmatch(line.rstrip()))
            if skip and out and STAMP.match(out[-1]):
                out.pop()
        elif STAMP.match(line):
            skip = False
        if not skip:
            out.append(line)
    return "\n".join(out).strip()


def fenced_commands(content):
    """Commands of the first fenced bash block, or None when there is no fence."""
    for m in re.finditer(r"^```(\w*)[^\n]*\n(.*?)^```", content or "", re.M | re.S):
        if m.group(1) in ("", "bash", "sh", "shell"):
            cmds = [line.split("#", 1)[0].strip() for line in m.group(2).splitlines()]
            return [c for c in cmds if c]
    return None


def none_reason(content):
    m = re.search(r"^\s*none:\s*(.+)$", content or "", re.M)
    return m.group(1).strip() if m else None


def body_branch(body):
    m = re.search(r"^\W*Branch:\s*`?([^\s`]+)", body, re.M)
    return m.group(1).rstrip(".,;:") if m else None


# --- kanban-md -------------------------------------------------------------


def show_task(task_id):
    task = json.loads(run(["kanban-md", "show", str(task_id), "--json"]))
    task["body"] = task.get("body") or ""
    return task


# --- state -----------------------------------------------------------------


def state_dir(cwd=None):
    return Path(git("rev-parse", "--absolute-git-dir", cwd=cwd)) / "kb-review"


def round_dirs(sd):
    if not sd.is_dir():
        return {}
    return {
        int(m.group(1)): p
        for p in sd.iterdir()
        if p.is_dir() and (m := re.fullmatch(r"round-(\d+)", p.name))
    }


def current_round(sd, body):
    """(N, open) per plan: open only when round-N dir exists without verdict.json."""
    dirs = round_dirs(sd)
    n = max([0, *dirs, *body_rounds(body)])
    if n in dirs and not (dirs[n] / "verdict.json").exists():
        return n, True
    return n + 1, False


def load(path):
    return json.loads(Path(path).read_text())


def open_round(sd):
    dirs = round_dirs(sd)
    d = dirs and dirs[max(dirs)]
    if not d or (d / "verdict.json").exists() or not (d / "prep.json").exists():
        raise Fail("no open round; run prep")
    return d


def check_branch(body):
    want = body_branch(body)
    have = git("branch", "--show-current")
    if not want:
        raise Fail("task body has no `Branch:` line")
    if have != want:
        raise Fail(f"on branch {have!r}, task body says {want!r}")


def dirty_files(cwd=None):
    return git("status", "--porcelain", cwd=cwd)


# --- checks ----------------------------------------------------------------


def check_commands_in(path):
    if not path.is_file():
        return None
    return fenced_commands(last_section(path.read_text(), "Check commands"))


def dirs_up(top):
    """top, then each parent up to $HOME or /."""
    home = Path(os.environ.get("HOME", "/")).resolve()
    yield top
    while top != home and top.parent != top:
        top = top.parent
        yield top


def repo_checks(top):
    for d in dirs_up(top):
        for name in ("AGENTS.md", "CLAUDE.md"):
            cmds = check_commands_in(d / name)
            if cmds:
                return cmds, str(d / name)
    mk = top / "Makefile"
    if mk.is_file():
        rules = re.findall(r"^([A-Za-z0-9_. -]+?)\s*:(?!=)", mk.read_text(), re.M)
        targets = {t for r in rules for t in r.split()}
        if "check" in targets:
            return ["make check"], "Makefile check"
        found = [f"make {t}" for t in ("lint", "test") if t in targets]
        if found:
            return found, "Makefile " + "/".join(c.split()[1] for c in found)
    if (top / "go.mod").is_file():
        return ["go test ./...", "golangci-lint run ./..."], "go.mod"
    return [], "none"


def run_checks(cmds, cwd):
    """cmds: [(cmd, source)]; one deadline over all."""
    deadline = time.monotonic() + CHECK_DEADLINE
    for cmd, source in cmds:
        print(f"$ {cmd}  ({source})", file=sys.stderr)
        p = subprocess.Popen(
            cmd, shell=True, executable="/bin/bash", cwd=cwd, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace",
            start_new_session=True,
        )
        try:
            out, _ = p.communicate(timeout=max(0.0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            # shell=True children (npm, docker) outlive the shell unless the group dies
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            p.wait()
            raise Fail(f"timed out: {cmd} ({source})")
        if p.returncode:
            tail = "\n".join(out.splitlines()[-50:])
            raise Fail(f"check failed: {cmd} ({source}), exit {p.returncode}\n{tail}")


# --- axes ------------------------------------------------------------------


def is_ui_file(f):
    name = Path(f).name
    return any(fnmatch.fnmatch(name, g) for g in UI_GLOBS) and not any(
        fnmatch.fnmatch(name, g) for g in UI_EXCLUDE
    )


def candidate_axes(files):
    return [*ALWAYS_AXES, *(["ui"] if any(map(is_ui_file, files)) else [])]


def triggers(axis, files):
    """Whether a scope's diff warrants a reviewer; an empty diff never does."""
    return bool(files) and (axis != "ui" or any(map(is_ui_file, files)))


def changed(scope, cwd=None):
    return [f for f in git("diff", "--name-only", scope, cwd=cwd).splitlines() if f]


def plan_axes(n, sd, base, head, fb, files, cwd=None):
    """-> (axes, carried, scopes, prev_head, usable previous verdict or None)."""
    prev = None
    pv = sd / f"round-{n - 1}" / "verdict.json"
    if n > 1 and pv.exists():
        prev = load(pv)
        if prev.get("feedback_count") != fb:
            prev = None
    axes, carried, scopes = [], {}, {}
    prev_head = prev["head"] if prev else None
    for axis in candidate_axes(files):
        entry = prev["axes"].get(axis) if prev else None
        if entry and entry["verdict"] == "APPROVE":
            scope = f"{prev_head}..{head}"
            if not triggers(axis, changed(scope, cwd)):
                carried[axis] = entry.get("carried_from", n - 1)
                continue
        else:
            scope = f"{base}..{head}"
        axes.append(axis)
        scopes[axis] = scope
    return axes, carried, scopes, prev_head, prev


# --- prompt ----------------------------------------------------------------


def standards_paths(top):
    paths = [top / n for n in STANDARDS_FILES]
    paths += sorted((top / "docs" / "agents").glob("*.md"))
    paths += [d / "CLAUDE.md" for d in list(dirs_up(top))[1:]]
    return [str(p) for p in paths if p.is_file()]


def render_findings(axis, findings):
    lines = []
    for k, f in enumerate(findings, 1):
        loc = f["file"] + (f":{f['line']}" if f.get("line") is not None else "")
        lines.append(f"- {axis}#{k} [{f['severity']}] {ind(loc)}: {ind(f['what'])}")
        lines.append(f"  why: {ind(f['why'])}")
        if f.get("fix"):
            lines.append(f"  fix: {ind(f['fix'])}")
    return lines


def write_prompt(path, axis, task, top, scope, body, prev, tests_content, checks, check_source):
    script = SKILL_DIR / "kanban_review.py"
    parts = [
        f"# Review: axis `{axis}`, task #{task['id']}: {task['title']}",
        f"Read `## Shared` and `## Axis: {axis}` in `{SKILL_DIR / 'reviewing-changes.md'}`.",
        f"Worktree: `{top}`\nDiff: `git -C {top} diff {scope}`",
        "## Standards files\n" + ("\n".join(f"- {p}" for p in standards_paths(top)) or "(none)"),
        "## Task body\n" + (strip_script_sections(body) or "(empty)"),
    ]
    for h, c in all_sections(body, "User feedback"):
        parts.append(f"{h}\n{c}")
    jc = last_section(body, "Judgment calls")
    parts.append("## Judgment calls\n" + (jc or "(none)"))
    parts.append(
        f"## Checks ({check_source}), all passed\n"
        + ("\n".join(f"- `{c}`" for c in checks) or "(none)")
        + "\n\n## Tests run (replayed, passed)\n"
        + (tests_content or "(none)")
    )
    entry = prev["axes"].get(axis) if prev else None
    if entry and entry["verdict"] != "APPROVE":
        parts.append(
            f"## Your previous findings (round {prev['round']})\n"
            + "\n".join(render_findings(axis, entry["findings"]))
        )
        for h, c in all_sections(body, r"Finding disposition round \d+"):
            parts.append(f"{h}\n{c}")
    parts.append(
        "## Submit\n"
        f"```bash\ncd {top} && uv run {script} submit {axis} <<'JSON'\n<result JSON>\nJSON\n```\n"
        "`line` key required (int or null); `fix` required on critical/important. Example:\n"
        f"```json\n{EXAMPLE}\n```"
    )
    path.write_text("\n\n".join(parts) + "\n")


# --- validation & verdict --------------------------------------------------


def validate(data):
    errs = []
    if not isinstance(data, dict):
        return ["top level must be an object"]
    s = data.get("strengths")
    if not isinstance(s, list) or not all(isinstance(x, str) for x in s):
        errs.append("strengths: list of strings required")
    fs = data.get("findings")
    if not isinstance(fs, list):
        return errs + ["findings: list required"]
    for i, f in enumerate(fs):
        p = f"findings[{i}]"
        if not isinstance(f, dict):
            errs.append(f"{p}: object required")
            continue
        if f.get("severity") not in SEVERITIES:
            errs.append(f"{p}.severity: one of {', '.join(SEVERITIES)}")
        for k in ("file", "what", "why"):
            if not isinstance(f.get(k), str) or not f[k].strip():
                errs.append(f"{p}.{k}: non-empty string required")
        if "line" not in f:
            errs.append(f"{p}.line: key required (int or null)")
        elif f["line"] is not None and (type(f["line"]) is not int):
            errs.append(f"{p}.line: int or null")
        fix = f.get("fix")
        if f.get("severity") in ("critical", "important"):
            if not isinstance(fix, str) or not fix.strip():
                errs.append(f"{p}.fix: required on {f['severity']}")
        elif fix is not None and not isinstance(fix, str):
            errs.append(f"{p}.fix: string")
    return errs


def counts(findings):
    return {s: sum(f["severity"] == s for f in findings) for s in SEVERITIES}


def axis_verdict(c):
    bad = c["critical"] or c["important"] or c["suggestion"] >= 3
    return "CHANGES_REQUESTED" if bad else "APPROVE"


def ind(s):
    # splitlines, not split("\n"): body parsing also breaks on \r, \v, \f, \u2028
    return "\n  ".join(str(s).splitlines())


def render_block(v):
    lines = [
        f"## Review round {v['round']}",
        f"Verdict: {v['verdict']} (head {v['head'][:12]}, checks: {v['check_source']})",
    ]
    for axis, a in v["axes"].items():
        if "carried_from" in a:
            lines.append(f"### {axis}: APPROVE (round {a['carried_from']}, not rerun)")
            continue
        c = a["counts"]
        lines.append(
            f"### {axis}: {a['verdict']} ({a['scope']}; "
            f"{c['critical']} critical, {c['important']} important, {c['suggestion']} suggestion)"
        )
        lines += [f"- strength: {ind(s)}" for s in a["strengths"]]
        lines += render_findings(axis, a["findings"])
    return "\n".join(lines)


# --- subcommands -----------------------------------------------------------


def cmd_prep(task_id, parent):
    task = show_task(task_id)
    body = task["body"]
    check_branch(body)
    if dirty := dirty_files():
        raise Fail("working tree dirty; commit or stash first:\n" + dirty)
    top = Path(git("rev-parse", "--show-toplevel"))
    sd = state_dir()
    n, is_open = current_round(sd, body)
    rd = sd / f"round-{n}"
    head = git("rev-parse", "HEAD")
    fb = feedback_count(body)
    old = load(rd / "prep.json") if is_open and (rd / "prep.json").exists() else {}
    if (old.get("head"), old.get("feedback_count")) != (head, fb) and rd.exists():
        shutil.rmtree(rd)

    base = git("merge-base", "HEAD", parent)
    files = changed(f"{base}..{head}")

    checks, check_source = repo_checks(top)
    tests_content = last_section(body, "Tests run")
    tests = fenced_commands(tests_content) or []
    if check_source == "none" and not tests and not none_reason(tests_content):
        raise Fail("no checks and no targeted tests; list tests you ran in `## Tests run`")
    run_checks([(c, check_source) for c in checks] + [(c, "## Tests run") for c in tests], top)
    if dirty := dirty_files():
        raise Fail("checks modified files: " + ", ".join(
            line[3:] for line in dirty.splitlines()
        ) + "; commit or gitignore them")

    axes, carried, scopes, prev_head, prev = plan_axes(n, sd, base, head, fb, files)
    rd.mkdir(parents=True, exist_ok=True)
    prep = {
        "task_id": task_id, "round": n, "base": base, "head": head, "prev_head": prev_head,
        "feedback_count": fb, "axes": axes, "carried": carried, "scopes": scopes,
        "checks": checks + tests, "check_source": check_source,
    }
    (rd / "prep.json").write_text(json.dumps(prep, indent=2))
    for axis in axes:
        write_prompt(rd / f"{axis}.prompt.md", axis, task, top, scopes[axis], body, prev,
                     tests_content, checks, check_source)
    print(f"round {n}")
    for axis, k in carried.items():
        print(f"carried {axis}: APPROVE (round {k})")
    for axis in axes:
        if not (rd / f"{axis}.json").exists():
            print(f"{axis} {rd / f'{axis}.prompt.md'}")
    return 0


def cmd_submit(axis):
    rd = open_round(state_dir())
    if axis not in load(rd / "prep.json")["axes"]:
        raise Fail(f"axis {axis} not scheduled this round")
    try:
        data = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        raise Fail(f"invalid JSON: {e}\nExample:\n{EXAMPLE}")
    errs = validate(data)
    if errs:
        raise Fail("\n".join(errs) + f"\nExample:\n{EXAMPLE}")
    (rd / f"{axis}.json").write_text(json.dumps(data, indent=2))
    print(f"{axis}: {len(data['findings'])} finding(s) recorded")
    return 0


def cmd_verdict(agent):
    sd = state_dir()
    rd = open_round(sd)
    prep = load(rd / "prep.json")
    body = show_task(prep["task_id"])["body"]
    check_branch(body)
    if git("rev-parse", "HEAD") != prep["head"]:
        raise Fail("HEAD moved since prep; rerun prep")
    missing = [a for a in prep["axes"] if not (rd / f"{a}.json").exists()]
    if missing:
        raise Fail("missing axis results: " + ", ".join(missing))
    n = prep["round"]
    out = {}
    if prep["carried"]:
        prev = load(sd / f"round-{n - 1}" / "verdict.json")
    for axis in [a for a in AXES if a in prep["axes"] or a in prep["carried"]]:
        if axis in prep["carried"]:
            out[axis] = {**prev["axes"][axis], "carried_from": prep["carried"][axis]}
            continue
        r = load(rd / f"{axis}.json")
        c = counts(r["findings"])
        out[axis] = {"verdict": axis_verdict(c), "counts": c, "scope": prep["scopes"][axis],
                     "strengths": r["strengths"], "findings": r["findings"]}
    combined = "CHANGES_REQUESTED" if any(
        a["verdict"] != "APPROVE" for a in out.values()) else "APPROVE"
    v = {"round": n, "verdict": combined, "head": prep["head"],
         "feedback_count": prep["feedback_count"], "axes": out,
         "checks": prep["checks"], "check_source": prep["check_source"]}
    block = render_block(v)
    # body first: a failed append leaves the round open for a rerun
    run(["kanban-md", "edit", str(prep["task_id"]), "-a", block, "-t", "--claim", agent])
    (rd / "verdict.json").write_text(json.dumps(v, indent=2))
    print(block)
    if combined != "APPROVE":
        print(f"\nDisposition heading: ## Finding disposition round {n}")
    return 0


def cmd_gate(task_id, wt, target):
    body = show_task(task_id)["body"]
    wt = Path(wt)
    alive = (wt / ".git").exists()
    dirs = round_dirs(state_dir(cwd=wt)) if alive else {}
    verdicts = {n: load(d / "verdict.json") for n, d in dirs.items() if (d / "verdict.json").exists()}
    head = git("rev-parse", "HEAD", cwd=wt) if alive else None
    out = []
    if not verdicts:
        out.append("NOT REVIEWED")
    else:
        v = verdicts[max(verdicts)]
        if head and head != v["head"]:
            out.append(f"STALE: verdict at {v['head'][:12]}, HEAD {head[:12]}")
        if feedback_count(body) != v["feedback_count"]:
            out.append("STALE: user feedback recorded after verdict")
    if alive and dirty_files(cwd=wt):
        out.append("DIRTY: worktree has uncommitted changes")
    if verdicts:
        out += ["", render_block(v)]
        in_pass = sum(x["feedback_count"] == v["feedback_count"] for x in verdicts.values())
        out.append(f"\nRounds: {max(verdicts)} total, {in_pass} in current pass")
        out.append(f"Check source: {v['check_source']}")
        out += [f"- `{c}`" for c in v["checks"]]
    for h, c in all_sections(body, r"Finding disposition round \d+"):
        out += ["", h, c]
    for name in ("Judgment calls", "Tests run"):
        c = last_section(body, name)
        out += ["", f"## {name}", c or "(none)"]
    for h, c in all_sections(body, "User feedback"):
        out += ["", h, c]
    if alive:
        base = git("merge-base", "HEAD", target, cwd=wt)
        out += ["", "## Commits", git("log", "--oneline", f"{base}..HEAD", cwd=wt),
                "", "## Diff stat", git("diff", "--stat", f"{base}..HEAD", cwd=wt)]
    print("\n".join(out))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="kanban_review.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep")
    p.add_argument("task_id")
    p.add_argument("parent_branch")
    p = sub.add_parser("submit")
    p.add_argument("axis", choices=AXES)
    p = sub.add_parser("verdict")
    p.add_argument("--claim", required=True)
    p = sub.add_parser("gate")
    p.add_argument("task_id")
    p.add_argument("worktree")
    p.add_argument("target_branch")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "prep":
            return cmd_prep(a.task_id, a.parent_branch)
        if a.cmd == "submit":
            return cmd_submit(a.axis)
        if a.cmd == "verdict":
            return cmd_verdict(a.claim)
        return cmd_gate(a.task_id, a.worktree, a.target_branch)
    except Fail as e:
        print(str(e), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
