#!/usr/bin/env python3
"""Load and query goal notes in <vault>/Goals/. One loader for the goals and daily skills.

  goals.py tree     VAULT [--date D]   open goals covering D as a tree, Backlog as 💭 leaves
  goals.py check    VAULT [--date D]   health check: YAML errors, orphans, broken parents, caps, stale, TBD
  goals.py week     VAULT [--date D]   open Week goals covering D (+ parent names), for daily notes
  goals.py meetings VAULT [--date D]   discuss_at name -> open or Backlog goals tagged with it
  goals.py json     VAULT              every goal as JSON

D defaults to today in Europe/Brussels. Goals/Reviews/ is not read (non-recursive).
Uses PyYAML when installed, else a built-in parser for flat frontmatter.
"""
import datetime as dt, glob, json, os, re, sys
from collections import defaultdict

try:
    import yaml
except ImportError:  # e.g. the Mac's device shell
    yaml = None

OPEN = {"Active", "On track", "At risk"}
CLOSED = {"Done", "Dropped", "Rolled over"}
EMOJI = {"Active": "🔵", "On track": "🟢", "At risk": "🟠", "Done": "✅",
         "Dropped": "⚪", "Rolled over": "↪️", "Backlog": "💭"}
ORDER = ["Decade", "Year", "Month", "Week"]
CAPS = {"Decade": 5, "Year": 6, "Month": 5, "Week": 5}
FM = re.compile(r"\A---\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)


def _scalar(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    v = re.sub(r"\s+#.*$", "", v)
    return None if v in ("", "~", "null") else v


def _mini_yaml(text):
    """Parse flat `key: value` lines and block lists (`key:` + `  - item`)."""
    out, key = {}, None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^\s+-\s*(.*)$", line)
        if m and key is not None:
            if not isinstance(out[key], list):
                out[key] = []
            out[key].append(_scalar(m.group(1)))
            continue
        m = re.match(r"^([^\s:][^:]*):(?:\s+(.*))?$", line)
        if not m:
            raise ValueError(f"can't parse line: {line!r}")
        key, val = m.group(1).strip(), (m.group(2) or "").strip()
        out[key] = [] if val == "[]" else _scalar(val)
    return out


def _parse(text):
    return yaml.safe_load(text) if yaml else _mini_yaml(text)


def _name(link):
    while isinstance(link, list) and link:  # unquoted [[x]] parses as a nested list in YAML
        link = link[0]
    m = re.match(r"^\[\[([^\]|#]+)", str(link).strip())
    return (m.group(1) if m else str(link)).strip()


def _list(v):
    return v if isinstance(v, list) else ([] if v in (None, "") else [v])


def _date(v):
    if isinstance(v, dt.date):
        return v
    try:
        return dt.date.fromisoformat(str(v)) if v else None
    except ValueError:
        return None


def load(vault):
    goals, errors = [], []
    for p in sorted(glob.glob(os.path.join(vault, "Goals", "*.md"))):
        base = os.path.basename(p)
        text = open(p, encoding="utf-8").read()
        m = FM.match(text)
        if not m:
            errors.append(f"{base}: no frontmatter")
            fm = {}
        else:
            try:
                fm = _parse(m.group(1)) or {}
            except Exception as e:
                errors.append(f"{base}: frontmatter error: {' '.join(str(e).split())[:160]}")
                continue
        if not isinstance(fm, dict):
            errors.append(f"{base}: frontmatter is not a mapping")
            continue
        fm["name"] = base[:-3]
        fm["path"] = p
        fm["parent"] = [_name(x) for x in _list(fm.get("parent")) if x]
        fm["discuss_at"] = [str(x) for x in _list(fm.get("discuss_at")) if x]
        fm["period_start"], fm["period_end"] = _date(fm.get("period_start")), _date(fm.get("period_end"))
        fm["status"] = fm.get("status") or ("Backlog" if not fm.get("horizon") else "Active")
        goals.append(fm)
    return goals, errors


def covers(g, d):
    return bool(g["period_start"] and g["period_end"] and g["period_start"] <= d <= g["period_end"])


def is_open(g, d):
    return g["status"] in OPEN and covers(g, d)


def children(goals, name):
    return [g for g in goals if name in g["parent"]]


def _rank(g):
    return ORDER.index(g["horizon"]) if g.get("horizon") in ORDER else 9


def tree(goals, d):
    show = [g for g in goals if is_open(g, d) or g["status"] == "Backlog"]
    names = {g["name"] for g in show}
    out = []

    def walk(g, depth, seen):
        e = EMOJI.get(g["status"], "")
        extra = ""
        if g["status"] == "Backlog":
            extra = f" — ready when: {g.get('ready_when') or 'room'}; {g.get('shape') or 'Needs shaping'}"
        out.append(f"{'  ' * depth}- {e} {g.get('horizon') or 'Backlog'}: [[{g['name']}]]{extra}")
        for c in sorted(children(show, g["name"]), key=lambda c: (c["status"] == "Backlog", _rank(c), c["name"])):
            if c["name"] not in seen:
                walk(c, depth + 1, seen | {c["name"]})

    roots = [g for g in show if not any(p in names for p in g["parent"])]
    for r in sorted(roots, key=lambda g: (_rank(g), g["name"])):
        walk(r, 0, {r["name"]})
    return "\n".join(out) or "No open goals."


def check(goals, errors, d):
    flags = list(errors)
    names = {g["name"] for g in goals}
    for g in goals:
        h = g.get("horizon")
        if h != "Decade" and not g["parent"]:
            flags.append(f"orphan: [[{g['name']}]] has no parent")
        for p in g["parent"]:
            if p not in names:
                flags.append(f"broken parent: [[{g['name']}]] → [[{p}]] has no note")
        if g["status"] not in OPEN | CLOSED | {"Backlog"}:
            flags.append(f"unknown status '{g['status']}': [[{g['name']}]]")
        if h and h not in ORDER:
            flags.append(f"unknown horizon '{h}': [[{g['name']}]]")
        if h and not (g["period_start"] and g["period_end"]):
            flags.append(f"missing period: [[{g['name']}]]")
        if g["status"] == "Backlog" and h:
            flags.append(f"Backlog goal with a horizon: [[{g['name']}]]")
    for h in ORDER:
        n = sum(1 for g in goals if g.get("horizon") == h and is_open(g, d))
        if n > CAPS[h]:
            flags.append(f"over cap: {n} open {h} goals (max {CAPS[h]})")

    def recent_child(g, horizon, weeks):
        cutoff = d - dt.timedelta(weeks=weeks)
        return any(c.get("horizon") == horizon and c["period_end"] and c["period_end"] >= cutoff
                   for c in children(goals, g["name"]))

    for g in goals:
        if not is_open(g, d):
            continue
        if g.get("horizon") == "Year":
            if not recent_child(g, "Month", 6):
                flags.append(f"stale: Year goal [[{g['name']}]] has no Month child in the last 6 weeks")
            if "TBD" in str(g.get("done_looks_like") or "TBD"):
                flags.append(f"TBD: Year goal [[{g['name']}]] has no measurable done_looks_like")
        if g.get("horizon") == "Month" and not recent_child(g, "Week", 2):
            flags.append(f"stale: Month goal [[{g['name']}]] has no Week child in the last 2 weeks")
    return "\n".join(flags) or "No flags."


def latest_weekly_review(vault):
    notes = sorted(glob.glob(os.path.join(vault, "Goals", "Reviews", "Week of *.md")))
    return os.path.basename(notes[-1])[:-3] if notes else None


def week(goals, d, vault):
    rows = [g for g in goals if g.get("horizon") == "Week" and is_open(g, d)]
    if not rows:
        last = latest_weekly_review(vault)
        return "No week goals set — run /goals review week" + (f" (latest draft: [[{last}]])" if last else "")
    return "\n".join(f"{EMOJI.get(g['status'], '')} [[{g['name']}]]" + "".join(f" (→ [[{p}]])" for p in g["parent"])
                     for g in sorted(rows, key=lambda g: g["name"]))


def meetings(goals, d):
    idx = defaultdict(list)
    for g in goals:
        if g["status"] == "Backlog" or is_open(g, d):
            for m in g["discuss_at"]:
                idx[m].append({k: g.get(k) for k in ("name", "status", "shape", "ready_when", "parent", "path")})
    return json.dumps(idx, ensure_ascii=False, indent=1, default=str)


def today():
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("Europe/Brussels")).date()
    except Exception:
        return dt.date.today()


def main(argv):
    if argv[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return
    if len(argv) < 2:
        sys.exit(__doc__)
    cmd, vault = argv[0], argv[1]
    if not os.path.isdir(os.path.join(vault, "Goals")):
        sys.exit(f"no Goals/ folder under {vault}")
    d = today()
    if "--date" in argv:
        i = argv.index("--date")
        d = _date(argv[i + 1] if i + 1 < len(argv) else None)
        if d is None:
            sys.exit("--date needs YYYY-MM-DD")
    goals, errors = load(vault)
    if cmd == "tree":
        print(tree(goals, d))
    elif cmd == "check":
        print(check(goals, errors, d))
    elif cmd == "week":
        print(week(goals, d, vault))
    elif cmd == "meetings":
        print(meetings(goals, d))
    elif cmd == "json":
        print(json.dumps(goals, ensure_ascii=False, indent=1, default=str))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
