#!/usr/bin/env python3
"""하니스 자체 점검 — 가짜 조사 데이터로 파이프라인 전체를 한 번 돌려 본다.

실제 특허 데이터가 아니라 배관 점검용 표본이다. 이 점검이 통과해야
게이트 검사기와 문서 생성기가 실제 조사에서 동작한다고 말할 수 있다.

  python3 pcvx/scripts/selftest.py            # 임시 작업 공간에서 실행 후 정리
  python3 pcvx/scripts/selftest.py --keep     # 결과물을 남긴다
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402

TODAY = common.today()
YEAR = int(TODAY[:4])


def fixture_records() -> dict:
    return {
        "as_of": TODAY,
        "records": [
            {
                "id": "P001",
                "family_id": "FAM-0001",
                "family_members": ["KR 10-2021-0012345", "US 2022/0123456 A1"],
                "representative_doc": "KR 10-2456789 B1",
                "title_original": "표본 고체 전해질 조성물",
                "title_ko": "표본 고체 전해질 조성물",
                "application_number": "KR 10-2021-0012345",
                "filing_date": "2021-03-04",
                "publication_number": "KR 10-2022-0098765 A",
                "publication_date": "2022-09-01",
                "registration_number": "KR 10-2456789 B1",
                "registration_date": "2023-05-12",
                "registration_status": "등록",
                "priority_date": "2021-03-04",
                "expiry_estimate": "2041-03-04 (출원일 기준 20년, 존속기간 연장 없음)",
                "legal_status": "등록 유지",
                "legal_status_checked_on": TODAY,
                "applicant": "표본화학 주식회사",
                "current_assignee": "표본화학 주식회사",
                "assignment_history": "양도 이력 없음",
                "inventors": ["홍길동", "김표본"],
                "jurisdiction": "KR",
                "ipc": ["H01M 10/0562"],
                "cpc": ["H01M 10/0562"],
                "source_url": "https://patents.google.com/patent/KR102456789B1/ko",
                "independent_claim_text": (
                    "황화물계 고체 전해질을 포함하는 전해질층과,\n"
                    "상기 전해질층의 일면에 배치된 양극층과,\n"
                    "상기 전해질층의 타면에 배치된 음극층을 포함하는 전고체 전지."
                ),
                "claim_elements": [
                    {"element": "황화물계 고체 전해질을 포함하는 전해질층",
                     "role": "이온이 지나가는 통로 역할을 한다",
                     "scope_effect": "황화물계로 한정했으므로 산화물계를 쓰는 제품은 이 청구항에 걸리지 않는다"},
                    {"element": "전해질층 일면의 양극층",
                     "role": "전기를 내보내는 쪽이다",
                     "scope_effect": "배치 위치를 특정해 구조가 다른 전지를 권리범위 밖으로 밀어낸다"},
                ],
                "dependent_claim_summary": "제2항은 전해질층 두께를 한정해 권리범위를 좁힌다.",
                "plain_explanation": (
                    "이 특허는 배터리 안에서 액체 대신 굳은 물질로 전기를 나르는 구조를 다룬다. "
                    "그 굳은 물질을 황이 들어간 재료로 만들고, 그 양옆에 전기를 내보내는 층과 받는 층을 붙인 형태다. "
                    "따라서 황이 들어간 재료로 같은 구조를 만들어 파는 행위를 막는다. "
                    "황이 아닌 다른 재료를 쓰면 이 특허에는 걸리지 않는다."
                ),
                "acquisition_failures": [],
            },
            {
                "id": "P002",
                "family_id": "FAM-0002",
                "family_members": ["US 17/123,456"],
                "representative_doc": "US 2022/0123456 A1",
                "title_original": "Sample separator for secondary battery",
                "title_ko": "이차전지용 표본 분리막",
                "application_number": "US 17/123,456",
                "filing_date": "2021-11-19",
                "publication_number": "US 2022/0123456 A1",
                "publication_date": "2022-04-21",
                "registration_number": "해당 없음(미등록)",
                "registration_date": "해당 없음(미등록)",
                "registration_status": "출원 중(등록 미확인)",
                "priority_date": "2020-12-01",
                "expiry_estimate": "2041-11-19 (등록 시 출원일 기준 20년, 특허기간조정 미반영)",
                "legal_status": "심사 계속",
                "legal_status_checked_on": TODAY,
                "applicant": "Sample Materials Inc.",
                "current_assignee": "Sample Materials Inc.",
                "assignment_history": "양도 이력 없음",
                "inventors": ["John Sample"],
                "jurisdiction": "US",
                "ipc": ["H01M 50/40"],
                "cpc": ["H01M 50/403"],
                "source_url": "https://patents.google.com/patent/US20220123456A1/en",
                "independent_claim_text": (
                    "A separator comprising a porous substrate,\n"
                    "and a coating layer disposed on at least one surface of the porous substrate,\n"
                    "wherein the coating layer comprises inorganic particles."
                ),
                "claim_elements": [
                    {"element": "다공성 기재", "role": "전기를 통하지 않게 막으면서 이온은 지나가게 한다",
                     "scope_effect": "구멍이 없는 막을 쓰는 제품은 권리범위 밖이 된다"},
                    {"element": "무기 입자를 포함하는 코팅층", "role": "열에 견디게 해 준다",
                     "scope_effect": "무기 입자로 한정해 유기 코팅만 쓴 제품은 걸리지 않는다"},
                ],
                "dependent_claim_summary": "제3항은 무기 입자의 크기를 한정해 범위를 좁힌다.",
                "plain_explanation": (
                    "이 출원은 배터리 안에서 두 극이 서로 닿지 않게 막아 주는 얇은 막을 다룬다. "
                    "구멍이 뚫린 막 위에 돌가루 같은 알갱이를 발라 열에 잘 견디게 만든 것이다. "
                    "그래서 구멍 뚫린 막에 무기 알갱이를 발라 파는 행위를 막으려는 것이다. "
                    "다만 아직 등록되지 않아 권리가 발생한 상태는 아니다."
                ),
                "acquisition_failures": [
                    {"field": "registration_date", "tried": ["GP", "USPTO", "ESP"],
                     "reason": "심사가 계속 중이어서 등록일 자체가 존재하지 않는다"},
                ],
            },
            {
                "id": "P003",
                "family_id": "FAM-0003",
                "family_members": ["JP 2022-123456 A"],
                "representative_doc": "JP 2022-123456 A",
                "title_original": "表本電極材料",
                "title_ko": "표본 전극 재료",
                "application_number": "JP 2022-123456",
                "filing_date": "2022-02-14",
                "publication_number": "JP 2022-123456 A",
                "publication_date": "2022-08-22",
                "registration_number": "해당 없음(미등록)",
                "registration_date": "해당 없음(미등록)",
                "registration_status": "출원 중(등록 미확인)",
                "priority_date": "2021-02-15",
                "expiry_estimate": "2042-02-14 (등록 시 출원일 기준 20년)",
                "legal_status": "심사 청구 완료",
                "legal_status_checked_on": TODAY,
                "applicant": "表本電池株式会社",
                "current_assignee": "表本電池株式会社",
                "assignment_history": "양도 이력 없음",
                "inventors": ["表本 太郎"],
                "jurisdiction": "JP",
                "ipc": ["H01M 4/38"],
                "cpc": ["H01M 4/386"],
                "source_url": "https://patents.google.com/patent/JP2022123456A/ja",
                "independent_claim_text": "[확보 실패] 구글 특허, 유럽특허청 에스파스넷, 세계지식재산기구 특허스코프, 일본 제이플랫팻 순으로 시도했으나 청구항 전문 원문에 접근하지 못했다.",
                "claim_elements": [
                    {"element": "[확보 실패]", "role": "청구항 원문 미확보",
                     "scope_effect": "원문 미확보로 판단 불가"},
                ],
                "dependent_claim_summary": "[확보 실패] 청구항 원문을 얻지 못해 종속항도 정리하지 못했다.",
                "plain_explanation": (
                    "이 출원의 청구항 원문을 네 곳에서 찾아보았으나 얻지 못했다. "
                    "제목과 분류로 보면 배터리의 전극에 쓰는 재료를 다루는 것으로 보이나 원문 확인이 필요하다. "
                    "무엇을 막는 특허인지는 원문을 보기 전에는 말할 수 없다."
                ),
                "acquisition_failures": [
                    {"field": "independent_claim_text",
                     "tried": ["GP", "ESP", "WIPO", "JPP"],
                     "reason": "네 경로 모두에서 청구항 전문이 열리지 않았다"},
                ],
            },
        ],
    }


def fixture_queries() -> dict:
    return {
        "as_of": TODAY, "agent": "A1",
        "terms": {
            "synonyms": ["고체 전해질", "전고체 전해질", "무기 전해질"],
            "english": ["solid electrolyte", "solid-state electrolyte", "all solid state"],
            "broader": ["이차전지", "에너지 저장 장치", "전기화학 소자"],
            "narrower": ["황화물계 고체 전해질", "산화물계 고체 전해질", "고분자 고체 전해질"],
            "jargon": ["전고체", "ASSB", "SSE"],
        },
        "classifications": [
            {"code": "H01M 10/0562", "system": "CPC", "note": "무기 고체 전해질을 쓰는 이차전지를 다루는 분류다"},
            {"code": "H01M 4/38", "system": "CPC", "note": "전극 활물질 재료를 다루는 분류다"},
            {"code": "H01M 50/40", "system": "IPC", "note": "이차전지 분리막 구조를 다루는 분류다"},
        ],
        "queries": [
            {"id": "Q1", "type": "광역", "expression": '("solid electrolyte" OR "solid-state electrolyte")',
             "intent": "표현이 다른 특허까지 폭넓게 잡아 누락을 줄인다"},
            {"id": "Q2", "type": "광역", "expression": '(전고체 OR "고체 전해질")',
             "intent": "한국어 표기 특허를 놓치지 않는다"},
            {"id": "Q3", "type": "정밀", "expression": '("sulfide" AND "solid electrolyte" AND "all-solid-state battery")',
             "intent": "황화물계로 좁혀 잡음을 줄인다"},
            {"id": "Q4", "type": "정밀", "expression": '("oxide" AND "garnet" AND "solid electrolyte")',
             "intent": "산화물계 갈래만 따로 본다"},
            {"id": "Q5", "type": "분류코드", "expression": "CPC=H01M10/0562",
             "intent": "용어를 쓰지 않은 특허를 분류로 잡는다"},
            {"id": "Q6", "type": "출원인", "expression": 'assignee:("표본화학" OR "Sample Materials")',
             "intent": "상위 출원인의 포트폴리오를 통째로 훑는다"},
        ],
    }


def fixture_attempts() -> dict:
    attempts = []
    for window in common.WINDOWS:
        for code in common.SOURCE_CODES:
            attempts.append({
                "source": code, "attempted": True,
                "url": f"https://example.invalid/{code.lower()}?sort=new&window={window}",
                "window": window, "hits": 3, "accessed_on": TODAY,
                "note": "자체 점검용 표본 기록이다", "failure": "",
            })
    return {"as_of": TODAY, "agent": "A2", "attempts": attempts, "windows": common.WINDOWS}


def fixture_hits(records: dict) -> dict:
    return {
        "as_of": TODAY, "agent": "A2",
        "hits": [
            {"family_id": r["family_id"], "family_members": r["family_members"],
             "representative_doc": r["representative_doc"], "title": r["title_ko"],
             "jurisdiction": r["jurisdiction"], "publication_date": r["publication_date"],
             "source_url": r["source_url"], "matched_query": "Q1",
             "relevance_note": "주제의 핵심 갈래에 해당한다"}
            for r in records["records"]
        ],
        "dropped": [{"doc": "KR 10-2019-0000001", "reason": "주제와 다른 연료전지 분야다"}],
        "stage_counts": {w: 3 for w in common.WINDOWS},
    }


def fixture_context(records: dict) -> dict:
    return {
        "as_of": TODAY, "agent": "A6",
        "method": "records.json 의 우선일을 연도별로 직접 세었다",
        "yearly_filings": [{"year": y, "count": c} for y, c in
                           [(YEAR - 5, 0), (YEAR - 4, 1), (YEAR - 3, 1), (YEAR - 2, 1),
                            (YEAR - 1, 0), (YEAR, 0)]],
        "top_applicants": [
            {"name": "표본화학 주식회사", "count": 1, "note": "황화물계 갈래를 잡고 있다"},
            {"name": "Sample Materials Inc.", "count": 1, "note": "분리막 코팅 갈래를 잡고 있다"},
            {"name": "表本電池株式会社", "count": 1, "note": "전극 재료 갈래를 잡고 있다"},
        ],
        "branches": [
            {"name": "황화물계 고체 전해질", "summary": "황이 들어간 재료로 전해질을 만드는 갈래다",
             "record_ids": ["P001"]},
            {"name": "분리막 코팅", "summary": "막 위에 무기 알갱이를 발라 열에 견디게 하는 갈래다",
             "record_ids": ["P002"]},
            {"name": "전극 재료", "summary": "전극에 쓰는 재료 자체를 바꾸는 갈래다",
             "record_ids": ["P003"]},
        ],
        "recent_12m": [
            {"headline": "최근 12개월 신규 공개 0건으로 확인되었다",
             "record_ids": [], "source_url": "https://example.invalid/gp?sort=new"},
        ],
    }


def fixture_redteam() -> dict:
    return {
        "as_of": TODAY, "agent": "A8",
        "new_queries": [
            {"expression": '("garnet" AND "lithium lanthanum zirconium oxide")',
             "intent": "A1이 안 쓴 물질명으로 다시 훑는다", "new_hits": 0},
            {"expression": "CPC=H01M50/403 AND 무기 입자", "intent": "다른 분류 섹션으로 재검색한다",
             "new_hits": 0},
        ],
        "checks": {
            "누락": {"status": "통과", "detail": "새 검색식 2종으로 재검색했고 신규 패밀리는 나오지 않았다", "to_agent": "A2"},
            "과대해석": {"status": "통과", "detail": "해설 3건을 청구항 문언과 대조했고 문언 밖 서술은 없었다", "to_agent": "A5"},
            "최신성": {"status": "통과", "recent_12m_ratio": 0.0,
                       "detail": "최근 12개월 창을 첫 단계로 검색했고 신규 공개가 0건임을 확인했다", "to_agent": "A2"},
            "혼동": {"status": "통과", "detail": "번호 표기 검사기가 위반 0건을 냈고 표본 3건을 원출처와 대조했다", "to_agent": "A4"},
        },
        "remands": [],
    }


def fixture_verification(verify_input: dict) -> dict:
    items, dist = [], {"상": 0, "중": 0, "하": 0}
    for entry in verify_input["items"]:
        field = entry["field"]
        value = entry["value"]
        if value.startswith(common.FAILURE_MARK):
            grade, sources, basis = "하", [entry["source_url"]], "3경로 재시도 후에도 원출처를 열지 못했다"
        elif field in {"application_number", "filing_date", "publication_number", "publication_date"}:
            grade = "상"
            sources = [entry["source_url"], "https://example.invalid/office-original"]
            basis = "특허청 공보 원문과 집계 데이터베이스가 같은 값이다"
        else:
            grade, sources, basis = "중", [entry["source_url"]], "2차 집계 데이터베이스 1곳에서만 확인했다"
        dist[grade] += 1
        items.append({
            "claim_id": entry["claim_id"], "grade": grade, "basis": basis,
            "sources": sources, "checked_on": TODAY,
            "corrected": False, "original_value": "", "corrected_value": "",
        })
    total = sum(dist.values()) or 1
    dist["low_ratio"] = round(dist["하"] / total, 4)
    return {"as_of": TODAY, "agent": "A7", "items": items, "distribution": dist}


def fixture_report(records: dict, context: dict, verification: dict) -> str:
    dist = verification["distribution"]
    total = dist["상"] + dist["중"] + dist["하"]
    out = [
        "# 1. 표지",
        "",
        f"이 보고서는 {TODAY} 기준으로 표본 주제에 대한 특허를 조사한 결과다. "
        "조사에 사용한 데이터베이스와 검색식은 부록에 모두 실었다. "
        "값 하나하나의 출처와 확인 날짜는 근거 대장에 따로 정리해 두었다. "
        "이 문서만으로 판단하기 어려운 부분은 근거 대장을 함께 보면 된다.",
        "",
        "# 2. 이 보고서를 읽는 법",
        "",
        "특허 이야기는 낯선 말이 많아서, 먼저 몇 가지 말뜻부터 정리하고 시작한다. "
        "출원(특허청에 심사를 신청하는 행위)은 아직 권리가 생긴 것이 아니라 신청만 한 상태를 뜻한다. "
        "등록(심사를 통과해 권리가 발생한 상태)이 되어야 비로소 남을 막을 힘이 생긴다. "
        "이 둘을 섞어 읽으면 없는 권리를 있다고 착각하게 되므로 표에서 반드시 구분해 보아야 한다.",
        "",
        "권리의 크기를 정하는 것은 청구항이라는 문장이다. "
        "그중 독립항(다른 항에 기대지 않고 홀로 권리범위를 정하는 청구항)이 가장 넓은 범위를 잡는다. "
        "종속항(독립항을 인용해 그 범위를 좁히는 청구항)은 독립항에 조건을 더 붙여 범위를 줄인다. "
        "우선일(권리의 선후를 따지는 기준일)은 누가 먼저인지를 가리는 날짜이고, "
        "존속기간(권리가 살아있는 기간)은 그 권리가 언제까지 살아 있는지를 말한다.",
        "",
        "분류 기호도 두 가지가 나온다. "
        "국제특허분류(IPC, International Patent Classification)는 전 세계가 함께 쓰는 기술 분류 체계다. "
        "협력적 특허분류(CPC, Cooperative Patent Classification)는 그보다 더 잘게 나눈 분류 체계다. "
        "두 분류는 검색할 때 서로 보완하는 역할을 한다.",
        "",
        "신뢰도 등급은 값을 얼마나 믿을 수 있는지를 세 단계로 나눈 것이다. "
        "높음은 특허청 원문과 독립된 다른 출처 두 곳이 같은 값을 보인 경우다. "
        "보통은 집계 데이터베이스 한 곳에서만 확인한 경우이고, 낮음은 원문 대조를 마치지 못한 경우다. "
        "낮음으로 표시된 값은 단정해서 읽지 말고 원문을 직접 확인한 뒤 쓰는 것이 안전하다.",
        "",
        "이것이 우리에게 왜 중요한가. 말뜻을 정확히 잡고 읽어야 표에 적힌 숫자를 잘못 해석하지 않는다. "
        "특히 등록과 출원을 구분하지 못하면 아직 존재하지 않는 권리를 피하려고 애쓰는 낭비가 생긴다. "
        "반대로 이미 살아 있는 권리를 놓치면 나중에 훨씬 큰 비용을 치르게 된다.",
        "",
        "# 3. 한눈에 보는 요약",
        "",
        f"이번 조사에서 확인한 특허 패밀리(같은 발명을 여러 나라에 출원한 묶음)는 모두 {len(records['records'])}건이다. "
        "이 가운데 이미 등록되어 권리가 살아 있는 것은 한 건이고, 나머지는 아직 심사가 끝나지 않았다. "
        "청구항 원문을 얻지 못한 건이 한 건 있어 그 건은 낮음 등급으로 처리했다. "
        "아래 표는 핵심 발견을 다섯 가지로 추린 것이다.",
        "",
        "다음 표는 이번 조사에서 가장 먼저 알아야 할 다섯 가지를 정리한 것이다. "
        "왼쪽 칸이 발견 내용이고 오른쪽 칸이 그 근거와 신뢰도 등급이다. "
        "등급 표시가 낮음인 줄은 아직 원문으로 확인하지 못한 내용이라는 뜻이다.",
        "",
        "| 핵심 발견 | 근거와 등급 |",
        "|---|---|",
        "| 등록되어 살아 있는 권리는 한 건이다 | 등록원부에서 확인했다 [상] |",
        "| 나머지 두 건은 아직 심사 중이다 | 각국 심사경과에서 확인했다 [상] |",
        "| 기술은 세 갈래로 나뉜다 | 수집한 특허의 청구항 구조로 나누었다 [중] |",
        "| 출원인은 세 곳으로 흩어져 있다 | 수집 표본 안에서의 집계다 [중] |",
        "| 한 건은 청구항 원문을 얻지 못해 내용을 단정할 수 없다 | 네 경로 시도 기록을 남겨 두었다 [하] |",
        "",
        f"등급 분포는 높음 {dist['상']}개, 보통 {dist['중']}개, 낮음 {dist['하']}개다. "
        f"전체 {total}개 항목 가운데 낮음 비율은 {dist['low_ratio'] * 100:.1f}퍼센트다.",
        "",
        "이것이 우리에게 왜 중요한가. 요약만 보고 판단하면 낮음 등급이 섞여 있다는 사실을 놓치기 쉽다. "
        "어떤 값이 확인된 것이고 어떤 값이 아직 아닌지를 함께 보아야 의사결정에 쓸 수 있다.",
        "",
        "# 4. 기술 분야 개관",
        "",
        "이 분야가 지금 어떤 상태인지부터 살펴본다. "
        "연도별로 보면 출원은 한 해에 한 건 안팎으로 꾸준히 나오다가 최근 해에는 잡히지 않았다. "
        "출원 후 18개월이 지나야 공개되는 제도 때문에, 가장 최근 출원이 아직 드러나지 않은 것으로 보인다. "
        "따라서 최근 해의 숫자가 0이라는 것을 활동이 멈춘 것으로 읽으면 안 된다.",
        "",
        "다음 표는 우선일을 기준으로 연도별 건수를 센 것이다. "
        "왼쪽이 연도이고 오른쪽이 그 해에 우선일이 잡힌 건수다. "
        "건수가 없는 해도 0으로 적어 두었으므로 빠진 해는 없다.",
        "",
        "| 연도 | 건수 |",
        "|---|---|",
    ]
    for row in context["yearly_filings"]:
        out.append(f"| {row['year']} | {row['count']} |")
    out += [
        "",
        "기술은 크게 세 갈래로 나뉜다. "
        "첫째는 전해질 자체를 굳은 재료로 바꾸는 갈래이고, 둘째는 막 위에 무기 알갱이를 발라 열에 견디게 하는 갈래다. "
        "셋째는 전극에 쓰는 재료를 바꾸는 갈래다. "
        "세 갈래는 해결하려는 문제가 서로 달라서, 한 갈래의 특허가 다른 갈래를 막지는 않는다.",
        "",
        "이것이 우리에게 왜 중요한가. 어느 갈래를 택하느냐에 따라 부딪히게 될 권리가 완전히 달라진다. "
        "갈래를 먼저 정하고 그 갈래의 권리만 좁혀 보는 편이 훨씬 효율적이다.",
        "",
        "# 5. 특허 상세",
        "",
    ]
    for rec in records["records"]:
        out += [
            f"## {rec['id']} · {rec['representative_doc']}",
            "",
            "다음 표는 이 특허의 기본 정보를 정리한 것이다. "
            "왼쪽이 항목 이름이고 오른쪽이 확인된 값이며, 대괄호 안의 글자가 신뢰도 등급이다. "
            "등록 여부 칸을 먼저 보면 이 권리가 지금 살아 있는지 아닌지를 바로 알 수 있다.",
            "",
            "| 항목 | 값 |",
            "|---|---|",
            f"| 제목 | {rec['title_ko']} [중] |",
            f"| 출원번호 | {rec['application_number']} [상] |",
            f"| 출원일 | {rec['filing_date']} [상] |",
            f"| 공개번호 | {rec['publication_number']} [상] |",
            f"| 등록번호 | {rec['registration_number']} [중] |",
            f"| 등록 여부 | {rec['registration_status']} [중] |",
            f"| 우선일 | {rec['priority_date']} [중] |",
            f"| 존속기간 만료 예정일 | {rec['expiry_estimate']} [중] |",
            f"| 법적 상태 | {rec['legal_status']} (확인일 {rec['legal_status_checked_on']}) [중] |",
            f"| 현재 권리자 | {rec['current_assignee']} [중] |",
            f"| 원문 주소 | {rec['source_url']} [중] |",
            "",
            "독립항 원문은 다음과 같다.",
            "",
        ]
        for line in rec["independent_claim_text"].splitlines():
            out.append(line)
        out += [
            "",
            "다음 표는 위 청구항을 구성요소별로 쪼갠 것이다. "
            "각 요소가 무슨 일을 하는지와, 그 요소 때문에 권리범위가 어떻게 달라지는지를 함께 적었다. "
            "권리범위를 좁히는 요소가 많을수록 피해 가기가 쉬워진다.",
            "",
            "| 구성요소 | 역할 | 권리범위에 미치는 영향 |",
            "|---|---|---|",
        ]
        for el in rec["claim_elements"]:
            out.append(f"| {el['element']} | {el['role']} | {el['scope_effect']} |")
        out += [
            "",
            rec["plain_explanation"],
            "",
            "이것이 우리에게 왜 중요한가. 이 건의 구성요소 가운데 하나라도 쓰지 않으면 이 청구항에는 걸리지 않는다. "
            "따라서 회피 설계를 검토할 때는 가장 좁게 한정된 요소부터 살펴보는 것이 순서다.",
            "",
        ]
    out += [
        "# 6. 종합 정리",
        "",
        "세 갈래를 나란히 놓고 보면 권리가 몰려 있는 곳과 비어 있는 곳이 드러난다. "
        "전해질 갈래에는 이미 등록된 권리가 있어 가장 조심해야 한다. "
        "분리막 갈래와 전극 재료 갈래는 아직 심사 중이어서 지금 당장 막는 힘은 없다. "
        "다만 심사가 끝나면 상황이 달라지므로 경과를 계속 보아야 한다.",
        "",
        "출원인 쪽을 보면 세 곳이 한 건씩 나누어 가지고 있어 한 곳에 몰려 있지는 않다. "
        "이 숫자는 이번에 수집한 표본 안에서의 집계이며 전 세계 순위가 아니다. "
        "표본이 세 건이므로 이 분포만으로 시장 구도를 단정하기는 어렵다. "
        "더 넓은 집계가 필요하면 유료 데이터베이스로 전수 조사를 해야 한다.",
        "",
        "이것이 우리에게 왜 중요한가. 권리가 몰린 갈래를 피해 가는 것만으로도 위험을 크게 줄일 수 있다. "
        "반대로 비어 보이는 갈래도 심사 중인 출원 때문에 나중에 막힐 수 있으므로 경과 관찰이 필요하다.",
        "",
    ]
    return "\n".join(out) + "\n"


def run(cmd: list[str], env: dict) -> tuple[int, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return proc.returncode, (proc.stdout + proc.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="임시 산출물을 지우지 않는다")
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="pcvx-selftest-"))
    ws, out = tmp / "workspace", tmp / "outputs"
    ws.mkdir(parents=True)
    out.mkdir(parents=True)
    env = dict(os.environ, PCVX_WORKSPACE=str(ws), PCVX_OUTPUT=str(out))

    print(f"[기준일: {TODAY} / 자체 점검]")
    print(f"임시 작업 공간: {tmp}")

    records = fixture_records()
    common.write_json(ws / "topic.json", {
        "topic": "표본 주제 전고체 전지 고체 전해질", "topic_slug": "표본_전고체",
        "jurisdictions": ["KR", "US", "JP"], "period": "최근 10년",
        "assignee_filter": "한정 없음", "target_count": 3, "confirmed_on": TODAY,
    })
    common.write_json(ws / "a1_queries.json", fixture_queries())
    common.write_json(ws / "source_attempts.json", fixture_attempts())
    common.write_json(ws / "a2_hits.json", fixture_hits(records))
    common.write_json(ws / "records.json", records)
    context = fixture_context(records)
    common.write_json(ws / "a6_context.json", context)
    common.write_json(ws / "a8_redteam.json", fixture_redteam())

    steps: list[tuple[str, list[str]]] = [
        ("preflight", [sys.executable, str(HERE / "preflight.py")]),
        ("G1", [sys.executable, str(HERE / "run_gates.py"), "G1"]),
        ("G2", [sys.executable, str(HERE / "run_gates.py"), "G2"]),
        ("번호 표기 검사", [sys.executable, str(HERE / "validate_records.py"), "--check-numbers"]),
        ("레코드 전체 검사", [sys.executable, str(HERE / "validate_records.py")]),
        ("G3", [sys.executable, str(HERE / "run_gates.py"), "G3"]),
        ("A7 격리 입력 생성", [sys.executable, str(HERE / "make_verify_input.py")]),
    ]
    failures: list[str] = []
    for label, cmd in steps:
        rc, output = run(cmd, env)
        print(f"\n--- {label} (exit={rc}) ---\n{output.strip()}")
        if rc != 0:
            failures.append(label)

    verify_input = common.read_json(ws / "a7_claims_to_verify.json")
    common.write_json(ws / "a7_verification.json", fixture_verification(verify_input))
    verification = common.read_json(ws / "a7_verification.json")
    (ws / "a9_report.md").write_text(fixture_report(records, context, verification), encoding="utf-8")

    steps2 = [
        ("G4", [sys.executable, str(HERE / "run_gates.py"), "G4"]),
        ("G5", [sys.executable, str(HERE / "run_gates.py"), "G5"]),
        ("보고서 본문 검사", [sys.executable, str(HERE / "validate_report.py"), str(ws / "a9_report.md")]),
        ("G6", [sys.executable, str(HERE / "run_gates.py"), "G6"]),
        ("엑셀 생성", [sys.executable, str(HERE / "build_xlsx.py")]),
        ("워드 생성", [sys.executable, str(HERE / "build_docx.py")]),
        ("발표자료 생성", [sys.executable, str(HERE / "build_pptx.py")]),
        ("근거 대장 생성", [sys.executable, str(HERE / "build_evidence.py")]),
        ("산출물 실물 검사", [sys.executable, str(HERE / "inspect_outputs.py")]),
        ("G7", [sys.executable, str(HERE / "run_gates.py"), "G7"]),
    ]
    for label, cmd in steps2:
        rc, output = run(cmd, env)
        print(f"\n--- {label} (exit={rc}) ---\n{output.strip()}")
        if rc != 0:
            failures.append(label)

    # 감사 로그는 A11이 쓰지만, 자체 점검에서는 형식만 갖춘 표본을 넣어 G8을 검사한다.
    (out / f"PCVX_감사로그_{common.today_compact()}.md").write_text(
        f"[기준일: {TODAY} / 에이전트: A11]\n\n# 감사 로그 (자체 점검 표본)\n\n"
        "이 파일은 배관 점검용 표본이며 실제 감사 결과가 아니다.\n",
        encoding="utf-8",
    )
    for label, cmd in [
        ("산출물 금지 표현 검사", [sys.executable, str(HERE / "validate_report.py"), "--scan-outputs"]),
        ("G8", [sys.executable, str(HERE / "run_gates.py"), "G8"]),
        ("완료 조건 체크리스트", [sys.executable, str(HERE / "run_gates.py"), "checklist"]),
    ]:
        rc, output = run(cmd, env)
        print(f"\n--- {label} (exit={rc}) ---\n{output.strip()}")
        if rc != 0:
            failures.append(label)

    print("\n" + "=" * 60)
    if failures:
        print(f"자체 점검 실패 {len(failures)}건: {', '.join(failures)}")
    else:
        print("자체 점검 통과: 모든 단계 정상")
    print(f"산출물: {out}")
    for f in sorted(out.glob('*')):
        print(f"  {f.name}  {f.stat().st_size:,} bytes")

    if not args.keep:
        shutil.rmtree(tmp, ignore_errors=True)
        print("임시 작업 공간 정리 완료 (--keep 을 주면 남긴다)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
