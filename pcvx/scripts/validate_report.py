#!/usr/bin/env python3
"""보고서 본문 검사기 — 금지 표현, 약어 첫 등장 풀어쓰기, 빈 표 셀, '하' 등급 단정형.

사용법:
  python3 pcvx/scripts/validate_report.py pcvx/workspace/a9_report.md
  python3 pcvx/scripts/validate_report.py --check-abbrev <파일>
  python3 pcvx/scripts/validate_report.py --scan-outputs      # 출력 파일 전부(docx/pptx/xlsx 포함)
"""
from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

# 첫 등장 시 풀어써야 하는 약어와 그 정식 표기
ABBREVIATIONS = {
    "IPC": "국제특허분류(IPC, International Patent Classification)",
    "CPC": "협력적 특허분류(CPC, Cooperative Patent Classification)",
    "FTO": "자유실시(Freedom to Operate",
    "PCT": "특허협력조약(PCT, Patent Cooperation Treaty)",
    "WIPO": "세계지식재산기구(WIPO, World Intellectual Property Organization)",
    "USPTO": "미국 특허상표청(USPTO, United States Patent and Trademark Office)",
    "EPO": "유럽특허청(EPO, European Patent Office)",
    "KIPRIS": "특허정보넷 키프리스(KIPRIS, Korea Intellectual Property Rights Information Service)",
    "CNIPA": "중국 국가지식산권국(CNIPA, China National Intellectual Property Administration)",
    "JPO": "일본 특허청(JPO, Japan Patent Office)",
    "PTA": "특허기간조정(PTA, Patent Term Adjustment)",
    "PTE": "특허기간연장(PTE, Patent Term Extension)",
}

# '하' 등급 자리에서는 서술형 종결(~다) 자체가 단정이 된다.
# 표 안에서는 마침표를 생략하는 일이 흔하므로 칸 끝·줄 끝도 종결로 본다.
ASSERTIVE = re.compile(r"다(\.|\s*\||\s*$)")

# 아래 표현이 함께 있으면 단정이 아니라 유보로 본다(§4가 지정한 서술 방식).
HEDGES = [
    "보이나", "원문 확인이 필요", "확인하지 못", "확인되지 않", "단정할 수 없",
    "추정", "판단 불가", "얻지 못해",
]

GRADE_TAG = re.compile(r"\[(상|중|하)\]")
DOCX_TEXT = re.compile(r"<w:t[^>]*>(.*?)</w:t>", re.S)
PPTX_TEXT = re.compile(r"<a:t>(.*?)</a:t>", re.S)


def office_text(path: Path) -> str:
    """docx / pptx / xlsx 내부 텍스트를 뽑아 하나의 문자열로."""
    if path.suffix.lower() not in {".docx", ".pptx", ".xlsx"}:
        return path.read_text(encoding="utf-8", errors="replace")
    chunks: list[str] = []
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if not name.endswith(".xml"):
                continue
            blob = zf.read(name).decode("utf-8", errors="replace")
            if path.suffix.lower() == ".docx" and name.startswith("word/"):
                chunks += DOCX_TEXT.findall(blob)
            elif path.suffix.lower() == ".pptx" and name.startswith("ppt/"):
                chunks += PPTX_TEXT.findall(blob)
            elif path.suffix.lower() == ".xlsx":
                chunks += re.findall(r"<t[^>]*>(.*?)</t>", blob, re.S)
    return "\n".join(chunks)


def check_forbidden(text: str, label: str) -> list[str]:
    return [
        f"{label}:{line} 금지 표현 {pat!r} — {snippet}"
        for pat, line, snippet in common.find_forbidden(text)
    ]


def check_abbrev(text: str, label: str) -> list[str]:
    """첫 등장 시 풀어쓰기 100% + 그 뒤 약어 단독 사용 금지(문체 규칙 1)."""
    problems = []
    for abbr, expanded in ABBREVIATIONS.items():
        if not re.search(rf"\b{re.escape(abbr)}\b", text):
            continue
        first_expanded = text.find(expanded)
        # 풀어쓴 자리에 들어 있는 약어는 정상 사용이므로 가려 두고 남은 것만 본다.
        masked = text.replace(expanded, " " * len(expanded)) if first_expanded != -1 else text
        bare = list(re.finditer(rf"\b{re.escape(abbr)}\b", masked))
        if first_expanded == -1:
            problems.append(
                f"{label}: 약어 {abbr} 가 풀어쓰기 없이 쓰였다. 첫 등장 시 '{expanded}' 형태로 쓴다."
            )
            continue
        for m in bare:
            line = text[: m.start()].count("\n") + 1
            if m.start() < first_expanded:
                problems.append(
                    f"{label}:{line} 약어 {abbr} 가 풀어쓰기보다 먼저 등장한다. 첫 등장 자리에서 풀어쓴다."
                )
            else:
                problems.append(
                    f"{label}:{line} 약어 {abbr} 를 단독으로 썼다. "
                    f"'{expanded.split('(')[0]}' 처럼 우리말 이름으로 쓴다."
                )
    return problems


def check_empty_cells(text: str, label: str) -> list[str]:
    problems = []
    for idx, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue  # 구분선
        for pos, value in enumerate(cells, start=1):
            if value == "":
                problems.append(f"{label}:{idx} 표 {pos}번째 칸이 비어 있다. 빈 셀 금지.")
    return problems


def check_low_grade_assertions(text: str, label: str) -> list[str]:
    problems = []
    for idx, line in enumerate(text.splitlines(), start=1):
        if "[하]" not in line:
            continue
        if any(h in line for h in HEDGES):
            continue
        body = GRADE_TAG.sub("", line).strip()
        if ASSERTIVE.search(body):
            problems.append(
                f"{label}:{idx} '하' 등급인데 단정형으로 서술했다. "
                "'~로 보이나 원문 확인이 필요하다' 형태로 고친다 — " + line.strip()[:100]
            )
    return problems


def check_table_intro(text: str, label: str) -> list[str]:
    """모든 표 앞에 2~3문장 해설이 있어야 한다 (문체 규칙 2)."""
    problems = []
    lines = text.splitlines()
    in_table = False
    for idx, line in enumerate(lines):
        stripped = line.strip()
        is_row = stripped.startswith("|") and stripped.endswith("|")
        if is_row and not in_table:
            in_table = True
            prior = [l.strip() for l in lines[max(0, idx - 4): idx] if l.strip()]
            prose = [p for p in prior if not p.startswith(("|", "#", "-", "*", ">"))]
            sentences = sum(p.count(".") + p.count("다\n") for p in prose)
            if not prose or sentences < 2:
                problems.append(
                    f"{label}:{idx + 1} 표 앞에 읽는 법 설명이 없거나 2문장 미만이다. 표만 던져놓지 않는다."
                )
        elif not is_row:
            in_table = False
    return problems


def run_checks(text: str, label: str, only_abbrev: bool = False) -> list[str]:
    if only_abbrev:
        return check_abbrev(text, label)
    return (
        check_forbidden(text, label)
        + check_abbrev(text, label)
        + check_empty_cells(text, label)
        + check_low_grade_assertions(text, label)
        + check_table_intro(text, label)
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default=str(common.WORKSPACE / "a9_report.md"))
    ap.add_argument("--check-abbrev", action="store_true")
    ap.add_argument("--scan-outputs", action="store_true", help="출력 디렉터리의 산출물 전부 검사")
    args = ap.parse_args()

    print(f"[기준일: {common.today()} / 검사: validate_report]")
    targets: list[Path] = []
    if args.scan_outputs:
        out = common.output_dir()
        targets = sorted(
            p for p in out.glob("PCVX_*")
            if p.suffix.lower() in {".docx", ".pptx", ".xlsx", ".md"}
        )
        if not targets:
            print(f"[실패] {out} 에 PCVX_ 산출물이 없다. A10 이 먼저 파일을 만들어야 한다.")
            return 1
    else:
        path = Path(args.path)
        if not path.exists():
            print(f"[실패] {path} 가 없다.")
            return 1
        targets = [path]

    all_problems: list[str] = []
    for path in targets:
        text = office_text(path)
        problems = run_checks(text, path.name, args.check_abbrev)
        if args.scan_outputs:
            # 산출 파일에서는 금지 표현과 빈 셀만 본다(문체 검사는 본문 대상).
            problems = check_forbidden(text, path.name) + check_empty_cells(text, path.name)
        print(f"  {path.name}: {len(text)}자, 위반 {len(problems)}건")
        all_problems += problems

    if not all_problems:
        print("통과: 위반 0건")
        return 0
    print(f"\n위반 총 {len(all_problems)}건")
    for line in all_problems:
        print(f"  - {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
