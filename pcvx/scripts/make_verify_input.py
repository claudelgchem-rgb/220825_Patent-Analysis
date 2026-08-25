#!/usr/bin/env python3
"""A7 격리 입력 생성기 — records.json 을 항목 단위로 평탄화한다.

A7 에게는 이 결과물 하나만 넘긴다. 조사 에이전트의 추론·요약·근거 설명은 담지 않는다.
담기는 것은 [항목] [값] [출처 URL] [접속일] 넷뿐이다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

# 검증 대상 항목 — 값이 판단 근거가 되는 필드만.
VERIFY_FIELDS = [
    "title_original",
    "application_number",
    "filing_date",
    "publication_number",
    "publication_date",
    "registration_number",
    "registration_date",
    "registration_status",
    "priority_date",
    "expiry_estimate",
    "legal_status",
    "applicant",
    "current_assignee",
    "inventors",
    "ipc",
    "cpc",
    "independent_claim_text",
]


def main() -> int:
    data = common.read_json(common.WORKSPACE / "records.json")
    if not data:
        print("[실패] records.json 이 없다. A3~A5 를 먼저 실행한다.")
        return 1

    as_of = common.today()
    items = []
    for rec in data.get("records", []):
        rid = rec.get("id", "?")
        url = str(rec.get("source_url", "")).strip() or common.FAILURE_MARK
        accessed = str(rec.get("legal_status_checked_on", "")).strip() or as_of
        for field in VERIFY_FIELDS:
            if field not in rec:
                continue
            value = rec[field]
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            items.append(
                {
                    "claim_id": f"{rid}.{field}",
                    "record_id": rid,
                    "field": field,
                    "value": str(value),
                    "source_url": url,
                    "accessed_on": accessed,
                }
            )

    payload = {
        "as_of": as_of,
        "note": (
            "이 파일은 A7 전용 격리 입력이다. 조사 에이전트의 추론 과정은 담기지 않았다. "
            "각 항목을 원출처에서 직접 재조회해 검증하라."
        ),
        "items": items,
    }
    out = common.WORKSPACE / "a7_claims_to_verify.json"
    common.write_json(out, payload)
    print(f"[기준일: {as_of} / 도구: make_verify_input]")
    print(f"레코드 {len(data.get('records', []))}건 → 검증 항목 {len(items)}개")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
