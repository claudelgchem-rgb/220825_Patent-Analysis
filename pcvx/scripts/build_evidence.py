#!/usr/bin/env python3
"""4번 산출물 — 근거·출처 대장 md. 항목별 출처 URL·접속일·신뢰도 등급·정정 이력."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

FIELD_LABELS = {
    "title_original": "제목(원문)", "application_number": "출원번호", "filing_date": "출원일",
    "publication_number": "공개번호", "publication_date": "공개일",
    "registration_number": "등록번호", "registration_date": "등록일",
    "registration_status": "등록 여부", "priority_date": "우선일",
    "expiry_estimate": "존속기간 만료 예정일", "legal_status": "법적 상태",
    "applicant": "출원인", "current_assignee": "현재 권리자", "inventors": "발명자",
    "ipc": "국제특허분류", "cpc": "협력적 특허분류",
    "independent_claim_text": "독립항 원문",
}


def main() -> int:
    env = common.env()
    records = (common.read_json(common.WORKSPACE / "records.json", {}) or {}).get("records", [])
    verification = common.read_json(common.WORKSPACE / "a7_verification.json", {}) or {}
    attempts = common.read_json(common.WORKSPACE / "source_attempts.json", {}) or {}
    if not verification.get("items"):
        print("[실패] a7_verification.json 에 검증 항목이 없다. A7 을 먼저 실행한다.")
        return 1

    by_record: dict[str, list[dict]] = {}
    for item in verification["items"]:
        rid = str(item.get("claim_id", "")).split(".")[0]
        by_record.setdefault(rid, []).append(item)

    dist = verification.get("distribution", {})
    total = sum(dist.get(g, 0) for g in common.GRADES) or len(verification["items"])
    low_ratio = dist.get("low_ratio") or dist.get("하", 0) / (total or 1)

    lines = [
        f"[기준일: {env['as_of']} / 에이전트: A10 근거·출처 대장]",
        "",
        "# 근거·출처 대장",
        "",
        "이 문서는 보고서에 실린 값 하나하나가 어디서 나왔는지를 기록한 것이다. "
        "값이 맞는지 다시 확인하고 싶을 때는 해당 항목의 출처 주소를 열어 접속일과 함께 보면 된다. "
        "신뢰도 등급은 특허 건이 아니라 항목 단위로 매겼으므로, 같은 특허 안에서도 항목마다 등급이 다를 수 있다.",
        "",
        "## 등급 분포",
        "",
        "| 등급 | 항목 수 | 비율 |",
        "|---|---|---|",
    ]
    for grade in common.GRADES:
        count = dist.get(grade, 0)
        lines.append(f"| {grade} | {count} | {count / (total or 1) * 100:.1f}% |")
    lines += [
        f"| 합계 | {total} | 100.0% |",
        "",
        f"신뢰도 '하' 등급 비율은 {low_ratio * 100:.1f}퍼센트다.",
    ]
    if low_ratio > 0.30:
        lines += ["", f"> {common.low_ratio_warning()}"]

    lines += ["", "## 항목별 근거", ""]
    for rec in records:
        rid = rec.get("id", "?")
        doc = common.cell(rec.get("representative_doc"))
        title = common.cell(rec.get("title_ko") or rec.get("title_original"))
        lines += [
            f"### {rid} · {doc}",
            "",
            f"{title}",
            "",
            "아래 표는 이 특허에 대해 보고서에 적은 값과 그 근거를 항목별로 정리한 것이다. "
            "등급 칸은 그 값을 얼마나 믿을 수 있는지를 나타내고, 판정 근거 칸은 왜 그 등급인지를 한 줄로 설명한다. "
            "정정 칸에 값이 있으면 원출처와 달라 고쳤다는 뜻이다.",
            "",
            "| 항목 | 등급 | 판정 근거 | 출처 | 재조회 확인일 | 정정 이력 |",
            "|---|---|---|---|---|---|",
        ]
        items = by_record.get(rid, [])
        if not items:
            lines.append(
                f"| 전체 | 하 | 검증 항목이 만들어지지 않았다 | {common.cell(rec.get('source_url'))} "
                f"| {common.cell(rec.get('legal_status_checked_on'), env['as_of'])} | 정정 없음 |"
            )
        for item in items:
            field = str(item.get("claim_id", "")).split(".")[-1]
            label = FIELD_LABELS.get(field, field)
            corrected = (
                f"{common.cell(item.get('original_value'), '(빈 값)')} → "
                f"{common.cell(item.get('corrected_value'), '(빈 값)')}"
                if item.get("corrected") else "정정 없음"
            )
            sources = " , ".join(item.get("sources") or [common.FAILURE_MARK])
            lines.append(
                f"| {label} | {common.cell(item.get('grade'))} | {common.cell(item.get('basis'))} "
                f"| {sources} | {common.cell(item.get('checked_on'), env['as_of'])} | {corrected} |"
            )
        failures = rec.get("acquisition_failures") or []
        if failures:
            lines += ["", "확보에 실패한 항목과 시도 경로는 다음과 같다.", ""]
            for f in failures:
                lines.append(
                    f"- {common.cell(f.get('field'))}: "
                    f"{' → '.join(f.get('tried') or [common.FAILURE_MARK])} 순으로 시도했고, "
                    f"{common.cell(f.get('reason'))} 때문에 얻지 못했다."
                )
        lines.append("")

    lines += [
        "## 데이터베이스 접속 기록",
        "",
        "아래 표는 어떤 데이터베이스를 어떤 시간 창으로 열었고 몇 건을 얻었는지 남긴 것이다. "
        "접근이 막혀 실패한 시도도 그대로 남겨 두었으므로, 어디까지 훑었는지를 이 표로 확인할 수 있다. "
        "법적 상태는 접속일 기준이라는 점을 함께 보아야 한다.",
        "",
        "| 소스 | URL | 시간 창 | 수집 건수 | 접속일 | 비고 |",
        "|---|---|---|---|---|---|",
    ]
    for a in attempts.get("attempts", []):
        lines.append(
            f"| {common.cell(a.get('source'))} | {common.cell(a.get('url'))} "
            f"| {common.cell(a.get('window'))} | {common.cell(a.get('hits'), '0')} "
            f"| {common.cell(a.get('accessed_on'), env['as_of'])} "
            f"| {common.cell(a.get('failure') or a.get('note'), '정상 수행')} |"
        )

    out = common.output_dir() / f"PCVX_근거대장_{env['as_of_compact']}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[기준일: {env['as_of']} / 도구: build_evidence]")
    print(f"-> {out}  ({out.stat().st_size:,} bytes, 항목 {total}개)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
