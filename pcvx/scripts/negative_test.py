#!/usr/bin/env python3
"""역방향 점검 — 일부러 규칙을 어긴 입력을 넣어 게이트가 실제로 반려하는지 본다.

통과만 확인하는 점검은 통과를 증명하지 못한다. 각 위반이 잡히지 않으면 이 점검이 실패한다.
"""
from __future__ import annotations

import copy
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402
import selftest as fx  # noqa: E402

TODAY = common.today()


def seed(ws: Path) -> dict:
    records = fx.fixture_records()
    context = fx.fixture_context(records)
    common.write_json(ws / "topic.json", {
        "topic": "표본 주제", "topic_slug": "표본", "jurisdictions": ["KR"],
        "period": "최근 10년", "assignee_filter": "한정 없음",
        "target_count": 3, "confirmed_on": TODAY,
    })
    common.write_json(ws / "a1_queries.json", fx.fixture_queries())
    common.write_json(ws / "source_attempts.json", fx.fixture_attempts())
    common.write_json(ws / "a2_hits.json", fx.fixture_hits(records))
    common.write_json(ws / "records.json", records)
    common.write_json(ws / "a6_context.json", context)
    common.write_json(ws / "a8_redteam.json", fx.fixture_redteam())
    subprocess.run([sys.executable, str(HERE / "make_verify_input.py")],
                   capture_output=True, env=dict(os.environ, PCVX_WORKSPACE=str(ws)))
    vi = common.read_json(ws / "a7_claims_to_verify.json")
    ver = fx.fixture_verification(vi)
    common.write_json(ws / "a7_verification.json", ver)
    (ws / "a9_report.md").write_text(fx.fixture_report(records, context, ver), encoding="utf-8")
    return {"records": records, "context": context, "verification": ver}


# --- 위반 주입기 ---------------------------------------------------------


def break_missing_source(ws: Path) -> None:
    data = common.read_json(ws / "source_attempts.json")
    data["attempts"] = [a for a in data["attempts"] if a["source"] != "KIPRIS"]
    common.write_json(ws / "source_attempts.json", data)


def break_family_duplicate(ws: Path) -> None:
    data = common.read_json(ws / "a2_hits.json")
    data["hits"][1]["family_id"] = data["hits"][0]["family_id"]
    common.write_json(ws / "a2_hits.json", data)


def break_application_as_registration(ws: Path) -> None:
    data = common.read_json(ws / "records.json")
    rec = data["records"][1]  # 출원 중인 건에 등록번호를 채워 넣는다
    rec["registration_number"] = rec["application_number"]
    common.write_json(ws / "records.json", data)


def break_stale_legal_check(ws: Path) -> None:
    data = common.read_json(ws / "records.json")
    data["records"][0]["legal_status_checked_on"] = "2020-01-01"
    common.write_json(ws / "records.json", data)


def break_missing_verification(ws: Path) -> None:
    data = common.read_json(ws / "a7_verification.json")
    data["items"] = data["items"][:-3]
    common.write_json(ws / "a7_verification.json", data)


def break_high_grade_single_source(ws: Path) -> None:
    data = common.read_json(ws / "a7_verification.json")
    for item in data["items"]:
        if item["grade"] == "상":
            item["sources"] = item["sources"][:1]
            break
    common.write_json(ws / "a7_verification.json", data)


def break_forbidden_phrase(ws: Path) -> None:
    path = ws / "a9_report.md"
    path.write_text(path.read_text(encoding="utf-8")
                    + "\n등록 여부는 추후 확인 필요하다.\n", encoding="utf-8")


def break_low_grade_assertion(ws: Path) -> None:
    path = ws / "a9_report.md"
    path.write_text(path.read_text(encoding="utf-8")
                    + "\n이 특허는 경쟁 제품 전부를 막는다. [하]\n", encoding="utf-8")


def break_bare_abbreviation(ws: Path) -> None:
    path = ws / "a9_report.md"
    path.write_text(path.read_text(encoding="utf-8")
                    + "\n분류는 CPC 기준으로 정리했다.\n", encoding="utf-8")


def break_redteam_one_query(ws: Path) -> None:
    data = common.read_json(ws / "a8_redteam.json")
    data["new_queries"] = data["new_queries"][:1]
    common.write_json(ws / "a8_redteam.json", data)


def break_query_shortfall(ws: Path) -> None:
    data = common.read_json(ws / "a1_queries.json")
    data["queries"] = data["queries"][:4]
    common.write_json(ws / "a1_queries.json", data)


CASES = [
    ("지정 데이터베이스 하나를 건너뛰면 G2가 잡는다", break_missing_source, "G2"),
    ("같은 패밀리를 두 건으로 세면 G2가 잡는다", break_family_duplicate, "G2"),
    ("출원번호를 등록번호로 쓰면 G3가 잡는다", break_application_as_registration, "G3"),
    ("법적상태 확인일이 오래되면 레코드 검사가 잡는다", break_stale_legal_check, "records"),
    ("검증 항목을 빠뜨리면 G4가 잡는다", break_missing_verification, "G4"),
    ("'상' 등급에 출처가 하나뿐이면 G4가 잡는다", break_high_grade_single_source, "G4"),
    ("금지 표현을 쓰면 G6가 잡는다", break_forbidden_phrase, "G6"),
    ("'하' 등급을 단정형으로 쓰면 G6가 잡는다", break_low_grade_assertion, "G6"),
    ("약어를 풀어쓰지 않으면 G6가 잡는다", break_bare_abbreviation, "G6"),
    ("레드팀 재검색이 1개면 G5가 잡는다", break_redteam_one_query, "G5"),
    ("검색식이 6종 미만이면 G1이 잡는다", break_query_shortfall, "G1"),
]


def check(gate: str, ws: Path, out: Path) -> tuple[int, str]:
    env = dict(os.environ, PCVX_WORKSPACE=str(ws), PCVX_OUTPUT=str(out))
    cmd = (
        [sys.executable, str(HERE / "validate_records.py")]
        if gate == "records"
        else [sys.executable, str(HERE / "run_gates.py"), gate]
    )
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout.strip()


def main() -> int:
    print(f"[기준일: {TODAY} / 역방향 점검]")
    base = Path(tempfile.mkdtemp(prefix="pcvx-negative-"))
    ws0, out0 = base / "ws", base / "out"
    ws0.mkdir(parents=True)
    out0.mkdir(parents=True)
    subprocess.run([sys.executable, str(HERE / "preflight.py")], capture_output=True,
                   env=dict(os.environ, PCVX_WORKSPACE=str(ws0), PCVX_OUTPUT=str(out0)))
    seed(ws0)

    # 먼저 손대지 않은 입력이 통과하는지 확인한다. 통과하지 않으면 역방향 점검이 무의미하다.
    misses: list[str] = []
    for gate in ("G1", "G2", "G3", "G4", "G5", "G6", "records"):
        rc, _ = check(gate, ws0, out0)
        if rc != 0:
            misses.append(f"기준 상태에서 {gate} 가 이미 미달이다 — 표본이 잘못되었다")

    for label, breaker, gate in CASES:
        ws = base / f"case-{abs(hash(label))}"
        shutil.copytree(ws0, ws)
        breaker(ws)
        rc, output = check(gate, ws, out0)
        caught = rc != 0
        print(f"  [{'잡음' if caught else '놓침'}] {label}")
        if not caught:
            misses.append(f"{label} — {gate} 가 통과시켜 버렸다")
        else:
            first = next((l.strip() for l in output.splitlines() if l.strip().startswith("-")), "")
            if first:
                print(f"            {first[:110]}")

    shutil.rmtree(base, ignore_errors=True)
    print("\n" + "=" * 60)
    if misses:
        print(f"역방향 점검 실패 {len(misses)}건:")
        for m in misses:
            print(f"  - {m}")
        return 1
    print(f"역방향 점검 통과: 주입한 위반 {len(CASES)}건을 모두 잡아냈다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
