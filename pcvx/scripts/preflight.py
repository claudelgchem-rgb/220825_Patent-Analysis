#!/usr/bin/env python3
"""PCVX 0단계 — 오늘 날짜, 출력 경로, 문서 생성 도구를 실제로 확인해 env.json 에 기록한다.

규칙 1: 날짜는 학습 지식이 아니라 실행 결과만 쓴다.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import tempfile
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402


def probe_python_libs() -> dict:
    return {
        name: importlib.util.find_spec(name) is not None
        for name in ("docx", "pptx", "openpyxl")
    }


def probe_node_libs() -> dict:
    result = {}
    node = shutil.which("node")
    for pkg in ("docx", "pptxgenjs"):
        if not node:
            result[pkg] = False
            continue
        proc = subprocess.run(
            [node, "-e", f"require('{pkg}')"], capture_output=True, text=True
        )
        result[pkg] = proc.returncode == 0
    return result


def probe_render() -> tuple[bool, str]:
    """LibreOffice 가 실제로 변환에 성공하는지 직접 해 본다.

    설치되어 있다는 것과 동작한다는 것은 다르다. A10 의 시각 확인 단계가
    이 환경에서 쓸 수 있는지 여부를 여기서 확정해 둔다.
    """
    soffice = shutil.which("soffice")
    if not soffice:
        return False, "soffice 가 설치되어 있지 않다"
    if importlib.util.find_spec("docx") is None:
        return False, "python-docx 가 없어 변환 시험 파일을 만들 수 없다"
    from docx import Document

    with tempfile.TemporaryDirectory(prefix="pcvx-render-") as tmp:
        probe = Path(tmp) / "probe.docx"
        doc = Document()
        doc.add_paragraph("PCVX render probe")
        doc.save(probe)
        try:
            proc = subprocess.run(
                [soffice, "--headless",
                 f"-env:UserInstallation=file://{tmp}/profile",
                 "--convert-to", "pdf", "--outdir", tmp, str(probe)],
                capture_output=True, text=True, timeout=120,
            )
        except subprocess.TimeoutExpired:
            return False, "soffice 변환이 120초 안에 끝나지 않았다"
        if (Path(tmp) / "probe.pdf").exists():
            return True, "변환 시험 성공 — 시각 확인 단계를 쓸 수 있다"
        detail = (proc.stderr or proc.stdout).strip().splitlines()
        return False, f"soffice 변환 실패: {detail[-1] if detail else '원인 미상'}"


def pick_output_dir() -> tuple[str, str]:
    override = os.environ.get("PCVX_OUTPUT")
    if override:
        Path(override).mkdir(parents=True, exist_ok=True)
        return override, "PCVX_OUTPUT 환경변수로 지정된 경로 사용"
    try:
        common.PREFERRED_OUTPUT.mkdir(parents=True, exist_ok=True)
        probe = common.PREFERRED_OUTPUT / ".pcvx_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return str(common.PREFERRED_OUTPUT), "지시서 기본 경로 사용"
    except OSError as exc:
        common.FALLBACK_OUTPUT.mkdir(parents=True, exist_ok=True)
        return (
            str(common.FALLBACK_OUTPUT),
            f"/mnt/user-data/outputs 사용 불가({exc.__class__.__name__}) — 저장소 내 outputs/ 로 대체",
        )


def main() -> int:
    stamp = subprocess.run(
        ["date", '+%Y-%m-%d (%A) %H:%M %Z'], capture_output=True, text=True, check=True
    ).stdout.strip()
    stamp_utc = subprocess.run(
        ["date", "-u", "+%Y-%m-%d %H:%M UTC"], capture_output=True, text=True, check=True
    ).stdout.strip()

    py_libs = probe_python_libs()
    node_libs = probe_node_libs()
    skills = {
        name: Path(f"/mnt/skills/public/{name}/SKILL.md").exists()
        for name in ("docx", "pptx", "xlsx")
    }

    if all(node_libs.values()) and skills["docx"] and skills["pptx"]:
        toolchain = "node"
        reason = "docx-js 와 pptxgenjs 가 모두 동작하고 공개 스킬 문서가 있다"
    elif all(py_libs.values()):
        toolchain = "python"
        reason = "python-docx / python-pptx / openpyxl 사용 가능"
    else:
        toolchain = "python"
        missing = [k for k, v in py_libs.items() if not v]
        reason = f"필수 라이브러리 미설치: {', '.join(missing)} — pip install 후 재실행하라"

    render_ok, render_note = probe_render()
    out_dir, out_note = pick_output_dir()
    common.WORKSPACE.mkdir(parents=True, exist_ok=True)
    (Path(out_dir)).mkdir(parents=True, exist_ok=True)

    env = {
        "as_of": common.today(),
        "as_of_compact": common.today_compact(),
        "local_stamp": stamp,
        "utc_stamp": stamp_utc,
        "output_dir": out_dir,
        "output_dir_note": out_note,
        "workspace": str(common.WORKSPACE),
        "doc_toolchain": toolchain,
        "doc_toolchain_reason": reason,
        "python_libs": py_libs,
        "node_libs": node_libs,
        "public_skills": skills,
        "tools": {
            "soffice": shutil.which("soffice") is not None,
            "pdftoppm": shutil.which("pdftoppm") is not None,
            "node": shutil.which("node") is not None,
        },
        "render_available": render_ok,
        "render_note": render_note,
    }
    common.write_json(common.WORKSPACE / "env.json", env)

    print(f"[기준일: {env['as_of']} / 에이전트: preflight]")
    print(f"현지시각   : {stamp}")
    print(f"협정세계시 : {stamp_utc}")
    print(f"출력 경로  : {out_dir}  ({out_note})")
    print(f"문서 도구  : {toolchain}  ({reason})")
    print(f"python libs: {py_libs}")
    print(f"node libs  : {node_libs}")
    print(f"공개 스킬  : {skills}")
    print(f"렌더 도구  : {env['tools']}")
    print(f"시각 확인  : {'가능' if render_ok else '불가'} ({render_note})")
    if not render_ok:
        print("           -> 시각 확인 대신 inspect_outputs.py 의 실물 검사로 G7 을 판정한다.")
    print("-> pcvx/workspace/env.json 기록 완료")

    if toolchain == "python" and not all(py_libs.values()):
        print("경고: 문서 생성 라이브러리가 없다. `pip install python-docx python-pptx openpyxl` 을 먼저 실행하라.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
