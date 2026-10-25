#!/usr/bin/env python3
"""PreToolUse(Bash|Write): 사람이 손본 리포트가 덮어써지는 사고를 막는다.

리포트는 만들 때마다 결과물/{자료 날짜}_{HHMM}/ 새 폴더에 들어가므로 생성기는 덮어쓰지 않는다.
남은 위험은 두 가지다.
  1. Bash · generate_report.py --notion --force-html
     가장 최근 리포트(사람이 넣은 마케팅 플랜 · 3열표가 든 것) 대신 새 자동 리포트를 노션에 올린다.
     노션의 같은 제목 페이지는 아카이브되므로, 노션에서 사람이 손본 섹션이 사라진다.
  2. Write · 결과물/ 안의 리포트 HTML 을 통째로 다시 쓴다.
     고칠 때는 Edit 로 그 자리만 고친다 (Step 5 수정 대응).
대상 리포트에 수동 섹션 마커가 실제로 있을 때만 차단한다 (없으면 조용히 통과).

표준 라이브러리만 사용한다. venv 없이 실행된다.
"""
import json
import os
import re
import shlex
import sys
from pathlib import Path

# 자동 생성 HTML에는 등장하지 않는 문구만 마커로 쓴다 (오탐 방지).
MANUAL_MARKERS = ["마케팅 플랜", "제품별 매출 목표", "핵심 실행 플랜", "다음달 목표"]
RESULT_ROOTS = ("결과물", "output")


def opt(tokens, name):
    """--name VALUE 또는 --name=VALUE 에서 VALUE 추출"""
    for i, t in enumerate(tokens):
        if t == name and i + 1 < len(tokens):
            return tokens[i + 1]
        if t.startswith(name + "="):
            return t.split("=", 1)[1]
    return None


def resolve_brand(brand_arg, data_dir):
    """generate_report.resolve_brand() 와 동일 규칙"""
    if brand_arg:
        return brand_arg
    if not data_dir:
        return None
    parts = Path(data_dir).parts
    if len(parts) < 2:
        return None
    last = parts[-1]
    is_date = last.isdigit() or len(last) == 6 or re.fullmatch(r"\d{4}-\d{2}-\d{2}", last)
    return parts[-2] if is_date else last


def target_filename(brand, data_dir):
    """generate_report.main() 의 파일명 생성 규칙과 동일해야 한다."""
    if not (brand and data_dir):
        return None
    code = Path(data_dir).parts[-1]
    if len(code) == 6 and code.isdigit():
        disp = f"20{code[:2]}.{code[2:4]}.{code[4:6]}"
    elif len(code) == 8 and code.isdigit():
        disp = f"{code[:4]}.{code[4:6]}.{code[6:8]}"
    else:
        disp = code
    return f"{brand}_광고리포트_{disp}.html"


def latest_with(root, fname):
    """generate_report.latest_result_dir() 와 같은 규칙 · 그 리포트가 든 폴더 중 이름순 마지막"""
    if not root.exists():
        return None
    dirs = sorted([d for d in root.iterdir() if d.is_dir() and (d / fname).exists()], key=lambda d: d.name)
    return dirs[-1] / fname if dirs else None


def markers_in(path):
    try:
        html = Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    return [m for m in MANUAL_MARKERS if m in html]


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False))
    sys.exit(0)


def check_write(ti):
    """Write 로 결과물/ 안의 리포트 HTML 을 통째로 다시 쓰려 할 때"""
    p = Path(ti.get("file_path") or "")
    if p.suffix.lower() != ".html" or not (set(RESULT_ROOTS) & set(p.parts)) or not p.exists():
        return
    found = markers_in(p)
    if found:
        deny(
            f"차단: {p.name} 에 사람이 손본 섹션이 있습니다 (감지: {', '.join(found)}).\n"
            f"Write 로 통째로 다시 쓰면 이 섹션들이 사라질 수 있습니다.\n"
            f"고칠 곳만 Edit 로 고치세요. 새 리포트가 필요하면 generate_report.py 를 다시 돌리면 새 결과물 폴더에 만들어집니다."
        )


def check_bash(cmd):
    if "--force-html" not in cmd:
        return
    try:
        tokens = shlex.split(cmd)
    except ValueError:
        return
    if "--notion" not in tokens:
        return            # 노션에 올리지 않으면 새 폴더에 새 리포트가 생길 뿐이다

    data_dir = opt(tokens, "--data-dir") or opt(tokens, "-d")
    fname = target_filename(resolve_brand(opt(tokens, "--brand"), data_dir), data_dir)
    if not fname:
        return

    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR") or ".").resolve()
    root = Path(opt(tokens, "--output-dir") or opt(tokens, "-o") or "결과물")
    if not root.is_absolute():
        root = proj / root
    target = latest_with(root, fname)
    if not target:
        return

    found = markers_in(target)
    if not found:
        return

    deny(
        f"차단: 가장 최근 리포트 {target.parent.name}/{target.name} 에 사람이 손본 섹션이 있습니다 (감지: {', '.join(found)}).\n"
        f"--notion --force-html 은 이 리포트 대신 새 자동 리포트를 노션에 올리고, 노션의 같은 제목 페이지를 아카이브합니다.\n\n"
        f"의도한 것이라면 → 사용자에게 먼저 확인받으세요.\n"
        f"손본 리포트를 올리려면 → --force-html 를 빼고 --notion 만 쓰세요 (가장 최근 결과물의 리포트를 그대로 올립니다)."
    )


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    ti = payload.get("tool_input") or {}
    if payload.get("tool_name") == "Write" or ("file_path" in ti and "command" not in ti):
        check_write(ti)
    else:
        check_bash(ti.get("command") or "")
    sys.exit(0)


if __name__ == "__main__":
    main()
