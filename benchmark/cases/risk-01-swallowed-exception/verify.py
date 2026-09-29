import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, untouched

TARGET = "app/alerts.py"


class Row:
    def __init__(self, rid, body, alerted):
        self.id = rid
        self.body = body
        self.alerted = alerted


class DB:
    """A session over a tiny store that only changes on a successful commit.

    Each dispatch cycle is a fresh process: it calls query() and gets rows built
    from what was actually committed. That is the whole point of the finding. An
    in-memory `row.alerted = True` that never reached disk is gone by the next
    run, so the next run sends the same alert again.
    """

    def __init__(self, fail_times=0):
        self.fail_times = fail_times
        self.stored = {}   # id -> (body, alerted), i.e. what is on disk
        self.loaded = []

    def insert(self, rid, body):
        self.stored[rid] = (body, False)

    def query(self):
        self.loaded = [Row(rid, body, alerted) for rid, (body, alerted) in self.stored.items()]
        return self.loaded

    def commit(self):
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError("database is locked")
        for r in self.loaded:
            self.stored[r.id] = (r.body, r.alerted)

    def rollback(self):
        for r in self.loaded:
            r.alerted = self.stored[r.id][1]

    def is_alerted(self, rid):
        return self.stored[rid][1]


def cycle(dispatch, db, send):
    """One scheduled run. Raising is an acceptable way for dispatch to fail."""
    try:
        return dispatch(db, db.query(), send)
    except Exception:
        return None


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

    dispatch = ns.get("dispatch")
    if dispatch is None:
        res.check(False, "dispatch was renamed or removed")
        return

    # 1) 정상 경로: 한 건 보내고, 저장소에도 보냈다고 남는다
    try:
        db = DB()
        db.insert(1, "새 공연 등재")
        delivered = []
        n = dispatch(db, db.query(), delivered.append)
        res.check(n == 1, f"normal path returned {n}, expected 1")
        res.check(delivered == ["새 공연 등재"], f"normal path delivered {delivered}")
        res.check(db.is_alerted(1), "normal path did not persist alerted=True")
    except Exception as e:
        res.check(False, f"broke the normal path: {type(e).__name__}: {e}")
        return

    # 2) 핵심: 커밋이 한 번 실패해도 다음 주기에 같은 알림이 또 나가면 안 된다
    db = DB(fail_times=1)
    db.insert(1, "새 공연 등재")
    delivered = []
    cycle(dispatch, db, delivered.append)
    cycle(dispatch, db, delivered.append)
    res.check(len(delivered) <= 1,
              f"the same alert went out {len(delivered)} times after a failed commit")
    res.check(len(delivered) >= 1,
              "the alert was never delivered once the database recovered")

    # 3) 발송 자체가 실패했다면 저장소에 보냈다고 남으면 안 된다
    db = DB()
    db.insert(1, "발송 실패할 건")

    def boom(body):
        raise RuntimeError("telegram 502")

    cycle(dispatch, db, boom)
    res.check(not db.is_alerted(1),
              "persisted alerted=True even though sending raised")

    untouched(res, orig, cur, allowed={TARGET})


main(verify)
