"""PCVX 공용 유틸 — 경로, 날짜, 금지 표현 규칙, JSON 입출력."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PCVX = REPO / "pcvx"
# PCVX_WORKSPACE / PCVX_OUTPUT 로 경로를 갈아끼울 수 있다(자체 점검·병렬 실행용).
WORKSPACE = Path(os.environ.get("PCVX_WORKSPACE") or (PCVX / "workspace"))
SCRIPTS = PCVX / "scripts"
REFERENCES = REPO / ".claude" / "skills" / "pcvx" / "references"
FALLBACK_OUTPUT = REPO / "outputs"
PREFERRED_OUTPUT = Path("/mnt/user-data/outputs")

# 규칙 3 — 금지 표현
FORBIDDEN = [
    "추후", "차후", "예정", "TBD", "tbd",
    "확인 필요", "확인필요", "미정", "생략",
    "추가 조사 필요", "작성 예정", "조사 예정", "사용자 확인 후",
]

# 지시서가 직접 요구한 정식 표현 — 금지 대상에서 제외한다.
# (RULES.md 의 허용 목록과 반드시 같아야 한다.)
ALLOWED_SPANS = [
    "존속기간 만료 예정일",
    "만료 예정일",
    "만료 예정",
    "원문 확인이 필요하다",
    "원문 확인이 필요한",
    "원문 확인이 필요",
    "전문가 검토가 필요합니다",
    "전문가 검토가 필요",
    "법률 검토를 반드시 별도로 받아야",
    "변리사·특허 전문가의 법률 검토",
    "특허 원문 및 전문가 검토",
]

GRADES = ("상", "중", "하")
GRADE_COLORS = {"상": "1E6B34", "중": "C05621", "하": "C0392B"}

SOURCE_CODES = ["GP", "ESP", "WIPO", "USPTO", "KIPRIS", "JPP", "CNIPA", "LENS"]
WINDOWS = ["최근 12개월", "최근 3년", "최근 10년", "전체 기간"]
QUERY_TYPES = {"광역": 2, "정밀": 2, "분류코드": 1, "출원인": 1}

REGISTRATION_STATUSES = {
    "등록", "출원 중(등록 미확인)", "거절", "소멸", "포기", "취하", "확보 실패",
}

FAILURE_MARK = "[확보 실패]"

# 문헌번호 표기 표준 (SOURCES.md 와 동일).
#
# 출원번호·공개번호·등록번호는 서로 다른 번호이고 형식도 다르다.
# 한 벌의 정규식으로 세 가지를 다 받으면, 출원번호 칸에 공개번호를 넣어도 통과해 버린다.
# 그래서 칸의 종류별로 따로 검사한다.
NUMBER_PATTERNS = {
    # 출원번호 — 각국 특허청이 접수 시 부여하는 번호. 공보 종별코드(A/B1/B2)가 붙지 않는다.
    "application": {
        "KR": re.compile(r"^KR\s10-\d{4}-\d{7}$"),
        "US": re.compile(r"^US\s(\d{2}/\d{3},\d{3}|\d{2}/\d{6})$"),
        "EP": re.compile(r"^EP\s\d{8}\.\d$"),
        "JP": re.compile(r"^JP\s\d{4}-\d{6}$"),
        "CN": re.compile(r"^CN\s\d{12}\.[\dX]$"),  # 끝자리는 검사숫자이며 X 가 올 수 있다
        "WO": re.compile(r"^PCT/[A-Z]{2}\d{4}/\d{6}$"),
    },
    # 공개번호 — 출원 내용이 일반에 공표될 때 붙는 번호. 종별코드 A 계열.
    "publication": {
        "KR": re.compile(r"^KR\s10-\d{4}-\d{7}\s?A$"),
        "US": re.compile(r"^US\s\d{4}/\d{7}\s?A1$"),
        "EP": re.compile(r"^EP\s\d\s?\d{3}\s?\d{3}\s?A\d$"),
        "JP": re.compile(r"^JP\s\d{4}-\d{6}\s?A$"),
        "CN": re.compile(r"^CN\s\d{9,12}\s?A$"),
        "WO": re.compile(r"^WO\s\d{4}/\d{6}\s?A\d$"),
    },
    # 등록번호 — 심사를 통과해 권리가 발생할 때 붙는 번호. 종별코드 B 계열(실용신안은 U).
    "registration": {
        "KR": re.compile(r"^KR\s(10-\d{7}\s?B[12]|20-\d{7}\s?Y[12])$"),
        "US": re.compile(r"^US\s[\d,]{7,12}\s?(B1|B2)$"),
        "EP": re.compile(r"^EP\s\d\s?\d{3}\s?\d{3}\s?B\d$"),
        "JP": re.compile(r"^JP\s\d{6,7}\s?(B[12]|U)$"),
        "CN": re.compile(r"^CN\s\d{9,12}\s?[BU]$"),
    },
}


def today() -> str:
    """실제 시스템 날짜. 학습 데이터의 날짜 감각을 쓰지 않는다."""
    return subprocess.run(
        ["date", "+%Y-%m-%d"], capture_output=True, text=True, check=True
    ).stdout.strip()


def today_compact() -> str:
    return today().replace("-", "")


def read_json(path, default=None):
    if not Path(path).exists():
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, data) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def env() -> dict:
    data = read_json(WORKSPACE / "env.json")
    if not data:
        raise SystemExit(
            "env.json 이 없다. 먼저 `python3 pcvx/scripts/preflight.py` 를 실행하라."
        )
    return data


def output_dir() -> Path:
    override = os.environ.get("PCVX_OUTPUT")
    if override:
        return Path(override)
    return Path(env()["output_dir"])


def mask_allowed(text: str) -> str:
    """허용 표현을 같은 길이의 자리표시자로 덮어 금지어 검색에서 제외한다."""
    for span in sorted(ALLOWED_SPANS, key=len, reverse=True):
        text = text.replace(span, " " * len(span))
    return text


def find_forbidden(text: str):
    """(패턴, 줄번호, 해당 줄) 목록. 허용 표현은 제외한다."""
    hits = []
    masked_lines = mask_allowed(text).splitlines()
    raw_lines = text.splitlines()
    for idx, masked in enumerate(masked_lines, start=1):
        for pattern in FORBIDDEN:
            if pattern in masked:
                hits.append((pattern, idx, raw_lines[idx - 1].strip()[:120]))
    return hits


def slugify(topic: str, limit: int = 30) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]+", "", topic).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned[:limit] or "무제"


def limits_text() -> str:
    """LIMITS.md 의 원문 블록. 한 글자도 고치지 않는다."""
    raw = (REFERENCES / "LIMITS.md").read_text(encoding="utf-8")
    body = raw.split("<!-- LIMITS:BEGIN -->")[1].split("<!-- LIMITS:END -->")[0]
    return body.strip()


def low_ratio_warning() -> str:
    return (
        "본 보고서의 상당 부분이 원문 미확인 정보에 근거하므로, "
        "의사결정에 사용하기 전 특허 원문 및 전문가 검토가 필요합니다."
    )


def cell(value, fallback: str = FAILURE_MARK) -> str:
    """빈 셀 금지 — 값이 비면 확보 실패 표기로 채운다."""
    if value is None:
        return fallback
    if isinstance(value, (list, tuple)):
        joined = ", ".join(str(v).strip() for v in value if str(v).strip())
        return joined or fallback
    text = str(value).strip()
    return text or fallback
