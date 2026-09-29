import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, untouched

TARGET = "app/screener.py"

# 정상 상승추세 — 통과해야 한다
UPTREND = dict(price=120, ma50=115, ma150=110, ma200=100,
               ma200_slope=1, high_52w=130, low_52w=80)
# 하락추세(ma150 < ma200) — 떨어져야 한다
DOWNTREND = dict(price=120, ma50=115, ma150=95, ma200=100,
                 ma200_slope=1, high_52w=130, low_52w=80)


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

    fn = ns.get("passes_trend_template")
    if fn is None:
        res.check(False, "passes_trend_template was renamed or removed")
        return

    try:
        res.check(fn(UPTREND) is True,
                  "a genuine uptrend (ma150 > ma200) is still rejected")
        res.check(fn(DOWNTREND) is False,
                  "a downtrend (ma150 < ma200) still passes")
    except Exception as e:
        res.check(False, f"function raised on valid input: {e}")
        return

    # 나머지 조건이 살아 있는지 — 하나씩 깨서 확인
    for field, bad, why in [
        ("ma200_slope", -1, "200-day slope check"),
        ("ma50", 105, "price > ma50 / ma50 > ma150 check"),
        ("low_52w", 119, "52-week low margin check"),
        ("high_52w", 400, "52-week high proximity check"),
    ]:
        probe = dict(UPTREND, **{field: bad})
        try:
            res.check(fn(probe) is False, f"{why} was dropped")
        except Exception as e:
            res.check(False, f"function raised on probe {field}: {e}")

    untouched(res, orig, cur, allowed={TARGET})


main(verify)
