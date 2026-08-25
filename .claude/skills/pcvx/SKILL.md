---
name: pcvx
description: "특허 서지·청구항 정리와 독립 신뢰도 검증을 수행하는 다중 에이전트 조사 하니스(PCVX, Patent Claim & Verification eXplorer)를 실행한다. 특허 조사, 선행기술 조사, 특허 landscape, 청구항 분석, 특허 동향 보고서, 경쟁사 특허 분석을 요청받았을 때 사용한다. 워드 보고서·PPT·엑셀 대장·근거 대장·감사 로그 5종을 한 번의 실행으로 완성한다."
---

# PCVX — 특허 조사·검증 하니스 오케스트레이터

당신은 오케스트레이터(O)다. A1~A11 하위 에이전트를 순차 실행하고, 게이트를 판정하고,
최종 산출물 5종을 완성해 제시한다.

## 시작 전에 반드시 읽을 것

`references/RULES.md` 를 먼저 읽는다. 그 3대 규칙은 당신과 모든 하위 에이전트에 적용된다.
하위 에이전트를 띄울 때는 **`references/RULES.md` 의 본문을 프롬프트 맨 앞에 그대로 복사**한다.
요약하거나 "규칙을 따르라"고만 쓰는 것은 위반이다.

참조 문서:

| 파일 | 언제 읽나 |
|---|---|
| `references/RULES.md` | 항상 (모든 에이전트 프롬프트 선두에 복사) |
| `references/SCHEMA.md` | 에이전트 실행 전 — 산출 JSON 형식 |
| `references/SOURCES.md` | A2·A3·A4·A8 프롬프트에 첨부 |
| `references/GRADING.md` | A7·A9 프롬프트에 첨부 |
| `references/STYLE.md` | A5·A9 프롬프트에 첨부 |
| `references/DOC_SPEC.md` | A10 프롬프트에 첨부 |
| `references/LIMITS.md` | A9·A10 (원문 그대로 삽입) |
| `references/GATES.md` | 게이트 판정 시 |

## 0단계 — 준비

```bash
date +"%Y-%m-%d (%A) %H:%M %Z" && date -u +"%Y-%m-%d %H:%M UTC"
python3 pcvx/scripts/preflight.py
```

`preflight.py` 는 오늘 날짜, 출력 디렉터리, 문서 생성 도구(node / python), 렌더 도구를
실제로 시험해 `pcvx/workspace/env.json` 에 기록한다. 이 파일의 `as_of` 가 모든 산출물의 기준일이다.

하니스 자체가 성한지 의심스러우면 다음 두 점검을 먼저 돌린다. 둘 다 임시 공간에서 돌고 실제 작업물을 건드리지 않는다.

```bash
python3 pcvx/scripts/selftest.py        # 표본 데이터로 파이프라인 전체를 한 번 돌린다
python3 pcvx/scripts/negative_test.py   # 일부러 규칙을 어긴 입력을 게이트가 잡는지 본다
```

## 1단계 — 주제 확정

주제가 이미 주어졌으면 그대로 확정하고 **질문 없이 끝까지 완주**한다.
주제가 비어 있으면 `AskUserQuestion` 으로 **단 한 번만** 묻는다. 답을 받는 즉시 나머지 조건은
아래 기본값으로 확정하고 이후 어떤 것도 되묻지 않는다.

| 조건 | 기본값 |
|---|---|
| 관할국 | 한국·미국·유럽·일본·중국 |
| 기간 | 최근 20년 |
| 기업·기관 한정 | 한정 없음 |
| 목표 건수 | 20건 |

확정 결과를 `pcvx/workspace/topic.json` 에 `references/SCHEMA.md` 형식으로 저장한다.

## 2단계 — A1~A11 실행

각 에이전트는 Agent 도구로 **독립 실행**한다. 에이전트 타입은 `.claude/agents/` 의 정의를 쓴다.

| 순서 | 에이전트 타입 | 역할 | 산출 |
|---|---|---|---|
| 1 | `pcvx-a1-query` | 주제 해석·검색식 설계 | `a1_queries.json` |
| 2 | `pcvx-a2-search` | 다중 데이터베이스 검색 | `a2_hits.json`, `source_attempts.json` |
| 3 | `pcvx-a3-legal` | 패밀리·법적상태 추적 | `records.json` 갱신 |
| 4 | `pcvx-a4-biblio` | 서지정보 추출 | `records.json` 갱신 |
| 5 | `pcvx-a5-claims` | 청구항 해석 | `records.json` 갱신 |
| 6 | `pcvx-a6-context` | 기술 맥락 정리 | `a6_context.json` |
| 7 | `pcvx-a7-verify` | 신뢰도 검증 ★격리★ | `a7_verification.json` |
| 8 | `pcvx-a8-redteam` | 반론·누락 점검 | `a8_redteam.json` |
| 9 | `pcvx-a9-writer` | 보고서 본문 | `a9_report.md` |
| 10 | `pcvx-a10-docs` | docx / pptx / xlsx 생성 | 출력 3종 |
| 11 | `pcvx-a11-audit` | 감사 | 감사 로그 |

A3·A4·A5는 같은 `records.json` 을 갱신하므로 **순차로** 실행한다(동시 실행 금지).
그 외에 병렬로 돌릴 수 있는 구간은 없다. 순서대로 간다.

### A7 격리 — 타협 대상이 아님

A7을 띄우기 전에 오케스트레이터가 직접 다음을 실행한다.

```bash
python3 pcvx/scripts/make_verify_input.py
```

이 스크립트는 `records.json` 을 항목 단위로 평탄화해 `a7_claims_to_verify.json` 을 만든다.
담기는 것은 `[항목] [값] [출처 URL] [접속일]` 넷뿐이다.

A7 프롬프트에는 **`a7_claims_to_verify.json` 경로만** 준다.
A1~A6의 산출물 경로, 추론 과정, 요약, "이 값은 이래서 맞다" 같은 설명을 절대 넘기지 않는다.
검증자가 조사자의 논리에 오염되지 않게 하려는 의도이며, 이 격리는 타협 대상이 아니다.

### A8 권한 분리

A8은 발견한 문제를 **직접 수정하지 않는다.** `a8_redteam.json` 의 `remands` 에 담는다.
오케스트레이터가 반려 대상 에이전트를 다시 띄워 수정하게 한다(에이전트당 최대 2회).

## 3단계 — 게이트 판정

각 에이전트 종료 직후 해당 게이트를 돌린다.

```bash
python3 pcvx/scripts/run_gates.py G1     # G1 … G8
python3 pcvx/scripts/run_gates.py all    # 전체 재검
```

- 통과 → 다음 단계.
- 미달 → 미달 사유를 그대로 담아 **같은 에이전트를 최대 2회 재실행**.
- 2회 재실행 후에도 미달 → 미달 사유를 `gate_log.json` 과 감사 로그에 적고 **진행한다. 중단하지 않는다.**

## 4단계 — 산출물 생성과 제시

A10이 5종을 만들고, A11이 감사한 뒤, 최종 파일 경로를 사용자에게 제시한다.
중간 보고로 턴을 끝내지 않는다. 한 번의 실행에서 워드와 PPT 생성까지 끝낸다.

## 완료 조건 체크리스트 (전부 예(Yes)여야 종료)

```bash
python3 pcvx/scripts/run_gates.py checklist
```

- [ ] 오늘 날짜를 실제 명령으로 확인했고, 모든 산출물에 기준일이 적혀 있다
- [ ] 최근 12개월 자료를 가장 먼저 조사했고, 그 결과가 보고서에 반영되어 있다
- [ ] "추후", "예정", "TBD", "확인 필요" 등 미루기 표현이 산출물에 0건이다
- [ ] 모든 특허에 대해 출원번호·출원일이 있으며, 등록 여부가 명확히 구분되어 있다
- [ ] 청구항 해설이 전문 용어 없이 초보자가 읽을 수 있게 작성되었다
- [ ] 신뢰도 검증 에이전트가 조사 에이전트와 분리되어 실행되었고, 항목 단위로 상/중/하가 부여되었다
- [ ] '하' 등급 항목이 보고서에서 단정형으로 서술되지 않았다
- [ ] 워드·PPT·엑셀 파일이 실제로 생성되어 출력 디렉터리에 있다
- [ ] 한계 문단(`references/LIMITS.md`)이 보고서에 원문 그대로 들어가 있다
