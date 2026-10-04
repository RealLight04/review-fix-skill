# review-fix

한 줄짜리 수정에 Opus까지 쓸 필요는 없습니다.

코드 리뷰가 찾아낸 finding마다 위험도를 매긴 뒤 그 수정을 안전하게 맡길 수 있는 가장 싼 모델에게
넘기는 [Claude Code](https://claude.com/claude-code) 스킬입니다. 기계적인 수정은 Haiku가, 흔한 버그는
Sonnet이, 잘못 고치면 대가가 큰 건 Opus가 맡습니다.

[English README](README.md) · [English SKILL](SKILL.md)

---

> Claude Code를 처음 써본다면 두 단어만 알고 가면 됩니다. 스킬은 필요할 때 불러 쓰는 프롬프트로,
> 여기서는 `/review-fix`로 부릅니다. finding은 코드 리뷰가 찾아낸 문제 하나를 말합니다. 파일과 줄,
> 무엇이 잘못됐는지가 한 묶음입니다. 이 스킬은 리뷰를 직접 하지 않고 이미 나온 finding을 받아서
> 고치기만 합니다.

## 설치하기 전에 먼저 볼 것

Claude Code에는 `/code-review --fix`가 이미 들어 있고 꽤 잘 만들어져 있습니다. 이 스킬을 깔기 전에
기본 기능이 어디까지 해 주는지부터 확인해 보세요.

- 리뷰 finding을 작업 트리에 바로 적용합니다(`--fix`).
- 다른 세션처럼 `CLAUDE.md`를 따릅니다. `REVIEW.md`는 GitHub에서 도는 관리형 Code Review만 읽고
  로컬 명령은 읽지 않습니다.
- finding마다 fixed / skipped / no change needed 중 하나로 결과를 알려 줍니다.
- effort 레벨(`low`부터 `max`까지)로 얼마나 넓게 볼지와 얼마나 확실한 것만 낼지를 조절합니다.
- `/code-review ultra --fix`로 클라우드에서 더 깊게 리뷰한 뒤 적용할 수 있습니다.

이 정도면 충분하다면 이 스킬은 필요 없습니다. 기본 기능을 쓰세요.

## 이 스킬이 더해 주는 것

`/code-review --fix`가 하지 않는 일이 두 가지 있습니다.

### 1. finding마다 모델을 따로 고릅니다

기본 수정 기능은 모델 하나로 전부 처리합니다. 이 스킬은 finding마다 등급을 매겨서 서로 다른 모델에게
보냅니다.

| 등급 | 기준 | 모델 |
|---|---|---|
| 사무적 | 기계적이고 되돌리기 쉬운 수정. 죽은 파일, 안 쓰는 import, 오타 같은 것 | `haiku` |
| 일반 | 주변 로직을 이해해야 하는 흔한 버그 수정 | `sonnet` |
| 고위험 | 인증, 결제, 마이그레이션, 동시성, 여러 파일에 걸친 동작 변경 | `opus` |

등급이 애매하면 위로 올립니다. 비용을 아끼려고 등급을 내리는 일은 없습니다. 잘못 고친 대가가 모델값보다
훨씬 큽니다.

### 2. 검증에 실패하면 같은 등급에서 한 번, 그다음 한 등급 위에서 한 번 다시 시도합니다

어느 등급이든 서브에이전트가 스스로 올린 보고를 그대로 믿지 않고 직접 확인합니다. 사무적 수정은 파일이
정말 바뀌었는지 보고 일반 수정은 테스트 스크립트를 돌리며 고위험 수정은 diff가 finding 범위를 넘지
않았는지 직접 읽습니다.

확인에서 걸리면 먼저 같은 등급에서 범위를 더 좁혀 한 번 더 시도하고 그래도 안 되면 한 등급 위 모델로
넘깁니다. 거기서도 안 되면 멈추고 상황을 그대로 보고합니다. 조용히 실패한 채 넘어가거나 끝없이 재시도하는
일은 없습니다.

`CLAUDE.md`에 적힌 짝 규칙도 읽습니다. "이 파일을 고치면 저 파일도 고친다" 같은 규칙입니다. finding이
짝 중 한쪽만 가리켜도 나머지까지 함께 고쳐서 반쪽만 고친 채 완료로 보고되는 일을 막습니다.

## 앞서 나온 비슷한 시도

모델을 등급별로 나눠 쓰는 발상은 새롭지 않습니다. 이 스킬도 먼저 나온 작업들을 변형한 것입니다.

- [Aider의 architect/editor 분리](https://aider.chat/2024/09/26/architect.html)(2024년 9월). 강한 모델이
  변경을 설계하고 싼 모델이 diff를 씁니다. 한 작업을 여러 모델 등급에 나눠 맡기는 방식의 원조 격입니다.
  그쪽은 작업 단계로 나누고 이 스킬은 위험도로 나눕니다.
- [AqueGen/model-routing](https://github.com/AqueGen/model-routing). Claude Code 서브에이전트를 작업
  유형(scout, implementer, reviewer)에 따라 나눠 보냅니다. [RouteLLM(ICLR 2025)](https://arxiv.org/pdf/2406.18665)을
  근거로 작업 유형으로 나누는 편이 복잡도 점수로 나누는 것보다 낫다고 주장하는데 이 스킬이 택한 방식과는
  반대되는 결론이라 어느 쪽을 쓸지 고르기 전에 읽어 볼 만합니다.
- [crissmoldovan/agent-skills](https://github.com/crissmoldovan/agent-skills). 모델 라우팅 스킬이 들어 있는
  스킬 묶음입니다. 자동으로 판단하지 않고 미리 정해 둔 프로필대로 나눕니다.

## 아직 재 보지 않은 것

이 분야에서는 수치를 공개하는 곳이 거의 없어서 여기서 먼저 밝혀 둡니다.

- 등급을 나누는 게 실제로 이득인지. finding마다 등급을 매기느라 메인 세션의 토큰이 드는데 이 비용을 싼
  모델로 아낀 비용과 비교해 본 적은 없습니다. finding이 몇 개 안 되면 본전도 못 뽑을 수 있습니다.
- 사무적 finding에서 Haiku가 Opus만큼 해내는지. 작은 케이스 셋으로 한 번 재 봤을 뿐이라 등급 경계는 여전히
  대부분 따져서 정한 것입니다.

[review-fix-bench](https://github.com/RealLight04/review-fix-bench)에 두 번째 질문을 겨냥한 케이스 15개가
있습니다. 등급마다 수정이 제대로 들어가고 범위를 넘지 않는지, 등급표가 기대한 등급을 고르는지를 봅니다. 정답이
이 스킬의 설치 폴더에 같이 깔리지 않도록 별도 레포에 뒀습니다.

결과는 두 번 재서 [여기](https://github.com/RealLight04/review-fix-bench/blob/main/results/RESULTS.md)에
올렸습니다.

첫 번째는 케이스 아홉 개로 Haiku, Sonnet, Opus의 수정 81번과 등급 판정 81번입니다. 사무적 수정 아홉 번은
Haiku도 Opus처럼 모두 해냈습니다. 예외를 삼키는 케이스는 Haiku가 못 고쳤는데 판정 9번이 모두 이 케이스를
Opus로 보냈습니다. 등급표가 기대한 등급과 맞은 건 81번 중 58번이고, 고위험 케이스를 일반으로 낮춰 본 경우가
13번입니다.

두 번째는 케이스 여섯 개를 더해 등급 판정만 54번 돌렸습니다. 인증, 결제, 개인정보, 마이그레이션 케이스는
36번 모두 고위험으로 판정했습니다. 첫 번째에서 낮춰 본 13번은 위험의 이유가 등급표에 적힌 단어가 아닌 두
케이스에 몰려 있었습니다. 그 두 케이스의 기대 등급을 제가 높게 잡았거나 등급표에 그 범주가 빠졌거나 둘 중
하나인데, 이런 케이스가 둘뿐이라 어느 쪽인지 가를 수 없습니다. 등급 경계는 아직 가설입니다. 토큰 수치는 서브에이전트 시작 비용이
대부분이라 첫 번째 질문은 그대로 열려 있습니다.

## delegate와 무엇이 다른가

같은 사람이 만든 [delegate](https://github.com/RealLight04/claude-delegate)도 등급을 매겨 모델을 고르고
결과를 검증합니다. 둘을 가르는 건 무엇을 입력으로 받느냐입니다.

delegate는 서로 독립적인 할 일 목록이면 종류를 가리지 않고 받습니다. 그래서 넘기기 전에 작업이 맥락 없이도
이해되는지, 묶은 뒤 그룹이 몇 개 남는지를 먼저 따집니다. review-fix는 코드 리뷰가 이미 찾아낸 finding만
받습니다. 파일과 줄과 문제가 정해져 있으니 위임 여부를 따질 일이 적고 대신 검증 안 된 finding 거르기,
`CLAUDE.md`에 그 규칙이 정말 있는지 확인하기, 리뷰 뒤에 가리킨 줄이 달라진 finding 건너뛰기, 원래 수정 중이던
파일의 해시를 남겨 보고를 정직하게 하기처럼 리뷰 수정에 맞춘 장치가 더 촘촘합니다.

상황별로 보면 이렇습니다.

- PR에 `/code-review`를 돌렸더니 finding이 여섯 개 나왔습니다. 안 쓰는 import 둘, 빠진 널 체크 하나,
  결제 재시도 버그 하나, 확인이 덜 된 PLAUSIBLE 둘입니다. 이럴 땐 review-fix를 씁니다. 확인된 네 개만
  등급별 모델로 고치고 PLAUSIBLE 두 개는 목록으로만 돌려줍니다.
- 배포 전에 README 오타, 설정 화면 다크 모드 버그, 로그 정리 스크립트 추가, 결제 모듈 리팩터링이
  쌓였습니다. 리뷰에서 나온 게 아니고 성격도 제각각이니 delegate를 씁니다. 파일이 모두 달라 네 그룹으로
  나뉘고 병렬로 처리됩니다.
- 할 일이 한두 개뿐이면 delegate를 쓸 필요가 없습니다. finding이 사소한 것 하나라면 review-fix도
  마찬가지입니다. 그냥 직접 시키는 편이 빠릅니다.

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

리뷰를 먼저 돌린 다음 이렇게 부릅니다.

```
/review-fix
```

인자 없이 부르면 대화에서 가장 최근에 나온 리뷰 결과를 씁니다. finding을 직접 붙여 넣어도 됩니다.

```
/review-fix app/alerts.py:42 dispatch()가 커밋 전에 예외를 삼켜서 알림이 두 번 나갈 수 있음
```

리뷰 결과 중 `PLAUSIBLE`로 표시됐거나 verdict가 없는 finding은 목록에만 올리고 손대지 않습니다. 검증되지
않은 주장으로 파일을 바꾸지는 않습니다. 직접 붙여 넣은 finding은 사용자가 확인한 것으로 봅니다. 다만
`PLAUSIBLE`이 적혀 있으면 붙여 넣었더라도 손대지 않습니다. 고치기 전에는 가리키는 코드를 먼저 읽고 설명한
문제가 없으면 "이미 문제없음"으로 보고합니다. 커밋도 요청하기 전에는 하지 않습니다.

전체 동작은 [SKILL.ko.md](SKILL.ko.md)에 있습니다. Claude가 실제로 받는 프롬프트를 한국어로 옮긴 것이라
읽어 보면 무엇을 하는지 그대로 알 수 있습니다.

## 라이선스

[MIT](LICENSE)
