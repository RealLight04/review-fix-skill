import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, untouched

MODELS = "app/models.py"
DB = "app/database.py"


def verify(res, case_dir, work, orig, cur):
    for f in (MODELS, DB):
        if f not in cur:
            res.check(False, f"{f} is gone")
            return

    # ① models.py에 컬럼이 추가됐는가
    m = cur[MODELS]
    res.check(re.search(r"poster_url\s*=\s*Column\(", m) is not None,
              "poster_url column not added to models.py")

    # ② database.py의 MIGRATIONS에도 같이 들어갔는가 — 이게 짝 규칙의 핵심
    d = cur[DB]
    ns = {}
    try:
        # sqlite3 import만 있으므로 그대로 실행 가능
        exec(compile(d, DB, "exec"), ns)
    except Exception as e:
        res.check(False, f"{DB} failed to execute: {e}")
        return
    migrations = ns.get("MIGRATIONS", {})
    shows = migrations.get("shows", {})
    res.check("poster_url" in shows,
              "poster_url missing from MIGRATIONS['shows'] — "
              "CLAUDE.md requires both files to change together")

    # 기존 마이그레이션 항목을 지우지 않았는가
    for keep in ("venue", "start_date", "is_upcoming"):
        res.check(keep in shows, f"removed existing migration entry `{keep}`")

    # 기존 모델 컬럼이 살아 있는가
    for keep in ("source_key", "title", "start_date", "is_upcoming"):
        res.check(re.search(rf"\b{keep}\s*=\s*Column\(", m) is not None,
                  f"removed existing model column `{keep}`")

    # CLAUDE.md는 읽으라고 준 것이지 고치라고 준 게 아니다
    untouched(res, orig, cur, allowed={MODELS, DB})


main(verify)
