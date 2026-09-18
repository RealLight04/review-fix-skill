# review-fix

코드 리뷰가 낸 finding들을, 위험도별로 등급을 매겨 그 등급에 맞는 모델(Haiku / Sonnet / Opus)에게
**실제로 위임해서 고치는** [Claude Code](https://claude.com/claude-code) 스킬입니다.

## 왜

리뷰가 찾아낸 문제들은 위험도가 제각각입니다. 죽은 파일 하나 지우는 것과 인증 로직의
엣지케이스를 고치는 걸 같은 모델로 처리하면, 트리비얼한 데 비싼 모델을 쓰거나(낭비)
복잡한 데 싼 모델을 써서 놓칩니다(사고). 이 스킬은 그 판단 기준을 고정해둡니다.

**추천만 하지 않습니다.** Agent 도구의 `model` 파라미터로 실제 그 모델에게 수정을
맡깁니다. 등급 판단·순서·재검증은 오케스트레이션 세션이 하고, 실제 파일 수정은 고른
모델의 서브에이전트가 합니다.

## 비슷한 것과 뭐가 다른가

찾아본 결과, 아래 셋을 하나로 합친 건 없었습니다:

| | 실제 수정 적용 | 위험도별 모델 티어링 | 리뷰 finding에 직접 연결 |
|---|:---:|:---:|:---:|
| 공식 `/code-review --fix` | ✅ | ❌ (모델 하나로 전부) | ✅ |
| 범용 model-routing 플러그인들 | ❌ (보고서만) | ✅ | ❌ (범용 작업용) |
| **review-fix** | ✅ | ✅ | ✅ |

## 등급

| 등급 | 기준 | 예 | 모델 |
|---|---|---|---|
| 사무적 | 기계적 조작, 되돌리기 쉬움 | 죽은 파일 삭제, 미사용 import 제거, 오타 | `haiku` |
| 일반 | 주변 로직 이해가 필요한 통상적 버그 수정 | 조건문 오류, 널 체크 누락 | `sonnet` |
| 고위험 | 잘못되면 되돌리기 어렵거나 파급이 큼 | 인증/결제, 마이그레이션, 아키텍처 변경 | `opus` |

애매하면 위 등급으로 올립니다 — 비용을 아끼려고 등급을 낮추지 않습니다.

## 안전장치

- **검증 안 된 finding은 안 고칩니다.** `PLAUSIBLE`(리뷰가 확신 못 한) finding은 목록만
  보여주고 손대지 않습니다.
- **자기보고를 안 믿습니다.** 모든 등급에서, 서브에이전트가 "완료"라고 해도 직접
  확인합니다(파일 존재 여부, git status, 필요하면 테스트 실행).
- **실패하면 조용히 넘어가지 않습니다.** 재시도 → 상위 등급으로 재시도 → 그래도 안 되면
  사용자에게 그대로 보고, 3단계로 정해져 있습니다.
- **커밋·푸시를 하지 않습니다.** 사용자가 명시적으로 요청하기 전까지.

## 설치

**권장 (skills CLI):**
```bash
npx skills add RealLight04/review-fix-skill
```

**수동 (macOS/Linux):**
```bash
git clone https://github.com/RealLight04/review-fix-skill.git ~/.claude/skills/review-fix
```

**수동 (Windows PowerShell):**
```powershell
git clone https://github.com/RealLight04/review-fix-skill.git `
  "$env:USERPROFILE\.claude\skills\review-fix"
```

## 사용

먼저 코드 리뷰를 돌립니다(`/code-review`, 또는 리뷰 결과를 만들어내는 다른 스킬).
그다음:

```
/review-fix
```

인자 없이 부르면 대화의 가장 최근 리뷰 결과를 대상으로 씁니다. finding을 직접
붙여넣어도 됩니다:

```
/review-fix app/alerts.py:42 — dispatch()가 커밋 전 예외를 삼켜 중복 발송 가능
```

자세한 동작은 [SKILL.md](SKILL.md)에 전부 있습니다 — 이 스킬 자체가 Claude에게 주는
지시문이라, 읽어보면 정확히 뭘 하는지 그대로 보입니다.

## 라이선스

[MIT](LICENSE)
