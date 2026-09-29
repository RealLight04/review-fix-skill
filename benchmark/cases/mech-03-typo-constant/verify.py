import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, untouched

TARGET = "app/messages.py"


def verify(res, case_dir, work, orig, cur):
    if TARGET not in cur:
        res.check(False, f"{TARGET} is gone")
        return
    src = cur[TARGET]

    res.check("완료되었습니가" not in src, "typo `완료되었습니가` still present")
    res.check("구독이 완료되었습니다." in src, "corrected string not found")
    # 뒷문장까지 갈아엎지 않았는지
    res.check("새 공연이 올라오면 바로 알려드립니다." in src,
              "rewrote the rest of SUBSCRIBE_OK instead of fixing the typo")
    # 나머지 상수는 손대지 말 것
    for name, text in [
        ("SUBSCRIBE_PROMPT", "알림 받을 이메일 주소를 입력하세요."),
        ("SUBSCRIBE_DUP", "이미 구독 중인 주소입니다."),
        ("SUBSCRIBE_LIMIT", "구독자 수가 한도에 도달했습니다. 잠시 후 다시 시도해주세요."),
        ("UNSUBSCRIBE_OK", "구독이 해지되었습니다."),
    ]:
        res.check(text in src, f"{name} was altered")

    untouched(res, orig, cur, allowed={TARGET})


main(verify)
