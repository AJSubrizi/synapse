#!/usr/bin/env python3
"""Skill scorecards — the reputation layer that makes the vault a *skills library*.

Each skill is a Markdown file with a scorecard in its frontmatter:

    uses: 0          # times the skill was applied (agent bumps this)
    score: 0.0       # running average quality vote, 1-5 (human or agent)
    votes: 0         # number of quality votes (for the running average)
    last_used: '-'   # ISO date of the last use

Usage (normally via `brain skill ...`):
    skill.py use  <name>                  # +1 use, set last_used = today
    skill.py rate <name> <1-5> [note...]  # add a quality vote
    skill.py list                         # the library, ranked by score then uses
    skill.py show <name>                  # one skill's scorecard + recent notes

Skills are resolved from $BRAIN_SKILLS_DIR (default: ../skills next to this file).
Every change is also appended to <skills>/_ratings.log for provenance.
"""
from __future__ import annotations

import datetime as dt
import fcntl
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.environ.get("BRAIN_SKILLS_DIR") or os.path.join(os.path.dirname(HERE), "skills")
LOG = os.path.join(SKILLS_DIR, "_ratings.log")
SCORE_KEYS = ("uses", "score", "votes", "last_used")


def today() -> str:
    return dt.date.today().isoformat()


def resolve(name: str) -> str | None:
    for cand in (
        os.path.join(SKILLS_DIR, f"{name}.md"),
        os.path.join(SKILLS_DIR, name, "SKILL.md"),
        os.path.join(SKILLS_DIR, name, f"{name}.md"),
    ):
        if os.path.isfile(cand):
            return cand
    return None


def split_fm(text: str) -> tuple[list[str], str]:
    """Return (frontmatter_lines, rest). Empty list if no frontmatter."""
    if not text.startswith("---"):
        return [], text
    end = text.find("\n---", 3)
    if end == -1:
        return [], text
    fm = text[3:end].lstrip("\n").splitlines()
    rest = text[end + 4:]
    return fm, rest


def get(fm: list[str], key: str) -> str | None:
    for line in fm:
        m = re.match(rf"{key}\s*:\s*(.*)$", line)
        if m:
            return m.group(1).strip().strip("'\"")
    return None


def requires_of(fm: list[str]) -> list[str]:
    """Skill dependencies declared as `requires: [[a]], [[b]]` (or a bare list)."""
    raw = get(fm, "requires")
    if not raw:
        return []
    deps = re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", raw)
    if not deps:
        deps = [t.strip() for t in raw.strip("[] ").split(",") if t.strip()]
    return [d.split("/")[-1].strip() for d in deps]


def card(fm: list[str]) -> dict[str, float]:
    return {
        "uses": int(float(get(fm, "uses") or 0)),
        "score": float(get(fm, "score") or 0),
        "votes": int(float(get(fm, "votes") or 0)),
    }


def set_keys(path: str, updates: dict[str, str]) -> None:
    text = open(path, encoding="utf-8").read()
    fm, rest = split_fm(text)
    if not fm:
        print(f"skill: {os.path.relpath(path, SKILLS_DIR)} has no frontmatter", file=sys.stderr)
        sys.exit(1)
    seen = set()
    for i, line in enumerate(fm):
        m = re.match(r"(\w+)\s*:", line)
        if m and m.group(1) in updates:
            fm[i] = f"{m.group(1)}: {updates[m.group(1)]}"
            seen.add(m.group(1))
    for k, v in updates.items():
        if k not in seen:
            fm.append(f"{k}: {v}")
    open(path, "w", encoding="utf-8").write("---\n" + "\n".join(fm) + "\n---\n" + rest)


def logline(action: str, name: str, value: str, note: str) -> None:
    os.makedirs(SKILLS_DIR, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(LOG, "a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)  # Lock to prevent concurrent writes
        f.write(f"[{stamp}] {action} {name} value={value} note={note!r}\n")
        fcntl.flock(f, fcntl.LOCK_UN)  # Unlock


def cmd_use(name: str) -> int:
    path = resolve(name)
    if not path:
        print(f"skill: not found: {name}", file=sys.stderr)
        return 1
    c = card(split_fm(open(path, encoding="utf-8").read())[0])
    uses = c["uses"] + 1
    set_keys(path, {"uses": str(uses), "last_used": today()})
    logline("use", name, str(uses), "")
    print(f"{name}: uses -> {uses}")
    return 0


def cmd_rate(name: str, raw: str, note: str) -> int:
    path = resolve(name)
    if not path:
        print(f"skill: not found: {name}", file=sys.stderr)
        return 1
    try:
        v = float(raw)
    except ValueError:
        print("skill: rating must be a number 1-5", file=sys.stderr)
        return 2
    if not 1 <= v <= 5:
        print("skill: rating must be between 1 and 5", file=sys.stderr)
        return 2
    c = card(split_fm(open(path, encoding="utf-8").read())[0])
    votes = c["votes"] + 1
    score = round((c["score"] * c["votes"] + v) / votes, 2)
    set_keys(path, {"score": str(score), "votes": str(votes)})
    logline("rate", name, str(v), note)
    print(f"{name}: score -> {score} ({votes} votes)")
    return 0


def all_skills() -> list[str]:
    paths = set(glob.glob(os.path.join(SKILLS_DIR, "*.md")))
    paths |= set(glob.glob(os.path.join(SKILLS_DIR, "*", "*.md")))
    out = []
    for p in paths:
        if os.path.basename(p).startswith("_"):
            continue
        out.append(p)
    return out


def cmd_list() -> int:
    rows = []
    for p in all_skills():
        fm, _ = split_fm(open(p, encoding="utf-8").read())
        if not fm:
            continue
        name = get(fm, "title") or os.path.splitext(os.path.basename(p))[0]
        c = card(fm)
        rows.append((c["score"], int(c["uses"]), int(c["votes"]), get(fm, "last_used") or "-", name))
    rows.sort(key=lambda r: (r[0], r[1]), reverse=True)
    print(f"{'score':>5}  {'uses':>4}  {'votes':>5}  {'last_used':<10}  skill")
    for score, uses, votes, last, name in rows:
        s = f"{score:.2f}" if votes else "  -"
        print(f"{s:>5}  {uses:>4}  {votes:>5}  {last:<10}  {name}")
    if not rows:
        print("  (no skills with scorecards yet)")
    return 0


def cmd_show(name: str) -> int:
    path = resolve(name)
    if not path:
        print(f"skill: not found: {name}", file=sys.stderr)
        return 1
    fm, _ = split_fm(open(path, encoding="utf-8").read())
    c = card(fm)
    print(f"skill:     {name}")
    print(f"file:      {os.path.relpath(path, SKILLS_DIR)}")
    print(f"version:   {get(fm, 'version') or '1'}")
    print(f"score:     {c['score']:.2f} ({int(c['votes'])} votes)" if c["votes"] else "score:     - (no votes)")
    print(f"uses:      {int(c['uses'])}")
    print(f"last_used: {get(fm, 'last_used') or '-'}")
    deps = requires_of(fm)
    if deps:
        print("requires:")
        for dep in deps:
            mark = "ok " if resolve(dep) else "MISS"
            print(f"  [{mark}] {dep}")
    if os.path.isfile(LOG):
        hist = [ln for ln in open(LOG, encoding="utf-8") if f" {name} " in ln][-5:]
        if hist:
            print("recent:")
            for ln in hist:
                print("  " + ln.rstrip())
    return 0


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) >= 3}


def cmd_suggest(query: str, limit: int = 5) -> int:
    """Recommend skills for a context/query: relevance (title/tags/summary overlap)
    nudged by reputation (score, uses). Pure ranking — picks among existing skills."""
    q = _tokens(query)
    if not q:
        print("usage: skill.py suggest <context words>", file=sys.stderr)
        return 2
    rows = []
    for p in all_skills():
        fm, _ = split_fm(open(p, encoding="utf-8").read())
        if not fm:
            continue
        name = get(fm, "title") or os.path.splitext(os.path.basename(p))[0]
        hay = _tokens(" ".join(filter(None, [
            get(fm, "title"), get(fm, "tags"), get(fm, "summary")])))
        overlap = len(q & hay)
        if not overlap:
            continue
        c = card(fm)
        rank = overlap + 0.1 * c["score"] + 0.01 * c["uses"]
        rows.append((rank, overlap, c["score"], int(c["uses"]), name,
                     get(fm, "summary") or ""))
    rows.sort(reverse=True)
    if not rows:
        print(f"no skill matches: {query}")
        return 0
    for rank, overlap, score, uses, name, summary in rows[:limit]:
        s = f"{score:.1f}" if score else "-"
        print(f"  {name}  (match {overlap}, score {s}, uses {uses})")
        if summary:
            print(f"      {summary}")
    return 0


def cmd_deps() -> int:
    """Report the dependency graph and flag broken `requires` links across all skills."""
    broken = 0
    for p in all_skills():
        fm, _ = split_fm(open(p, encoding="utf-8").read())
        name = get(fm, "title") or os.path.splitext(os.path.basename(p))[0]
        deps = requires_of(fm)
        if not deps:
            continue
        for dep in deps:
            if resolve(dep):
                print(f"  {name} -> {dep}")
            else:
                print(f"  {name} -> {dep}   [MISSING]")
                broken += 1
    if broken:
        print(f"\n{broken} broken dependency link(s)", file=sys.stderr)
    return 1 if broken else 0


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 0
    sub, rest = args[0], args[1:]
    if sub == "use" and rest:
        return cmd_use(rest[0])
    if sub == "rate" and len(rest) >= 2:
        return cmd_rate(rest[0], rest[1], " ".join(rest[2:]))
    if sub == "list":
        return cmd_list()
    if sub == "show" and rest:
        return cmd_show(rest[0])
    if sub == "suggest" and rest:
        return cmd_suggest(" ".join(rest))
    if sub == "deps":
        return cmd_deps()
    print("usage: skill.py use|rate|list|show|suggest|deps ...", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
