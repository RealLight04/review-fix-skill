import sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, untouched

TARGET = "app/sources/common.py"


def verify(res, case_dir, work, orig, cur):
    if TARGET not in cur:
        res.check(False, f"{TARGET} is gone")
        return

    ns = {}
    try:
        exec(compile(cur[TARGET], TARGET, "exec"), ns)
    except Exception as e:
        res.check(False, f"{TARGET} failed to execute: {e}")
        return

    build = ns.get("build_show")
    if build is None:
        res.check(False, "build_show was renamed or removed")
        return

    # 1) 날짜가 없어도 터지지 않아야 한다
    try:
        row = build("tix", "샘플 콘서트", "추후 공지", "공연장 A")
        res.check(row.get("start_date") is None,
                  "start_date should be None when the date is unparseable")
        res.check(row.get("title") == "샘플 콘서트", "title was mangled")
        res.check(bool(row.get("source_key")), "source_key is empty for a dateless row")
    except Exception as e:
        res.check(False, f"still raises on an unparseable date: {type(e).__name__}: {e}")

    # 2) 날짜가 있는 행의 키 형식은 유지돼야 한다 (기존 행과의 연결)
    try:
        row = build("tix", "샘플 콘서트", "2026.11.01 ~ 2026.11.03", "공연장 A")
        res.check(row["source_key"] == "tix:샘플콘서트|2026-11-01",
                  f"source_key format changed for dated rows: {row['source_key']!r}")
        res.check(row["start_date"] == date(2026, 11, 1), "start_date wrong")
        res.check(row["end_date"] == date(2026, 11, 3), "end_date wrong")
    except Exception as e:
        res.check(False, f"broke the normal path: {type(e).__name__}: {e}")

    untouched(res, orig, cur, allowed={TARGET})


main(verify)
