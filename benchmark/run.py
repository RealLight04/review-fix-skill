"""Benchmark runner. Python 3.8+, standard library only.

    python benchmark/run.py prepare <case> [workdir]   # copy the starting files
    python benchmark/run.py show    <case>             # print the finding to hand over
    python benchmark/run.py verify  <case> <workdir>   # judge the result
    python benchmark/run.py selftest                   # sanity-check every case

`prepare` never deletes a folder it did not create. Without a workdir it makes a
fresh temporary one. An existing workdir must be empty, or one that an earlier
`prepare` created (it carries a marker file).

`selftest` is the one to run after adding or editing a case. For every case it
checks that the verifier FAILS on the untouched starting state (a verifier that
passes before anything is fixed checks nothing) and PASSES on the case's
reference fix (a verifier that rejects a correct fix measures nothing either).

The fix step itself is not scripted: the point is to measure Claude Code
sessions and subagents at a given model tier. See README.md in this directory.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES = ROOT / "cases"
sys.path.insert(0, str(ROOT))
from harness import SENTINEL  # noqa: E402

TIERS = ("mechanical", "ordinary", "high-risk")
CHILD_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}


def case_dir(name: str) -> Path:
    d = CASES / name
    if not d.is_dir():
        sys.exit(f"no such case: {name}")
    return d


def prepare(name: str, workdir: str | None = None) -> int:
    src = case_dir(name) / "files"
    if workdir is None:
        # Case names start with the expected tier (mech-/ord-/risk-). Keep them out of
        # anything the session under test can see, including its own working path.
        dst = Path(tempfile.mkdtemp(prefix="review-fix-bench-"))
    else:
        dst = Path(workdir).resolve()
        if dst.exists() and not dst.is_dir():
            sys.exit(f"refusing: {dst} exists and is not a directory")
        if dst.is_dir() and any(dst.iterdir()):
            if not (dst / SENTINEL).is_file():
                sys.exit(f"refusing: {dst} is not empty and was not made by `prepare`. "
                         "Pass an empty or new directory, or omit it for a temp one.")
            shutil.rmtree(dst)
    shutil.copytree(src, dst, dirs_exist_ok=True)
    (dst / SENTINEL).write_text("prepared by benchmark/run.py\n", encoding="utf-8")
    print(f"prepared {name} -> {dst}")
    return 0


def show(name: str) -> int:
    print((case_dir(name) / "finding.md").read_text(encoding="utf-8"))
    return 0


def run_verifier(name: str, work: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(case_dir(name) / "verify.py"), str(work)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=CHILD_ENV,
    )


def verify(name: str, workdir: str) -> int:
    proc = run_verifier(name, Path(workdir).resolve())
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    return proc.returncode


def apply_reference(name: str, work: Path) -> None:
    """Overlay reference/ onto work. reference/DELETE lists paths to remove."""
    ref = case_dir(name) / "reference"
    for f in ref.rglob("*"):
        if f.is_file() and f.name != "DELETE":
            target = work / f.relative_to(ref)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, target)
    delete = ref / "DELETE"
    if delete.is_file():
        for line in delete.read_text(encoding="utf-8").splitlines():
            if line.strip():
                (work / line.strip()).unlink()


def last_line(proc: subprocess.CompletedProcess) -> str:
    return (proc.stderr.strip().splitlines() or ["(no stderr)"])[-1]


def check_case(name: str) -> str | None:
    """None if the case is sound, else what is wrong with it."""
    d = case_dir(name)
    try:
        tier = json.loads((d / "expected.json").read_text(encoding="utf-8")).get("tier")
    except (OSError, ValueError) as e:
        return f"expected.json missing or unreadable: {e}"
    if tier not in TIERS:
        return f"expected.json tier {tier!r} is not one of {TIERS}"
    if re.search(r"\btier\b", (d / "finding.md").read_text(encoding="utf-8"), re.I):
        return "finding.md mentions a tier; the expected answer must stay in expected.json"
    if not (d / "reference").is_dir():
        return "no reference/ fix"

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "w"
        shutil.copytree(d / "files", work)
        proc = run_verifier(name, work)
        if proc.returncode == 0:
            return "verifier passes before any fix"
        if "FAIL:" not in proc.stdout:
            # A crash also exits non-zero. Counting it as a proper FAIL would hide a broken case.
            return f"crashed on the starting state instead of reporting FAIL: {last_line(proc)}"

        apply_reference(name, work)
        proc = run_verifier(name, work)
        if proc.returncode != 0:
            why = next((l for l in proc.stdout.splitlines() if l.startswith("FAIL:")),
                       last_line(proc))
            return f"verifier rejects the reference fix: {why}"
    return None


def selftest() -> int:
    names = sorted(p.name for p in CASES.iterdir() if p.is_dir())
    print(f"self-testing {len(names)} cases (FAIL unfixed, PASS on the reference fix)\n")
    bad = []
    for name in names:
        problem = check_case(name)
        if problem:
            bad.append(name)
            print(f"  BROKEN  {name}: {problem}")
        else:
            print(f"  ok      {name}")
    print()
    if bad:
        print(f"{len(bad)} broken case(s): {', '.join(bad)}")
        return 1
    print("all cases fail before a fix and pass on the reference fix")
    return 0


def usage() -> int:
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if args == ["selftest"]:
        raise SystemExit(selftest())
    if len(args) in (2, 3) and args[0] == "prepare":
        raise SystemExit(prepare(*args[1:]))
    if len(args) == 2 and args[0] == "show":
        raise SystemExit(show(args[1]))
    if len(args) == 3 and args[0] == "verify":
        raise SystemExit(verify(args[1], args[2]))
    raise SystemExit(usage())
