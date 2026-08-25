#!/usr/bin/env python3
"""records.json 검사기 — 문헌번호 표기, 필수 필드, 등록 여부 구분, 빈 값.

사용법:
  python3 pcvx/scripts/validate_records.py                 # 전체 검사
  python3 pcvx/scripts/validate_records.py --check-numbers # 번호 표기만
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

REQUIRED = [
    "id", "family_id", "representative_doc", "title_original", "title_ko",
    "application_number", "filing_date", "publication_number", "publication_date",
    "registration_number", "registration_date", "registration_status",
    "priority_date", "expiry_estimate", "legal_status", "legal_status_checked_on",
    "applicant", "current_assignee", "inventors", "jurisdiction",
    "ipc", "cpc", "source_url",
    "independent_claim_text", "claim_elements", "plain_explanation",
]

NUMBER_FIELDS = {
    "application_number": "application",
    "publication_number": "publication",
    "registration_number": "registration",
}
FIELD_LABEL = {
    "application": "출원번호", "publication": "공개번호", "registration": "등록번호",
}
EXAMPLES = {
    "application": "KR 10-2021-0012345 / US 17/123,456 / EP 24729299.8 / JP 2016-103846 / CN 202210219113.5",
    "publication": "KR 10-2022-0098765 A / US 2022/0123456 A1 / EP 3 123 456 A1 / JP 2022-123456 A / CN 114123456 A",
    "registration": "KR 10-2456789 B1 / US 11,123,456 B2 / EP 3 123 456 B1 / JP 7123456 B2 / CN 114123456 B",
}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# SOURCES.md 문헌번호 표기 표준: 등록이 출원공개보다 먼저 이뤄지면 공개공보가 발행되지 않는다.
# 그런 건은 공개번호를 지어내지 않고 아래 표기를 쓴다.
NOT_PUBLISHED = "해당 없음(출원공개 없이 등록)"
NOT_APPLICABLE = {"해당 없음(미등록)", NOT_PUBLISHED, common.FAILURE_MARK}


def check_number(value: str, kind: str) -> str | None:
    """표기 위반이면 사유를 돌려준다. 통과면 None.

    칸의 종류(출원/공개/등록)에 맞는 형식인지 본다. 공개번호를 출원번호 칸에 넣는 것은
    통과시키지 않는다 — 세 번호는 서로 다른 번호다.
    """
    value = value.strip()
    if value in NOT_APPLICABLE or value.startswith(common.FAILURE_MARK):
        return None
    table = common.NUMBER_PATTERNS[kind]
    head = value.split(" ")[0].upper()
    if head.startswith("PCT/"):
        head = "WO"
    pattern = table.get(head)
    if pattern is None:
        return (
            f"{FIELD_LABEL[kind]} 칸인데 국가코드로 시작하지 않는다: {value!r}. "
            f"형식 예: {EXAMPLES[kind]}"
        )
    if pattern.match(value):
        return None
    # 다른 종류의 번호를 잘못 넣은 것인지 짚어 준다.
    for other, other_table in common.NUMBER_PATTERNS.items():
        if other == kind:
            continue
        other_pattern = other_table.get(head)
        if other_pattern and other_pattern.match(value):
            return (
                f"{FIELD_LABEL[kind]} 칸에 {FIELD_LABEL[other]}를 넣었다: {value!r}. "
                f"세 번호는 서로 다른 번호다. {FIELD_LABEL[kind]} 형식 예: {EXAMPLES[kind]}"
            )
    return f"{head} {FIELD_LABEL[kind]} 표기 표준에 맞지 않는다: {value!r}. 형식 예: {EXAMPLES[kind]}"


def validate(records: list, numbers_only: bool) -> list[str]:
    problems: list[str] = []
    seen_family: dict[str, str] = {}

    for rec in records:
        rid = rec.get("id") or "<id 없음>"

        for field, kind in NUMBER_FIELDS.items():
            raw = rec.get(field)
            if raw is None or str(raw).strip() == "":
                problems.append(f"{rid}: {field} 가 비어 있다. 값이 없으면 '[확보 실패]' 또는 '해당 없음(미등록)' 을 쓴다.")
                continue
            why = check_number(str(raw), kind)
            if why:
                problems.append(f"{rid}: {field} {why}")

        status = str(rec.get("registration_status", "")).strip()
        reg_no = str(rec.get("registration_number", "")).strip()
        if status and status not in common.REGISTRATION_STATUSES:
            problems.append(
                f"{rid}: registration_status 값 {status!r} 이 허용 목록에 없다 "
                f"({', '.join(sorted(common.REGISTRATION_STATUSES))})."
            )
        if status == "등록" and reg_no in NOT_APPLICABLE:
            problems.append(f"{rid}: 등록 상태인데 등록번호가 '{reg_no}' 다. 번호를 확보하거나 상태를 고친다.")
        if status.startswith("출원 중") and reg_no not in NOT_APPLICABLE:
            problems.append(
                f"{rid}: 미등록 상태인데 등록번호 {reg_no!r} 가 채워져 있다. "
                "출원번호를 등록번호처럼 쓰지 않는다."
            )
        app_no = str(rec.get("application_number", "")).strip()
        if reg_no not in NOT_APPLICABLE and app_no and reg_no == app_no:
            problems.append(f"{rid}: 등록번호와 출원번호가 같은 값이다({reg_no!r}). 서로 다른 번호다.")

        if numbers_only:
            continue

        for field in REQUIRED:
            value = rec.get(field)
            if value is None or (isinstance(value, str) and not value.strip()) or (
                isinstance(value, list) and not value
            ):
                problems.append(f"{rid}: 필수 항목 {field} 가 비어 있다. 빈 값 금지 — '[확보 실패]' + 사유를 쓴다.")

        for field in ("filing_date", "publication_date", "priority_date"):
            value = str(rec.get(field, "")).strip()
            if (
                value
                and not DATE_RE.match(value)
                and not value.startswith(common.FAILURE_MARK)
                and value not in NOT_APPLICABLE
            ):
                problems.append(f"{rid}: {field} 가 YYYY-MM-DD 형식이 아니다: {value!r}")

        checked = str(rec.get("legal_status_checked_on", "")).strip()
        if not DATE_RE.match(checked):
            problems.append(f"{rid}: legal_status_checked_on 이 없다. 확인일 없는 법적 상태 기술은 금지다.")
        elif checked != common.today():
            problems.append(
                f"{rid}: legal_status_checked_on 이 {checked} 로 오늘({common.today()})이 아니다. 오늘 기준으로 재확인한다."
            )

        fam = str(rec.get("family_id", "")).strip()
        if fam:
            if fam in seen_family:
                problems.append(f"{rid}: family_id {fam!r} 가 {seen_family[fam]} 와 중복이다. 패밀리 단위로 묶는다.")
            else:
                seen_family[fam] = rid

        claim = str(rec.get("independent_claim_text", "")).strip()
        if claim.startswith(common.FAILURE_MARK):
            if "시도" not in claim and "→" not in claim:
                problems.append(f"{rid}: 청구항 확보 실패 표기에 시도 경로와 실패 사유가 없다.")
        elif claim and "\n" not in claim:
            problems.append(f"{rid}: 독립항 원문이 한 줄이다. 구성요소가 보이도록 요소별로 줄바꿈한다.")

    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-numbers", action="store_true", help="문헌번호 표기만 검사")
    ap.add_argument("--path", default=str(common.WORKSPACE / "records.json"))
    args = ap.parse_args()

    data = common.read_json(Path(args.path))
    if not data:
        print(f"[실패] {args.path} 가 없다. A3 가 먼저 records.json 을 만들어야 한다.")
        return 1

    records = data.get("records", [])
    print(f"[기준일: {common.today()} / 검사: validate_records]")
    print(f"레코드 {len(records)}건 검사")

    problems = validate(records, args.check_numbers)
    if not problems:
        print("통과: 위반 0건")
        return 0

    print(f"위반 {len(problems)}건")
    for line in problems:
        print(f"  - {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
