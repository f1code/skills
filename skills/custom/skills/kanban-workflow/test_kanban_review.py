import io
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))
import kanban_review as kr  # noqa: E402

SCRIPT = Path(kr.__file__)

FAKE_KANBAN = r"""#!/usr/bin/env python3
import json, os, sys
body = os.environ["KB_BODY"]
with open(os.environ["KB_LOG"], "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\n")
a = sys.argv[1:]
if a[0] == "show":
    print(json.dumps({"id": int(a[1]), "title": "Task", "body": open(body).read()}))
elif a[0] == "edit":
    text = a[a.index("-a") + 1]
    stamp = "\n[[2026-10-12]] Mon 15:15\n" if "-t" in a else "\n"
    with open(body, "a") as f:
        f.write(stamp + text + "\n")
"""

CHECKS_MD = "## Check commands\n\n```bash\ntrue   # lint\n```\n"
BODY = "Do the thing.\n\nBranch: `feat/x`.\n\n[[2026-10-12]] Mon 10:00\n## Tests run\n```bash\ntrue\n```\n"


def sh(*cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class Env:
    def __init__(self, tmp, monkeypatch, capsys):
        self.tmp, self.mp, self.capsys = tmp, monkeypatch, capsys
        self.body = tmp / "body.md"
        self.log = tmp / "kb.log"
        self.repo = tmp / "proj" / "main"
        self.repo.mkdir(parents=True)

    @property
    def text(self):
        return self.body.read_text()

    def append(self, s):
        self.body.write_text(self.text + s)

    def commit(self, name, content="x\n", cwd=None):
        cwd = cwd or self.repo
        (cwd / name).parent.mkdir(parents=True, exist_ok=True)
        (cwd / name).write_text(content)
        sh("git", "add", "-A", cwd=cwd)
        sh("git", "commit", "-qm", f"add {name}", cwd=cwd)
        return sh("git", "rev-parse", "HEAD", cwd=cwd)

    def call(self, *argv, stdin=""):
        self.capsys.readouterr()
        self.mp.setattr(sys, "stdin", io.StringIO(stdin))
        code = kr.main(list(argv))
        out, err = self.capsys.readouterr()
        return code, out, err

    def submit(self, axis, findings=(), strengths=("ok",)):
        return self.call("submit", axis, stdin=json.dumps(
            {"strengths": list(strengths), "findings": list(findings)}))

    def rounds(self):
        return self.repo / ".git" / "kb-review"

    def prep_json(self, n):
        return json.loads((self.rounds() / f"round-{n}" / "prep.json").read_text())


IMPORTANT = {"severity": "important", "file": "a.py", "line": 1, "what": "w", "why": "y", "fix": "f"}
SUGGESTION = {"severity": "suggestion", "file": "a.py", "line": None, "what": "w", "why": "y"}


@pytest.fixture
def env(tmp_path, monkeypatch, capsys):
    e = Env(tmp_path, monkeypatch, capsys)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "kanban-md"
    fake.write_text(FAKE_KANBAN)
    fake.chmod(0o755)
    for k, v in {
        "PATH": f"{bindir}:{os.environ['PATH']}", "HOME": str(tmp_path),
        "KB_BODY": str(e.body), "KB_LOG": str(e.log),
        "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }.items():
        monkeypatch.setenv(k, v)
    sh("git", "init", "-qb", "main", cwd=e.repo)
    e.commit("AGENTS.md", CHECKS_MD)
    sh("git", "checkout", "-qb", "feat/x", cwd=e.repo)
    e.commit("a.py")
    e.body.write_text(BODY)
    monkeypatch.chdir(e.repo)
    return e


# --- pure parsing ----------------------------------------------------------


def test_section_ends_at_stamp_heading_or_eof():
    body = textwrap.dedent("""\
        intro
        [[2026-10-12]] Mon 10:00
        ## Judgment calls
        - one
        [[2026-10-12]] Mon 10:05
        progress note
        [[2026-10-12]] Mon 10:06
        ## User feedback
        fix colors
        [[2026-10-12]] Mon 10:07
        another note
        ## Judgment calls
        - two
        ## User feedback
        more""")
    assert kr.last_section(body, "Judgment calls") == "- two"
    assert [c for _, c in kr.all_sections(body, "User feedback")] == ["fix colors", "more"]
    assert "progress note" not in kr.all_sections(body, "Judgment calls")[0][1]
    assert kr.feedback_count(body) == 2


def test_strip_script_sections_keeps_other_text():
    body = "intro\n[[2026-10-12]] x\n## Judgment calls\n- j\n[[2026-10-12]] y\nnote\n## Review round 1\nold\n## Notes\nkeep"
    out = kr.strip_script_sections(body)
    assert "- j" not in out and "old" not in out
    assert "note" in out and "## Notes\nkeep" in out and "intro" in out
    assert "[[2026-10-12]] x" not in out


def test_fenced_commands_and_none():
    c = "text\n```bash\nmake lint   # lint\n\ncd fe && npm test\n```\n```bash\nignored\n```"
    assert kr.fenced_commands(c) == ["make lint", "cd fe && npm test"]
    assert kr.fenced_commands("none: research task") is None
    assert kr.none_reason("none: research task") == "research task"
    assert kr.fenced_commands(None) is None
    assert kr.fenced_commands("```python\nx = 1\n```\n```bash\nmake t\n```") == ["make t"]


@pytest.mark.parametrize("line,want", [
    ("Branch: `feat/x`", "feat/x"),
    ("- **Branch: feat/y.", "feat/y"),
    ("Branch: feat/z;", "feat/z"),
    ("no branch here", None),
    ("see Branch: x", None),
])
def test_body_branch(line, want):
    assert kr.body_branch("title\n" + line + ("\nBranch: other" if want else "")) == want


def test_example_validates_and_fix_required():
    data = json.loads(kr.EXAMPLE)
    assert kr.validate(data) == []
    severities = {f["severity"] for f in data["findings"]}
    assert {"important", "suggestion"} <= severities
    del data["findings"][0]["fix"]
    assert any("fix" in e for e in kr.validate(data))


@pytest.mark.parametrize("mutate", [
    lambda d: d["findings"][0].pop("line"),
    lambda d: d["findings"][0].update(line=True),
    lambda d: d["findings"][0].update(severity="nit"),
    lambda d: d["findings"][0].update(what=""),
    lambda d: d.update(strengths="x"),
    lambda d: d.pop("findings"),
])
def test_schema_rejects(mutate):
    data = json.loads(kr.EXAMPLE)
    mutate(data)
    assert kr.validate(data)


def test_schema_rejects_non_object():
    assert kr.validate([]) == ["top level must be an object"]


@pytest.mark.parametrize("c,want", [
    ({"critical": 1, "important": 0, "suggestion": 0}, "CHANGES_REQUESTED"),
    ({"critical": 0, "important": 1, "suggestion": 0}, "CHANGES_REQUESTED"),
    ({"critical": 0, "important": 0, "suggestion": 3}, "CHANGES_REQUESTED"),
    ({"critical": 0, "important": 0, "suggestion": 2}, "APPROVE"),
])
def test_axis_verdict(c, want):
    assert kr.axis_verdict(c) == want


def test_ui_trigger():
    assert kr.candidate_axes(["src/App.tsx"])[-1] == "ui"
    assert "ui" not in kr.candidate_axes(["src/App.test.tsx", "x.spec.css", "a.py"])
    assert "ui" not in kr.candidate_axes([])
    assert kr.triggers("spec", []) is False
    assert kr.triggers("ui", ["a.py"]) is False


def test_render_has_no_heading_after_first_line():
    v = {"round": 2, "verdict": "CHANGES_REQUESTED", "head": "a" * 40, "check_source": "x",
         "axes": {
             "spec": {"verdict": "CHANGES_REQUESTED", "scope": "b..h",
                      "counts": {"critical": 0, "important": 1, "suggestion": 0},
                      "strengths": ["good\n## x", "cr\r## User feedback\u2028## y"],
                      "findings": [{**IMPORTANT, "fix": "do\n## User feedback\nx",
                                    "why": "w\n[[2026-10-12]] fake"}]},
             "standards": {"verdict": "APPROVE", "carried_from": 1}}}
    block = kr.render_block(v)
    lines = block.splitlines()
    assert lines[0] == "## Review round 2"
    assert not any(l.startswith("## ") or kr.STAMP.match(l) for l in lines[1:])
    assert "spec#1" in block and "APPROVE (round 1, not rerun)" in block
    body = "## User feedback\nhi\n" + block
    assert kr.feedback_count(body) == 1


# --- prep / submit / verdict ----------------------------------------------


def run_round(env, results):
    code, out, err = env.call("prep", "1", "main")
    assert code == 0, err
    for axis, findings in results.items():
        assert env.submit(axis, findings)[0] == 0
    code, out, err = env.call("verdict", "--claim", "kb-1")
    assert code == 0, err
    return out


def test_body_round_and_empty_state_dir_gives_next_round(env):
    env.append("\n## Review round 2\nVerdict: APPROVE\n")
    assert env.call("prep", "1", "main")[0] == 0
    p = env.prep_json(3)
    assert p["round"] == 3 and p["carried"] == {} and p["prev_head"] is None
    assert set(p["axes"]) == {"spec", "standards", "complexity"}
    assert all(s.startswith(p["base"]) for s in p["scopes"].values())


def test_round_dirs_sort_numerically(env):
    for n in (9, 10):
        (env.rounds() / f"round-{n}").mkdir(parents=True)
        (env.rounds() / f"round-{n}" / "verdict.json").write_text("{}")
    assert kr.current_round(env.rounds(), "") == (11, False)


def test_full_flow_carry_chain(env):
    out = run_round(env, {"spec": [], "standards": [IMPORTANT], "complexity": []})
    assert "Verdict: CHANGES_REQUESTED" in out
    assert "## Finding disposition round 1" in out
    assert json.loads(env.log.read_text().splitlines()[-1])[-2:] == ["--claim", "kb-1"]
    assert "## Review round 1" in env.text

    # same HEAD: approved axes carry, non-APPROVE reruns on base..HEAD
    code, out, _ = env.call("prep", "1", "main")
    p = env.prep_json(2)
    assert p["axes"] == ["standards"] and p["carried"] == {"spec": 1, "complexity": 1}
    assert p["scopes"]["standards"] == f"{p['base']}..{p['head']}"
    assert "carried spec" in out
    env.submit("standards", [IMPORTANT])
    env.call("verdict", "--claim", "kb-1")

    env.call("prep", "1", "main")
    p = env.prep_json(3)
    assert p["carried"] == {"spec": 1, "complexity": 1}
    env.submit("standards", [])
    code, out, _ = env.call("verdict", "--claim", "kb-1")
    v = json.loads((env.rounds() / "round-3" / "verdict.json").read_text())
    assert v["verdict"] == "APPROVE"
    assert v["axes"]["spec"]["carried_from"] == 1
    assert "spec: APPROVE (round 1, not rerun)" in out


def test_new_commit_reruns_approved_axis_on_incremental_scope(env):
    run_round(env, {"spec": [], "standards": [IMPORTANT], "complexity": []})
    prev = env.prep_json(1)["head"]
    head = env.commit("b.py")
    env.call("prep", "1", "main")
    p = env.prep_json(2)
    assert p["carried"] == {}
    assert p["scopes"]["spec"] == f"{prev}..{head}"
    assert p["scopes"]["standards"] == f"{p['base']}..{head}"


def test_feedback_starts_new_pass_with_same_head(env):
    run_round(env, {"spec": [], "standards": [], "complexity": []})
    env.append("\n[[2026-10-12]] Mon 11:00\n## User feedback\nrename it\n")
    env.call("prep", "1", "main")
    p = env.prep_json(2)
    assert p["carried"] == {} and p["prev_head"] is None
    assert set(p["axes"]) == {"spec", "standards", "complexity"}
    assert p["feedback_count"] == 1
    assert "rename it" in (env.rounds() / "round-2" / "spec.prompt.md").read_text()


def test_previous_findings_only_for_non_approve_axis(env):
    run_round(env, {"spec": [], "standards": [IMPORTANT], "complexity": []})
    env.commit("b.py")
    env.append("\n[[2026-10-12]] x\n## Finding disposition round 1\n- standards#1: declined: nope\n")
    env.call("prep", "1", "main")
    rd = env.rounds() / "round-2"
    spec = (rd / "spec.prompt.md").read_text()
    std = (rd / "standards.prompt.md").read_text()
    assert "previous findings" not in spec and "declined: nope" not in spec
    assert "## Review round" not in spec
    assert "standards#1" in std and "declined: nope" in std


def test_prompt_contents(env):
    env.append("\n[[2026-10-12]] x\n## Judgment calls\n- chose A\n")
    (env.tmp / "proj" / "CLAUDE.md").write_text("root rules")
    env.call("prep", "1", "main")
    p = env.prep_json(1)
    t = (env.rounds() / "round-1" / "spec.prompt.md").read_text()
    assert f"git -C {env.repo} diff {p['base']}..{p['head']}" in t
    assert "- chose A" in t and "Do the thing." in t
    assert str(env.tmp / "proj" / "CLAUDE.md") in t and str(env.repo / "AGENTS.md") in t
    assert "## Axis: spec" in t and "submit spec <<'JSON'" in t
    assert t.count("## Judgment calls") == 1


def test_crash_resume_keeps_submitted_results(env):
    env.call("prep", "1", "main")
    env.submit("spec", [])
    code, out, _ = env.call("prep", "1", "main")
    assert (env.rounds() / "round-1" / "spec.json").exists()
    assert "spec " not in out and "standards " in out
    env.commit("b.py")
    env.call("prep", "1", "main")
    assert not (env.rounds() / "round-1" / "spec.json").exists()


def test_ui_axis_scheduled(env):
    env.commit("web/App.tsx")
    env.call("prep", "1", "main")
    assert "ui" in env.prep_json(1)["axes"]


def test_ui_carries_when_no_ui_change(env):
    env.commit("web/App.tsx")
    run_round(env, {"spec": [IMPORTANT], "standards": [], "complexity": [], "ui": []})
    env.commit("b.py")
    env.call("prep", "1", "main")
    p = env.prep_json(2)
    assert p["carried"] == {"ui": 1}
    assert set(p["axes"]) == {"spec", "standards", "complexity"}


def test_prep_branch_mismatch(env):
    sh("git", "checkout", "-qb", "other", cwd=env.repo)
    code, _, err = env.call("prep", "1", "main")
    assert code == 3 and "feat/x" in err


def test_prep_no_branch_line(env):
    env.body.write_text("nothing")
    assert env.call("prep", "1", "main")[0] == 3


def test_prep_dirty_tree(env):
    (env.repo / "new.txt").write_text("u")
    code, _, err = env.call("prep", "1", "main")
    assert code == 3 and "dirty" in err


def test_failing_checks_exit_3_no_round(env):
    env.body.write_text(BODY.replace("true\n```", "echo boom; exit 4\n```"))
    code, _, err = env.call("prep", "1", "main")
    assert code == 3 and "exit 4" in err and "boom" in err
    assert not (env.rounds() / "round-1").exists()


def test_checks_modifying_files_exit_3_no_round(env):
    env.body.write_text(BODY.replace("true\n```", "touch gen.out\n```"))
    code, _, err = env.call("prep", "1", "main")
    assert code == 3 and "checks modified files: gen.out" in err
    assert not (env.rounds() / "round-1").exists()


def test_checks_modifying_tracked_file(env):
    env.body.write_text(BODY.replace("true\n```", "echo y >> a.py\n```"))
    code, _, err = env.call("prep", "1", "main")
    assert code == 3 and "checks modified files: a.py;" in err


def test_checks_run_in_bash_tolerate_binary_output(env):
    env.body.write_text(BODY.replace("true\n```", "[[ 1 == 1 ]] && printf '\\xff\\n'\n```"))
    assert env.call("prep", "1", "main")[0] == 0


def test_check_timeout(env, monkeypatch):
    monkeypatch.setattr(kr, "CHECK_DEADLINE", 1)
    env.body.write_text(BODY.replace("true\n```", "sleep 30\n```"))
    code, _, err = env.call("prep", "1", "main")
    assert code == 3 and "timed out: sleep 30 (## Tests run)" in err


def test_no_checks_and_no_tests(env):
    env.commit("AGENTS.md", "nothing")
    env.body.write_text("Branch: feat/x\n")
    code, _, err = env.call("prep", "1", "main")
    assert code == 3 and "no checks and no targeted tests" in err
    env.body.write_text("Branch: feat/x\n## Tests run\nnone: research spike\n")
    assert env.call("prep", "1", "main")[0] == 0
    assert env.prep_json(1)["check_source"] == "none"


def test_check_source_order(env):
    top = env.repo
    assert kr.repo_checks(top) == (["true"], str(top / "AGENTS.md"))
    env.commit("AGENTS.md", "x")
    (env.tmp / "proj" / "CLAUDE.md").write_text(CHECKS_MD.replace("true", "echo up"))
    assert kr.repo_checks(top) == (["echo up"], str(env.tmp / "proj" / "CLAUDE.md"))
    (env.tmp / "proj" / "CLAUDE.md").unlink()
    env.commit("Makefile", "lint test: deps\n\ttrue\nX := 1\n")
    assert kr.repo_checks(top) == (["make lint", "make test"], "Makefile lint/test")
    env.commit("Makefile", "check:\n\ttrue\n")
    assert kr.repo_checks(top)[0] == ["make check"]
    env.commit("Makefile", "")
    env.commit("go.mod", "module x\n")
    assert kr.repo_checks(top)[1] == "go.mod"


def test_submit_errors(env):
    code, _, err = env.submit("spec")
    assert code == 3 and "no open round" in err
    env.call("prep", "1", "main")
    code, _, err = env.call("submit", "spec", stdin="not json")
    assert code == 3 and '"strengths"' in err
    code, _, err = env.submit("spec", [{**IMPORTANT, "fix": ""}])
    assert code == 3 and "fix" in err
    code, _, err = env.submit("ui")
    assert code == 3 and "not scheduled" in err
    assert not (env.rounds() / "round-1" / "spec.json").exists()


def test_verdict_errors(env):
    assert env.call("verdict", "--claim", "a")[0] == 3
    env.call("prep", "1", "main")
    env.submit("spec")
    code, _, err = env.call("verdict", "--claim", "a")
    assert code == 3 and "standards" in err and "complexity" in err
    env.commit("b.py")
    code, _, err = env.call("verdict", "--claim", "a")
    assert code == 3 and "rerun prep" in err


def test_verdict_append_failure_keeps_round_open(env, monkeypatch):
    env.call("prep", "1", "main")
    for a in ("spec", "standards", "complexity"):
        env.submit(a)
    real = kr.run
    def boom(cmd, *a, **k):
        if cmd[:2] == ["kanban-md", "edit"]:
            raise subprocess.CalledProcessError(1, cmd)
        return real(cmd, *a, **k)
    monkeypatch.setattr(kr, "run", boom)
    with pytest.raises(subprocess.CalledProcessError):
        kr.main(["verdict", "--claim", "a"])
    monkeypatch.setattr(kr, "run", real)
    assert env.call("verdict", "--claim", "a")[0] == 0
    assert env.text.count("## Review round 1") == 1


def test_null_body(env, monkeypatch):
    monkeypatch.setattr(kr, "run", lambda *a, **k: '{"id": 1, "body": null}')
    assert kr.show_task(1)["body"] == ""


def test_killpg_race(env, monkeypatch):
    monkeypatch.setattr(kr, "CHECK_DEADLINE", 0.5)
    def gone(*a):
        raise ProcessLookupError
    monkeypatch.setattr(kr.os, "killpg", gone)
    with pytest.raises(kr.Fail, match="timed out"):
        kr.run_checks([("sleep 1", "x")], env.repo)


def test_verdict_three_suggestions(env):
    out = run_round(env, {"spec": [SUGGESTION] * 3, "standards": [SUGGESTION] * 2, "complexity": []})
    v = json.loads((env.rounds() / "round-1" / "verdict.json").read_text())
    assert v["axes"]["spec"]["verdict"] == "CHANGES_REQUESTED"
    assert v["axes"]["standards"]["verdict"] == "APPROVE"
    assert v["verdict"] == "CHANGES_REQUESTED" and "spec#3" in out


# --- gate ------------------------------------------------------------------


def test_gate(env):
    code, out, _ = env.call("gate", "1", str(env.repo), "main")
    assert code == 0 and out.startswith("NOT REVIEWED")
    run_round(env, {"spec": [], "standards": [], "complexity": []})
    code, out, _ = env.call("gate", "1", str(env.repo), "main")
    assert "STALE" not in out and "Verdict: APPROVE" in out
    env.append("\n[[2026-10-12]] Mon 16:00\n## User feedback\nmore\n")
    assert "STALE: user feedback" in env.call("gate", "1", str(env.repo), "main")[1]
    assert "Rounds: 1 total, 1 in current pass" in out and "add a.py" in out
    assert "a.py" in out.split("## Diff stat")[1]
    env.commit("b.py")
    (env.repo / "c.txt").write_text("dirty")
    code, out, _ = env.call("gate", "1", str(env.repo), "main")
    assert "STALE: verdict at" in out and "DIRTY" in out


def test_gate_worktree_gone(env):
    code, out, _ = env.call("gate", "1", str(env.tmp / "gone"), "main")
    assert code == 0 and "NOT REVIEWED" in out and "## Tests run" in out


def test_worktree_state_isolated(env):
    wt = env.tmp / "proj" / "worktrees" / "x"
    sh("git", "checkout", "-q", "main", cwd=env.repo)
    sh("git", "worktree", "add", "-q", str(wt), "feat/x", cwd=env.repo)
    env.mp.chdir(wt)
    assert env.call("prep", "1", "main")[0] == 0
    assert not env.rounds().exists()
    assert list((env.repo / ".git" / "worktrees").glob("*/kb-review/round-1/prep.json"))
    t = next((env.repo / ".git" / "worktrees").glob("*/kb-review/round-1/spec.prompt.md")).read_text()
    assert f"cd {wt} && uv run" in t


# --- script as a program ---------------------------------------------------


def test_script_header_and_exit_codes(env):
    lines = SCRIPT.read_text().splitlines()
    assert lines[0] == "#!/usr/bin/env -S uv run --script"
    assert lines[1] == "# /// script"
    run = lambda *a: subprocess.run([sys.executable, str(SCRIPT), *a], capture_output=True,
                                    text=True, input="{}")
    assert run().returncode == 2
    assert run("submit", "bogus").returncode == 2
    r = run("submit", "spec")
    assert r.returncode == 3 and "no open round" in r.stderr
