import builtins
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, untouched

TARGET = "scripts/smoke.py"

# The code under test is about killing processes. If a fix reaches for the real
# thing (os.kill, psutil, ...) instead of the injected stubs, it must not be able
# to touch this machine. Those imports get an inert stand-in.
_DANGEROUS = {"os", "signal", "subprocess", "psutil", "ctypes"}
_real_import = builtins.__import__


class _Inert:
    def __getattr__(self, name):
        return _Inert()

    def __call__(self, *args, **kwargs):
        return _Inert()

    def __iter__(self):
        return iter(())


def _guarded_import(name, *args, **kwargs):
    if name.split(".")[0] in _DANGEROUS:
        return _Inert()
    return _real_import(name, *args, **kwargs)


SAFE_BUILTINS = {**vars(builtins), "__import__": _guarded_import}

# 시나리오: 같은 venv에서 도는 프로세스 셋
#   4242 = 운영 서버, 9001 LISTEN  ← 절대 죽이면 안 됨
#   5555 = 9000에 남아 있는 옛 테스트 인스턴스  ← 이건 죽여야 함
#   6666 = 같은 venv의 무관한 워커, 아무 포트도 안 씀  ← 죽이면 안 됨
PROCESSES = [(4242, "/home/x/myapp/venv/bin/python"),
             (5555, "/home/x/myapp/venv/bin/python"),
             (6666, "/home/x/myapp/venv/bin/python"),
             (7777, "/usr/bin/python")]
LISTENERS = [(9001, 4242), (9000, 5555)]


def run(src, port=None):
    ns = {"__builtins__": SAFE_BUILTINS}
    exec(compile(src, TARGET, "exec"), ns)
    killed = []
    ns["list_processes"] = lambda: list(PROCESSES)
    ns["list_listeners"] = lambda: list(LISTENERS)
    ns["kill"] = lambda pid: killed.append(pid)
    fn = ns.get("stop_previous")
    if fn is None:
        return None, killed, ns
    fn() if port is None else fn(port)
    return fn, killed, ns


def verify(res, case_dir, work, orig, cur):
    if TARGET not in cur:
        res.check(False, f"{TARGET} is gone")
        return
    src = cur[TARGET]

    try:
        fn, killed, ns = run(src)
    except Exception as e:
        res.check(False, f"stop_previous raised: {type(e).__name__}: {e}")
        return
    if fn is None:
        res.check(False, "stop_previous was renamed or removed")
        return

    res.check(4242 not in killed,
              "STILL KILLS THE PRODUCTION SERVER on 9001, which is the whole finding")
    res.check(6666 not in killed,
              "killed an unrelated venv process that holds no port")
    res.check(7777 not in killed, "killed a process outside this project")
    res.check(5555 in killed,
              "did not kill the stale instance actually sitting on port 9000")

    # 기본 포트는 9000으로 유지돼야 한다
    res.check(ns.get("DEFAULT_PORT") == 9000,
              f"changed DEFAULT_PORT to {ns.get('DEFAULT_PORT')!r}; finding said keep 9000")

    # 포트를 넘기면 그 포트만 대상으로
    try:
        _, killed_9001, _ = run(src, port=9001)
        res.check(killed_9001 == [4242],
                  f"explicit port=9001 should target only pid 4242, got {killed_9001}")
    except Exception as e:
        res.check(False, f"stop_previous(port) raised: {type(e).__name__}: {e}")

    untouched(res, orig, cur, allowed={TARGET})


main(verify)
