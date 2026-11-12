#!/usr/bin/env python3
"""Surgical read-modify-write for vault notes: the file is re-read on every call.

  note.py show    FILE [HEADING]                       print the note, or one section's body
  note.py replace FILE HEADING < body                  replace a section's body (creates it at the end)
  note.py append  FILE HEADING < lines                 append lines to a section (creates it at the end)
  note.py tag     FILE TAG                             add TAG to the frontmatter `tags:` block list
  note.py create  FILE TAG [TAG...] [--set KEY=VALUE]  create a note whose frontmatter holds the KEY=VALUE
                                                       pairs then the tags (no-op if the file exists)

HEADING is the full heading line, e.g. "## Open" or "### Scorecard". A section runs
until the next heading of the same or higher level (headings inside ``` fences don't
count). Everything else is left byte-for-byte.
"""
import os, re, sys


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    tmp = path + ".tmp-claude"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def level(line):
    m = re.match(r"^(#{1,6}) ", line)
    return len(m.group(1)) if m else 0


def headings(lines):
    """Yield (index, level) for real headings: outside frontmatter and code fences."""
    in_fm = bool(lines) and lines[0].rstrip("\r\n") == "---"
    fence = False
    for i, line in enumerate(lines):
        bare = line.rstrip("\r\n")
        if in_fm:
            if i > 0 and bare == "---":
                in_fm = False
            continue
        if bare.lstrip().startswith("```"):
            fence = not fence
            continue
        if not fence and level(line):
            yield i, level(line)


def find(lines, heading):
    """Return (start, end) line indexes of the section body, or None."""
    lvl = level(heading)
    hs = list(headings(lines))
    for k, (i, l) in enumerate(hs):
        if lines[i].rstrip("\r\n").rstrip() == heading.strip():
            end = next((j for j, lj in hs[k + 1:] if lj <= lvl), len(lines))
            return i + 1, end
    return None


def set_section(path, heading, body, mode):
    lines = read(path).splitlines(keepends=True)
    body = body if body.endswith("\n") else body + "\n"
    span = find(lines, heading)
    if span is None:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines += ["\n", heading.strip() + "\n", "\n", body]
    else:
        s, e = span
        old = lines[s:e]
        # keep the blank lines that separate this section from the next one
        tail = []
        while old and old[-1].strip() == "":
            tail.insert(0, old.pop())
        new = ["\n", body] if mode == "replace" else old + [body]
        if e < len(lines):
            new += tail or ["\n"]
        lines[s:e] = new
    write(path, "".join(lines))


def add_tag(path, tag):
    text = read(path)
    m = re.match(r"^---\n(.*?\n)---\n", text, re.S)
    if not m:
        write(path, f"---\ntags:\n  - {tag}\n---\n" + text)
        return
    fm = m.group(1)
    if re.search(rf"^\s+- {re.escape(tag)}\s*$", fm, re.M):
        return
    if re.search(r"^tags:\s*$", fm, re.M):
        fm = re.sub(r"^(tags:\s*\n(?:\s+- .*\n)*)", lambda k: k.group(1) + f"  - {tag}\n", fm, count=1, flags=re.M)
    else:
        fm += f"tags:\n  - {tag}\n"
    write(path, "---\n" + fm + "---\n" + text[m.end():])


def create(path, args):
    if os.path.exists(path):
        return
    tags, sets, i = [], [], 0
    while i < len(args):
        if args[i] == "--set":
            k, _, v = args[i + 1].partition("=")
            sets.append(f"{k}: {v}\n")
            i += 2
        else:
            tags.append(args[i])
            i += 1
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    write(path, "---\n" + "".join(sets) + "tags:\n" + "".join(f"  - {t}\n" for t in tags) + "---\n")


def main(argv):
    if argv[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return
    if len(argv) < 2:
        sys.exit(__doc__)
    cmd, path, *rest = argv
    if cmd == "show":
        lines = read(path).splitlines(keepends=True)
        if rest:
            span = find(lines, rest[0])
            if span is None:
                sys.exit(f"no section {rest[0]!r} in {path}")
            sys.stdout.write("".join(lines[span[0]:span[1]]))
        else:
            sys.stdout.write("".join(lines))
    elif cmd in ("replace", "append") and rest:
        set_section(path, rest[0], sys.stdin.read(), cmd)
    elif cmd == "tag" and rest:
        add_tag(path, rest[0])
    elif cmd == "create":
        create(path, rest)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
