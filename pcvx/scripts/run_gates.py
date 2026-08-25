#!/usr/bin/env python3
"""게이트 판정기 G1~G8 — GATES.md 의 기계 판정 기준을 그대로 검사한다.

사용법:
  python3 pcvx/scripts/run_gates.py G1
  python3 pcvx/scripts/run_gates.py all
  python3 pcvx/scripts/run_gates.py checklist
종료 코드 0 = 통과, 1 = 미달.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

W = common.WORKSPACE


def _fail(msgs: list[str], text: str) -> None:
    msgs.append(text)


def gate_g1() -> list[str]:
    p: list[str] = []
    data = common.read_json(W / "a1_queries.json")
    if not data:
        return ["a1_queries.json 이 없다."]
    queries = data.get("queries", [])
    if len(queries) < 6:
        _fail(p, f"검색식이 {len(queries)}종이다. 6종 이상 필요하다.")
    counts: dict[str, int] = {}
    for q in queries:
        counts[q.get("type", "?")] = counts.get(q.get("type", "?"), 0) + 1
        if not str(q.get("intent", "")).strip():
            _fail(p, f"검색식 {q.get('id', '?')} 에 의도 설명이 없다.")
        if not str(q.get("expression", "")).strip():
            _fail(p, f"검색식 {q.get('id', '?')} 의 식이 비어 있다.")
    for qtype, need in common.QUERY_TYPES.items():
        if counts.get(qtype, 0) < need:
            _fail(p, f"{qtype}형 검색식이 {counts.get(qtype, 0)}종이다. {need}종 이상 필요하다.")
    classes = data.get("classifications", [])
    if len(classes) < 3:
        _fail(p, f"분류코드가 {len(classes)}개다. 3개 이상 필요하다.")
    for c in classes:
        if not str(c.get("note", "")).strip():
            _fail(p, f"분류코드 {c.get('code', '?')} 에 한 줄 설명이 없다.")
    return p


def gate_g2() -> list[str]:
    p: list[str] = []
    attempts = common.read_json(W / "source_attempts.json")
    hits = common.read_json(W / "a2_hits.json")
    if not attempts:
        return ["source_attempts.json 이 없다."]
    if not hits:
        return ["a2_hits.json 이 없다."]

    tried = {a.get("source") for a in attempts.get("attempts", []) if a.get("attempted")}
    missing = [s for s in common.SOURCE_CODES if s not in tried]
    if missing:
        _fail(p, f"시도하지 않은 소스: {', '.join(missing)} — 규칙 3 위반.")

    windows = set(attempts.get("windows", [])) | {
        a.get("window") for a in attempts.get("attempts", [])
    }
    for w in common.WINDOWS:
        if w not in windows:
            _fail(p, f"시간 창 '{w}' 기록이 없다. 계단식 확장을 지킨다.")

    first = (attempts.get("attempts") or [{}])[0].get("window")
    if first and first != common.WINDOWS[0]:
        _fail(p, f"첫 검색 창이 '{first}' 다. 최근 12개월부터 시작한다 — 규칙 2 위반.")

    seen: dict[str, str] = {}
    for h in hits.get("hits", []):
        fam = str(h.get("family_id", "")).strip()
        doc = h.get("representative_doc", "?")
        if not fam:
            _fail(p, f"{doc}: family_id 가 없다. 패밀리 단위 중복 제거를 하지 않았다.")
            continue
        if fam in seen:
            _fail(p, f"family_id {fam} 중복: {doc} 와 {seen[fam]}. 같은 발명을 두 건으로 세지 않는다.")
        else:
            seen[fam] = doc
    return p


def gate_g3() -> list[str]:
    p: list[str] = []
    topic = common.read_json(W / "topic.json", {})
    data = common.read_json(W / "records.json")
    if not data:
        return ["records.json 이 없다."]
    records = data.get("records", [])
    target = int(topic.get("target_count", 20))
    if len(records) < target:
        _fail(p, f"레코드가 {len(records)}건이다. 목표 {target}건에 미달.")
    for rec in records:
        rid = rec.get("id", "?")
        if not str(rec.get("application_number", "")).strip():
            _fail(p, f"{rid}: 출원번호가 없다.")
        if not str(rec.get("filing_date", "")).strip():
            _fail(p, f"{rid}: 출원일이 없다.")
        status = str(rec.get("registration_status", "")).strip()
        if status not in common.REGISTRATION_STATUSES:
            _fail(p, f"{rid}: registration_status {status!r} 가 허용 목록 밖이다.")
    rc = subprocess.run(
        [sys.executable, str(common.SCRIPTS / "validate_records.py"), "--check-numbers"],
        capture_output=True, text=True,
    )
    if rc.returncode != 0:
        _fail(p, "문헌번호 표기 검사 미통과 — validate_records.py --check-numbers 출력 참조.")
    return p


def gate_g4() -> list[str]:
    p: list[str] = []
    src = common.read_json(W / "a7_claims_to_verify.json")
    ver = common.read_json(W / "a7_verification.json")
    if not src:
        return ["a7_claims_to_verify.json 이 없다. make_verify_input.py 를 먼저 실행한다."]
    if not ver:
        return ["a7_verification.json 이 없다."]

    want = {i["claim_id"] for i in src.get("items", [])}
    got = {i.get("claim_id") for i in ver.get("items", [])}
    for missing in sorted(want - got):
        _fail(p, f"검증 누락 항목: {missing}")
    for extra in sorted(got - want):
        _fail(p, f"입력에 없는 항목이 검증 결과에 있다: {extra}")

    for item in ver.get("items", []):
        cid = item.get("claim_id", "?")
        grade = item.get("grade")
        if grade not in common.GRADES:
            _fail(p, f"{cid}: 등급이 상/중/하 가 아니다({grade!r}).")
        if not str(item.get("basis", "")).strip():
            _fail(p, f"{cid}: 판정 근거 한 줄이 없다.")
        sources = item.get("sources") or []
        if not sources:
            _fail(p, f"{cid}: 출처가 없다.")
        if grade == "상" and len(sources) < 2:
            _fail(p, f"{cid}: '상' 등급인데 출처가 {len(sources)}개다. 독립 출처 2개 이상이 필요하다.")
        if not str(item.get("checked_on", "")).strip():
            _fail(p, f"{cid}: 재조회 확인일이 없다.")
    return p


def gate_g5() -> list[str]:
    p: list[str] = []
    data = common.read_json(W / "a8_redteam.json")
    if not data:
        return ["a8_redteam.json 이 없다."]
    new_q = data.get("new_queries", [])
    if len(new_q) < 2:
        _fail(p, f"레드팀 재검색 검색식이 {len(new_q)}개다. 2개 이상 필요하다.")
    for q in new_q:
        if not str(q.get("expression", "")).strip():
            _fail(p, "재검색 검색식 중 식이 비어 있는 것이 있다.")
    checks = data.get("checks", {})
    for name in ("누락", "과대해석", "최신성", "혼동"):
        entry = checks.get(name, {})
        if str(entry.get("status", "")).strip() not in ("통과", "반려"):
            _fail(p, f"'{name}' 점검의 status 가 통과/반려 로 기록되지 않았다.")
    if "recent_12m_ratio" not in checks.get("최신성", {}):
        _fail(p, "최신성 점검에 최근 12개월 반영률(recent_12m_ratio)이 없다.")
    return p


def gate_g6() -> list[str]:
    path = W / "a9_report.md"
    if not path.exists():
        return ["a9_report.md 가 없다."]
    rc = subprocess.run(
        [sys.executable, str(common.SCRIPTS / "validate_report.py"), str(path)],
        capture_output=True, text=True,
    )
    if rc.returncode != 0:
        return [line.strip("  - ") for line in rc.stdout.splitlines() if line.startswith("  - ")]
    return []


def gate_g7() -> list[str]:
    rc = subprocess.run(
        [sys.executable, str(common.SCRIPTS / "inspect_outputs.py")],
        capture_output=True, text=True,
    )
    if rc.returncode != 0:
        return [l for l in rc.stdout.splitlines() if l.strip().startswith("-")] or [
            "inspect_outputs.py 미통과"
        ]
    return []


def gate_g8() -> list[str]:
    p: list[str] = []
    out = common.output_dir()
    stamp = common.today_compact()
    expected = ["특허조사보고서", "특허대장", "근거대장", "감사로그"]
    files = list(out.glob("PCVX_*"))
    for key in expected:
        if not any(key in f.name for f in files):
            _fail(p, f"산출물 누락: PCVX_{key}_*")
    for f in files:
        if stamp not in f.name:
            _fail(p, f"{f.name}: 파일명에 오늘 날짜({stamp})가 없다.")
    rc = subprocess.run(
        [sys.executable, str(common.SCRIPTS / "validate_report.py"), "--scan-outputs"],
        capture_output=True, text=True,
    )
    if rc.returncode != 0:
        p += [line.strip("  - ") for line in rc.stdout.splitlines() if line.startswith("  - ")]
    rc2 = subprocess.run(
        [sys.executable, str(common.SCRIPTS / "inspect_outputs.py"), "--strict"],
        capture_output=True, text=True,
    )
    if rc2.returncode != 0:
        p += [l.strip() for l in rc2.stdout.splitlines() if l.strip().startswith("-")]
    return p


GATES = {
    "G1": ("검색식 6종 이상 + 분류코드 3개 이상", gate_g1),
    "G2": ("지정 데이터베이스 전부 시도 + 패밀리 단위 중복 제거", gate_g2),
    "G3": ("목표 건수 확보 + 출원번호·출원일 최소 확보", gate_g3),
    "G4": ("전 항목 상/중/하 + 판정근거 부여", gate_g4),
    "G5": ("누락 재검색 2회 이상 + 과대해석 점검", gate_g5),
    "G6": ("금지 표현 0건 + 약어 첫 등장 풀어쓰기 100%", gate_g6),
    "G7": ("3개 파일 실제 생성 + 열어서 내용 확인", gate_g7),
    "G8": ("3대 규칙 준수 + 빈 항목 0건", gate_g8),
}

CHECKLIST = [
    ("오늘 날짜를 실제 명령으로 확인했고, 모든 산출물에 기준일이 적혀 있다", ["G8"]),
    ("최근 12개월 자료를 가장 먼저 조사했고, 그 결과가 보고서에 반영되어 있다", ["G2", "G5"]),
    ("미루기 표현이 산출물에 0건이다", ["G6", "G8"]),
    ("모든 특허에 출원번호·출원일이 있고 등록 여부가 명확히 구분되어 있다", ["G3"]),
    ("청구항 해설이 초보자가 읽을 수 있게 작성되었다", ["G6"]),
    ("신뢰도 검증이 분리 실행되었고 항목 단위로 상/중/하가 부여되었다", ["G4"]),
    ("'하' 등급 항목이 단정형으로 서술되지 않았다", ["G6"]),
    ("워드·PPT·엑셀 파일이 실제로 생성되어 출력 디렉터리에 있다", ["G7"]),
    ("한계 문단이 보고서에 원문 그대로 들어가 있다", ["G7"]),
]


def log_result(gate: str, problems: list[str]) -> None:
    path = W / "gate_log.json"
    log = common.read_json(path, {"entries": []})
    attempts = sum(1 for e in log["entries"] if e["gate"] == gate) + 1
    log["entries"].append(
        {
            "gate": gate,
            "attempt": attempts,
            "result": "통과" if not problems else "미달",
            "reason": problems,
            "at": common.today(),
        }
    )
    common.write_json(path, log)


def run_one(gate: str) -> int:
    title, fn = GATES[gate]
    problems = fn()
    log_result(gate, problems)
    if problems:
        print(f"[{gate}] 미달 — {title}")
        for line in problems:
            print(f"  - {line}")
        return 1
    print(f"[{gate}] 통과 — {title}")
    return 0


def run_checklist() -> int:
    print(f"[기준일: {common.today()} / 완료 조건 체크리스트]")
    results = {g: not GATES[g][1]() for g in GATES}
    bad = 0
    for text, gates in CHECKLIST:
        ok = all(results.get(g, False) for g in gates)
        bad += 0 if ok else 1
        mark = "예" if ok else "아니오"
        print(f"  [{mark}] {text}  (근거 게이트: {', '.join(gates)})")
    print(f"\n미충족 {bad}건")
    return 0 if bad == 0 else 1


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    target = sys.argv[1]
    print(f"[기준일: {common.today()} / 게이트 판정]")
    if target == "checklist":
        return run_checklist()
    if target == "all":
        rc = 0
        for gate in GATES:
            rc |= run_one(gate)
        return rc
    gate = target.upper()
    if gate not in GATES:
        print(f"알 수 없는 게이트: {target}. 가능한 값: {', '.join(GATES)}, all, checklist")
        return 2
    return run_one(gate)


if __name__ == "__main__":
    raise SystemExit(main())
