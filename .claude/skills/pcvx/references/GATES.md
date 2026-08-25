# 실행 순서와 게이트 (오케스트레이터 판정표)

각 게이트에서 미달 시 해당 에이전트를 **최대 2회 재실행**한다.
그래도 미달이면 미달 사유를 감사 로그에 적고 진행한다(중단 금지).

```
[날짜 확인] → A1 검색식
   └ G1: 검색식 6종 이상 + 분류코드 3개 이상 확보?
→ A2 검색 (최신순, 계단식 확장)
   └ G2: 지정 데이터베이스 전부 시도 + 패밀리 단위 중복 제거 완료?
→ A3 법적상태 → A4 서지정보 → A5 청구항
   └ G3: 목표 건수 확보 + 각 건에 출원번호·출원일 최소 확보?
→ A6 기술 맥락
→ A7 신뢰도 검증 (격리 실행)
   └ G4: 전 항목에 상/중/하 + 판정근거 부여 완료?
→ A8 레드팀
   └ G5: 누락 재검색 2회 이상 실행 + 과대해석 점검 완료?
   └ (반려 발생 시 해당 에이전트 재실행, 최대 2회)
→ A9 보고서 본문
   └ G6: 금지 표현 0건 + 약어 첫 등장 풀어쓰기 100%?
→ A10 파일 생성 (docx / pptx / xlsx)
   └ G7: 3개 파일 실제 생성 + 열어서 내용 확인 완료?
→ A11 감사
   └ G8: 3대 규칙 준수 확인 + 빈 항목 0건?
→ 최종 제시
```

## 기계 판정 기준 (`pcvx/scripts/run_gates.py <GATE>` 가 실제로 검사하는 조건)

| 게이트 | 검사 대상 파일 | 통과 조건 |
|---|---|---|
| G1 | `workspace/a1_queries.json` | `queries` 6개 이상(광역 2·정밀 2·분류 1·출원인 1 유형 모두 존재) AND `classifications` 3개 이상(각 코드에 `note` 존재) |
| G2 | `workspace/a2_hits.json`, `workspace/source_attempts.json` | 8개 소스코드 전부 `attempted=true` AND 계단식 4단계 모두 `window` 기록 AND 모든 레코드에 `family_id` 존재 AND `family_id` 중복 0 |
| G3 | `workspace/records.json` | 레코드 수 ≥ 목표 건수 AND 모든 레코드에 `application_number`·`filing_date` 비어있지 않음 AND `registration_status` ∈ {등록, 출원 중(등록 미확인), 거절, 소멸, 포기, 확보 실패} |
| G4 | `workspace/a7_verification.json` | 검증 항목 수 = 대상 항목 수 AND 모든 항목에 `grade`∈{상,중,하}·`basis`·`sources`(1개↑)·`checked_on` 존재 AND '상' 항목은 `sources` 2개 이상 |
| G5 | `workspace/a8_redteam.json` | `new_queries` 2개 이상 AND 4개 점검(누락·과대해석·최신성·혼동) 모두 `status` 기록 AND 최근 12개월 반영률 기록 |
| G6 | `workspace/a9_report.md` | 금지 표현 0건(허용 목록 제외) AND 약어 첫 등장 풀어쓰기 100% AND 빈 표 셀 0건 |
| G7 | `outputs/*.docx`, `*.pptx`, `*.xlsx` | 3개 파일 존재 AND 각 파일 열림 확인 AND docx 문단 수 > 0, pptx 슬라이드 14~20, xlsx 데이터 행 > 0 |
| G8 | 전체 산출물 5종 | 모든 파일 첫 줄 또는 표지에 `[기준일: YYYY-MM-DD]` AND 금지 표현 0건 AND 빈 셀 0건 |

재실행 이력은 `workspace/gate_log.json` 에 `{gate, attempt, result, reason, at}` 로 누적한다.
