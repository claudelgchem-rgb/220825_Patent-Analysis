# 검색 대상 데이터베이스와 접근 경로 (A2 필수 · 전부 시도)

한 소스라도 시도하지 않으면 규칙 3 위반이며 G2 게이트 실패다.
시도 결과는 성공/실패와 무관하게 `pcvx/workspace/source_attempts.json` 에 전부 기록한다.

## 1차 소스 (전부 시도 의무)

| 코드 | 이름 | 최신순 검색 진입 형식 |
|---|---|---|
| `GP` | Google Patents | `https://patents.google.com/?q=<QUERY>&sort=new` <br> 국가 한정: `&country=KR,US,EP,JP,CN` <br> 기간 한정: `&after=priority:YYYYMMDD` |
| `ESP` | Espacenet | `https://worldwide.espacenet.com/patent/search?q=<CQL>` (정렬: 공개일 내림차순) |
| `WIPO` | WIPO PATENTSCOPE | `https://patentscope.wipo.int/search/en/result.jsf?query=<QUERY>` (Sort by: Pub Date Desc) |
| `USPTO` | USPTO Patent Public Search / Patent Center | `https://ppubs.uspto.gov/pubwebapp/` , `https://patentcenter.uspto.gov/` |
| `KIPRIS` | 한국특허정보원 KIPRIS | `https://www.kipris.or.kr` (한국 건 필수) |
| `JPP` | J-PlatPat (일본) | `https://www.j-platpat.inpit.go.jp` |
| `CNIPA` | 중국 국가지식산권국 | `https://pss-system.cponline.cnipa.gov.cn` |
| `LENS` | The Lens | `https://www.lens.org/lens/search/patent/list?q=<QUERY>` |

## 계단식 시간 창 (규칙 2)

앞 단계를 끝내기 전에 뒤 단계로 넘어가지 않는다. 각 단계의 수집 건수를 기록한다.

1. 최근 12개월
2. 최근 3년
3. 최근 10년
4. 전체 기간

## 막혔을 때의 3경로 폴백 (규칙 3)

어떤 항목이든 1차 경로가 막히면 아래 순서로 최소 3경로를 시도하고, 시도 순서와 실패 사유를 남긴다.

1. Google Patents 개별 문헌 페이지 (`https://patents.google.com/patent/<DOCID>/en`)
2. Espacenet 개별 문헌 (`https://worldwide.espacenet.com/patent/search?q=pn%3D<DOCID>`)
3. WIPO PATENTSCOPE 개별 문헌
4. 각국 특허청 원문 (KIPRIS / USPTO / J-PlatPat / CNIPA / EPO Register)
5. 논문·보도자료·기업 IR 자료에 인용된 특허번호 (이 경로로만 확보한 값은 신뢰도 '하')

3경로 모두 실패한 경우에만 `[확보 실패]`로 표기하되, 시도 순서와 실패 사유를 함께 적는다.

## 패밀리 단위 중복 제거 (G2)

- 중복 제거 키는 **문헌번호가 아니라 단순패밀리 식별자**다.
- 우선 순위: ① DOCDB 단순패밀리 ID(Espacenet) → ② Google Patents `Worldwide applications` 묶음 → ③ 우선권 번호+우선일 조합.
- 동일 발명의 국가별 대응 특허는 하나의 레코드로 묶고, `family_members` 배열에 각국 문헌번호를 담는다.
- 대표 문헌은 ① 등록건 우선 → ② 청구항 원문 확보가 쉬운 관할 우선 → ③ 최신 공개 우선 순으로 고른다.

## 문헌번호 표기 표준 (A4 · 위반 시 A8이 '혼동'으로 반려)

**출원번호·공개번호·등록번호는 서로 다른 번호이고 형식도 다르다.** 칸마다 그 칸의 번호를 넣는다.
검사기(`validate_records.py`)가 칸 종류별로 따로 본다.

| 관할 | 출원번호 | 공개번호 | 등록번호 |
|---|---|---|---|
| 한국 | `KR 10-2021-0012345` | `KR 10-2022-0098765 A` | `KR 10-2456789 B1` (실용신안 `KR 20-0456789 Y1`) |
| 미국 | `US 17/123,456` | `US 2022/0123456 A1` | `US 11,123,456 B2` |
| 유럽 | `EP 24729299.8` | `EP 3 123 456 A1` | `EP 3 123 456 B1` |
| 일본 | `JP 2016-103846` | `JP 2022-123456 A` | `JP 7123456 B2` (실용신안 `JP 3214309 U`) |
| 중국 | `CN 202210219113.5` (끝자리 검사숫자, `X` 가능) | `CN 114123456 A` | `CN 114123456 B` |
| 국제출원 | `PCT/KR2021/012345` | `WO 2022/123456 A1` | — |

특히 **유럽 출원번호는 공개번호와 전혀 다른 체계**다. `EP 4 724 115 A1` 은 공개번호이지 출원번호가 아니다.
중국·일본 출원번호에는 공보 종별코드(`A`, `B`)가 붙지 않는다.

출원번호를 등록번호처럼 쓰는 것은 금지한다. 등록 여부가 확인되지 않은 건은
`출원 중(등록 미확인)`으로 표기한다.

한국에서 등록이 출원공개보다 먼저 이뤄지면 공개공보가 발행되지 않는다. 그런 건은 공개번호를
지어내지 말고 `해당 없음(출원공개 없이 등록)` 으로 쓰고 근거를 `note` 에 남긴다.
