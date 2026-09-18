# review-fix

**한 줄짜리 수정에 Opus를 태우지 않기.**

코드 리뷰가 낸 finding을 위험도별로 등급 매겨, 안전하게 처리할 수 있는 가장 싼
모델에게 수정을 맡기는 [Claude Code](https://claude.com/claude-code) 스킬입니다.
기계적인 건 Haiku, 통상적인 버그는 Sonnet, 잘못되면 비싼 건 Opus.

[English README](README.md) · [English SKILL](SKILL.md)

---

## 먼저 알아야 할 것: 이미 갖고 계신 것

Claude Code에는 `/code-review --fix`가 들어 있고, 잘 만들어져 있습니다. 뭘 설치하기
전에 이게 **이미** 하는 걸 아셔야 합니다.

- 리뷰 finding을 작업트리에 바로 적용 (`--fix`)
- severity 등급 부여 (Important / Nit / Pre-existing)
- finding마다 **fixed / skipped / no change needed** 로 결과 보고
- effort 레벨(`low` … `max`)로 커버리지와 확신도를 맞바꿈
- `REVIEW.md`로 저장소마다 severity 정의를 재정의
- `/code-review ultra --fix`로 클라우드 심층 리뷰 후 적용

이걸로 충분하시면 이 스킬은 필요 없습니다. 내장된 걸 쓰세요.

## 이게 더하는 것

`/code-review --fix`가 안 하는 두 가지입니다.

**1. finding마다 다른 모델 등급.** 내장 수정 경로는 모델 하나로 돕니다. 이 스킬은
finding을 등급 매겨 각각 다른 모델에 보냅니다.

| 등급 | 기준 | 모델 |
|---|---|---|
| 사무적 | 기계적이고 되돌리기 쉬움 — 죽은 파일, 미사용 import, 오타 | `haiku` |
| 일반 | 주변 로직 이해가 필요한 통상적 버그 수정 | `sonnet` |
| 고위험 | 인증·결제·마이그레이션·동시성·여러 파일에 걸친 동작 변경 | `opus` |

애매하면 위로 올립니다. 비용 아끼려고 등급을 낮추는 건 금지입니다 — 잘못 고치는
비용이 모델 비용보다 큽니다.

**2. 검증 실패 시 에스컬레이션.** 모든 등급에서 서브에이전트의 자기 보고를 믿지 않고
직접 확인합니다(사무적: 파일이 실제로 바뀌었는지, 일반: 테스트 스크립트 실행,
고위험: diff가 범위를 벗어났는지 직접 읽기). 확인이 틀어지면 같은 등급에서 범위를
좁혀 재시도 → 한 등급 위로 재시도 → 그래도 안 되면 멈추고 보고합니다. 조용한 실패도,
무한 재시도도 없습니다.

`CLAUDE.md`의 짝 규칙("이 파일 고치면 저 파일도")도 읽어서, 짝 중 한쪽만 가리킨
finding이 반쪽만 고쳐진 채 "완료"로 보고되는 걸 막습니다.

## 선행 연구

모델 티어링은 새로운 게 아니고, 이 스킬은 앞선 작업들의 변형입니다.

- **[Aider architect/editor 분리](https://aider.chat/2024/09/26/architect.html)**
  (2024-09) — 강한 모델이 변경을 계획하고 싼 모델이 diff를 씁니다. "한 작업을 모델
  등급으로 쪼갠다"의 원조입니다. 그쪽은 *단계* 기준, 이 스킬은 *위험도* 기준입니다.
- **[AqueGen/model-routing](https://github.com/AqueGen/model-routing)** — Claude Code
  서브에이전트를 작업 유형(scout, implementer, reviewer)으로 라우팅합니다. 여기서
  [RouteLLM (ICLR 2025)](https://arxiv.org/pdf/2406.18665)을 인용하며 *작업유형
  라우팅이 복잡도점수 라우팅보다 낫다*고 하는데, 이건 이 스킬이 택한 방식에 대한
  반대 논거입니다. 고르시기 전에 읽어보실 만합니다.
- **[crissmoldovan/agent-skills](https://github.com/crissmoldovan/agent-skills)** —
  model-routing 스킬을 포함한 28종 팩. 자동 판단이 아니라 프로필 설정 방식입니다.

## 측정되지 않은 것

이 분야에서 아무도 수치를 안 내놓기에, 정직하게 밝힙니다.

- **여기서 티어링이 남는 장사인지.** finding마다 등급을 매기는 데 오케스트레이션
  세션의 토큰이 듭니다. 그 비용을 싼 모델로 아낀 것과 저울질해본 적이 없습니다.
  적은 건수에서는 본전을 못 뽑을 수 있습니다.
- **"사무적" finding에서 Haiku가 Opus만큼 하는지.** 등급 경계는 추론이지 측정이
  아닙니다.

둘 다 다루는 벤치마크가 [`benchmark/`](benchmark/)에 있습니다. 결과가 나오기
전까지 위 등급표는 가설로 봐주세요.

## 설치

```bash
npx skills add RealLight04/review-fix-skill
```

<details>
<summary>수동 설치</summary>

macOS / Linux:
```bash
git clone https://github.com/RealLight04/review-fix-skill.git ~/.claude/skills/review-fix
```

Windows PowerShell:
```powershell
git clone https://github.com/RealLight04/review-fix-skill.git `
  "$env:USERPROFILE\.claude\skills\review-fix"
```
</details>

## 사용

리뷰를 먼저 돌리고:

```
/review-fix
```

인자 없이 부르면 대화의 가장 최근 리뷰 결과를 씁니다. finding을 직접 붙여넣어도
됩니다.

```
/review-fix app/alerts.py:42 — dispatch()가 커밋 전 예외를 삼켜 중복 발송 가능
```

`PLAUSIBLE`이거나 verdict가 없는 finding은 목록만 보여주고 손대지 않습니다 —
검증 안 된 주장이 파일을 고치게 두지 않습니다. 커밋은 요청하기 전까지 안 합니다.

동작 전체는 [SKILL.ko.md](SKILL.ko.md)에 있습니다. Claude가 받는 프롬프트 그 자체라,
읽으면 정확히 뭘 하는지 그대로 보입니다.

## 라이선스

[MIT](LICENSE)
