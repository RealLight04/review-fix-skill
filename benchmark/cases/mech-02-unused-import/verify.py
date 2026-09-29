import ast
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, untouched

TARGET = "app/collector.py"


def verify(res, case_dir, work, orig, cur):
    if TARGET not in cur:
        res.check(False, f"{TARGET} is gone")
        return
    src = cur[TARGET]

    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        res.check(False, f"{TARGET} no longer parses: {e}")
        return

    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.asname or a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.update(a.asname or a.name for a in node.names)

    res.check("json" not in imported, "unused import `json` still present")
    res.check("timedelta" not in imported, "unused import `timedelta` still present")
    # 실제로 쓰이는 것은 남아 있어야 한다 — 과잉 삭제 방지
    for keep in ("logging", "date", "datetime"):
        res.check(keep in imported, f"removed `{keep}`, which is actually used")

    # 로직은 그대로여야 한다
    for marker in ("def collect(", "except Exception", "log.warning", "continue"):
        res.check(marker in src, f"logic changed: `{marker}` missing")

    untouched(res, orig, cur, allowed={TARGET})


main(verify)
