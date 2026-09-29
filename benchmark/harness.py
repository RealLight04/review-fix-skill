"""Shared helpers for benchmark case verifiers.

Each case ships a pristine `files/` directory (the starting state) and a
`verify.py`. A run copies `files/` to a scratch workdir, lets one model fix the
finding there, then runs `verify.py <workdir>`.

A verifier answers two questions, and both matter:

  1. Did the intended fix land?
  2. Did anything ELSE change?

Question 2 is half the point. A model that fixes the bug and also "helpfully"
reformats three other files has not done the job — the skill under test tells
subagents to fix one finding only, so scope creep is a failure, not a bonus.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

# Written by `run.py prepare` so it can tell its own workdirs from anything else.
# Never counts as a file the model added.
SENTINEL = ".review-fix-bench"


class Result:
    def __init__(self) -> None:
        self.problems: list[str] = []

    def check(self, ok: bool, msg: str) -> None:
        if not ok:
            self.problems.append(msg)

    def finish(self) -> None:
        if self.problems:
            for p in self.problems:
                print(f"FAIL: {p}")
            sys.exit(1)
        print("PASS")
        sys.exit(0)


def read_tree(root: Path) -> dict[str, str]:
    """{relative path: text} for every file under root. Missing root → {}."""
    out: dict[str, str] = {}
    if not root.exists():
        return out
    for f in sorted(root.rglob("*")):
        if f.is_file() and f.name != SENTINEL and "__pycache__" not in f.parts:
            rel = f.relative_to(root).as_posix()
            try:
                out[rel] = f.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                out[rel] = "<binary>"
    return out


def paths(case_dir: Path, work: Path) -> tuple[dict[str, str], dict[str, str]]:
    """(original, current) as {relative path: text}. Missing files are absent."""
    return read_tree(case_dir / "files"), read_tree(work)


def untouched(res: Result, orig: dict[str, str], cur: dict[str, str],
              allowed: set[str]) -> None:
    """Every file outside `allowed` must be byte-identical, present, and no new
    files added. Line endings are normalized so a CRLF checkout doesn't read as
    scope creep."""
    def norm(s: str) -> str:
        return s.replace("\r\n", "\n")

    for rel, text in orig.items():
        if rel in allowed:
            continue
        if rel not in cur:
            res.check(False, f"deleted a file it was not asked to touch: {rel}")
        elif norm(cur[rel]) != norm(text):
            res.check(False, f"modified a file it was not asked to touch: {rel}")
    for rel in cur:
        if rel not in orig and rel not in allowed:
            res.check(False, f"added an unrequested file: {rel}")


def main(verify) -> None:
    """verify(res, case_dir, work, orig, cur)"""
    # FAIL messages are partly Korean; a piped stdout on a non-UTF-8 locale
    # would otherwise crash the verifier instead of reporting.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    # The code under test logs its own warnings; they are noise next to PASS/FAIL.
    logging.disable(logging.CRITICAL)
    if len(sys.argv) != 2:
        print("usage: verify.py <workdir>")
        sys.exit(2)
    work = Path(sys.argv[1]).resolve()
    case_dir = Path(sys.argv[0]).resolve().parent
    res = Result()
    orig, cur = paths(case_dir, work)
    verify(res, case_dir, work, orig, cur)
    res.finish()
