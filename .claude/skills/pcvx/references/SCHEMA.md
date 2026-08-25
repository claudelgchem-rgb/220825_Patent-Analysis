# 에이전트 간 데이터 계약 (모든 파일은 `pcvx/workspace/` 에 UTF-8 JSON)

에이전트는 자유 서술이 아니라 **아래 스키마에 맞는 JSON 파일**을 남긴다.
게이트 검사기(`run_gates.py`)와 문서 생성기(`build_*.py`)가 이 파일들만 읽는다.

| 파일 | 생산자 | 소비자 |
|---|---|---|
| `env.json` | preflight | 전 에이전트 |
| `topic.json` | 오케스트레이터 | A1, A9, A10 |
| `a1_queries.json` | A1 | A2, A8, A10 |
| `source_attempts.json` | A2 | G2, A11 |
| `a2_hits.json` | A2 | A3 |
| `records.json` | A3·A4·A5 누적 갱신 | A6, A7, A9, A10 |
| `a6_context.json` | A6 | A9, A10 |
| `a7_claims_to_verify.json` | 오케스트레이터가 records.json에서 **추출·평탄화** | A7 |
| `a7_verification.json` | A7 | A9, A10, A11 |
| `a8_redteam.json` | A8 | 오케스트레이터(반려 판정) |
| `a9_report.md` | A9 | A10 |
| `gate_log.json` | 오케스트레이터 | A11 |

## topic.json

```json
{
  "topic": "조사 주제 원문",
  "topic_slug": "파일명용 축약형",
  "jurisdictions": ["KR","US","EP","JP","CN"],
  "period": "최근 10년",
  "assignee_filter": "한정 없음",
  "target_count": 50,
  "confirmed_on": "YYYY-MM-DD"
}
```

## a1_queries.json

```json
{
  "as_of": "YYYY-MM-DD", "agent": "A1",
  "terms": {"synonyms": [], "english": [], "broader": [], "narrower": [], "jargon": []},
  "classifications": [{"code": "H01M 10/0562", "system": "CPC", "note": "이 분류가 무엇을 다루는지 한 줄"}],
  "queries": [{"id":"Q1","type":"광역","expression":"...","intent":"이 검색식으로 무엇을 잡으려는지"}]
}
```

`type` 은 `광역`(2건 이상), `정밀`(2건 이상), `분류코드`(1건 이상), `출원인`(1건 이상) — 합계 6건 이상.

## source_attempts.json

```json
{"as_of":"YYYY-MM-DD","agent":"A2",
 "attempts":[{"source":"GP","attempted":true,"url":"...","window":"최근 12개월","hits":37,"note":"","failure":""}],
 "windows":["최근 12개월","최근 3년","최근 10년","전체 기간"]}
```

실패한 시도도 `attempted: true` 로 남기고 `failure` 에 사유를 적는다. 빠뜨린 소스만 `false` 다.

## records.json — 핵심 레코드

```json
{"as_of":"YYYY-MM-DD","records":[{
  "id": "P001",
  "family_id": "DOCDB 단순패밀리 ID 또는 우선권번호+우선일",
  "family_members": ["KR 10-2022-0098765 A","US 2023/0123456 A1"],
  "representative_doc": "KR 10-2456789 B1",
  "title_original": "", "title_ko": "",
  "application_number": "", "filing_date": "YYYY-MM-DD",
  "publication_number": "", "publication_date": "YYYY-MM-DD",
  "registration_number": "", "registration_date": "",
  "registration_status": "등록 | 출원 중(등록 미확인) | 거절 | 소멸 | 포기 | 확보 실패",
  "priority_date": "YYYY-MM-DD",
  "expiry_estimate": "존속기간 만료 예정일",
  "legal_status": "", "legal_status_checked_on": "YYYY-MM-DD",
  "applicant": "", "current_assignee": "", "assignment_history": "",
  "inventors": [], "jurisdiction": "KR",
  "ipc": [], "cpc": [], "source_url": "",
  "independent_claim_text": "요소별 줄바꿈된 독립항 원문",
  "claim_elements": [{"element":"","role":"","scope_effect":"권리범위를 좁히는지 넓히는지와 그 이유"}],
  "dependent_claim_summary": "권리범위에 실질적 영향이 있는 종속항만",
  "plain_explanation": "전문 용어 없는 3~5문장 해설",
  "acquisition_failures": [{"field":"","tried":["GP","ESP","WIPO"],"reason":""}]
}]}
```

- 청구항 원문을 확보하지 못하면 `independent_claim_text` 에 `[확보 실패]` 와 시도 경로를 적는다.
  요약서·초록으로 청구항을 추정해 채우는 것은 금지다.
- 값이 없는 필드를 빈 문자열로 두지 않는다. `[확보 실패]` + 사유를 적는다.
  (단, 미등록 건의 `registration_number`·`registration_date` 는 `해당 없음(미등록)` 으로 적는다.)

## a7_claims_to_verify.json — A7 격리 입력 (오케스트레이터가 생성)

A7에게는 이 파일 **하나만** 넘긴다. 조사 에이전트의 추론·요약·근거 설명은 넣지 않는다.

```json
{"as_of":"YYYY-MM-DD",
 "items":[{"claim_id":"P001.filing_date","record_id":"P001","field":"filing_date",
           "value":"2021-03-04","source_url":"https://...","accessed_on":"YYYY-MM-DD"}]}
```

## a7_verification.json

```json
{"as_of":"YYYY-MM-DD","agent":"A7",
 "items":[{"claim_id":"P001.filing_date","grade":"상",
           "basis":"판정 근거 한 줄","sources":["url1","url2"],
           "checked_on":"YYYY-MM-DD","corrected":false,
           "original_value":"","corrected_value":""}],
 "distribution":{"상":0,"중":0,"하":0,"low_ratio":0.0}}
```

## a8_redteam.json

```json
{"as_of":"YYYY-MM-DD","agent":"A8",
 "new_queries":[{"expression":"","intent":"","new_hits":0}],
 "checks":{
   "누락":{"status":"통과|반려","detail":"","to_agent":"A2"},
   "과대해석":{"status":"","detail":"","to_agent":"A5"},
   "최신성":{"status":"","recent_12m_ratio":0.0,"detail":"","to_agent":"A2"},
   "혼동":{"status":"","detail":"","to_agent":"A4"}},
 "remands":[{"agent":"A5","record_id":"P007","reason":""}]}
```

A8은 직접 수정하지 않는다. `remands` 에 담아 해당 에이전트로 반려한다(수정 권한 분리).

## a6_context.json

```json
{"as_of":"YYYY-MM-DD","agent":"A6",
 "yearly_filings":[{"year":2016,"count":3}],
 "top_applicants":[{"name":"","count":0,"note":""}],
 "branches":[{"name":"기술 갈래","summary":"","record_ids":[]}],
 "recent_12m":[{"headline":"","record_ids":[],"source_url":""}]}
```
