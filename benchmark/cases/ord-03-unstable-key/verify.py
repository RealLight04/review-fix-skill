import sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, untouched

TARGET = "app/dedupe.py"


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

    fn = ns.get("batch_keys")
    if fn is None:
        res.check(False, "batch_keys was renamed or removed")
        return

    # 1) 제목이 같고 날짜가 없는 5건 — 키가 전부 달라야 한다
    try:
        dateless = [{"title": "샘플 콘서트", "start_date": None} for _ in range(5)]
        keys = fn("tix", dateless)
        res.check(len(set(keys)) == 5,
                  f"dateless rows still collide: {len(set(keys))} unique of 5")
    except Exception as e:
        res.check(False, f"raised on dateless rows: {type(e).__name__}: {e}")

    # 2) 날짜가 있는 행의 키 형식은 그대로 — 기존 저장 행과 이어져야 한다
    try:
        dated = [{"title": "샘플 콘서트", "start_date": date(2026, 11, 1)}]
        got = fn("tix", dated)[0]
        res.check(got == "tix:샘플콘서트|2026-11-01",
                  f"changed the key format for dated rows: {got!r}")
    except Exception as e:
        res.check(False, f"broke the dated path: {type(e).__name__}: {e}")

    # 3) 같은 입력이면 같은 키 — 실행마다 달라지면 매번 '새 공연'이 된다
    try:
        rows = [{"title": "같은 공연", "start_date": None},
                {"title": "다른 공연", "start_date": None}]
        res.check(fn("tix", rows) == fn("tix", rows),
                  "keys are not stable across calls (random/uuid/timestamp used?)")
    except Exception as e:
        res.check(False, f"raised on stability probe: {type(e).__name__}: {e}")

    untouched(res, orig, cur, allowed={TARGET})


main(verify)
