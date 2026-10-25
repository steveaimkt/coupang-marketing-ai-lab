#!/usr/bin/env python3
"""PreToolUse(Bash): --force-html 로 수동 섹션이 날아가는 사고를 막는다.

워크플로우 Step 3 이후 HTML에는 사람이 손으로 넣은 마케팅 플랜/3열표가 들어 있다.
--force-html 은 그 파일을 통째로 새로 쓰므로 수동 작업이 유실된다.
대상 파일에 수동 섹션 마커가 실제로 있을 때만 차단한다 (없으면 조용히 통과).

표준 라이브러리만 사용한다. venv 없이 실행된다.
"""
import json
import os
import shlex
import sys
from pathlib import Path

# 자동 생성 HTML에는 등장하지 않는 문구만 마커로 쓴다 (오탐 방지).
MANUAL_MARKERS = ["마케팅 플랜", "제품별 매출 목표", "핵심 실행 플랜", "다음달 목표"]


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
    import re
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


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False))
    sys.exit(0)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    cmd = (payload.get("tool_input") or {}).get("command") or ""
    if "--force-html" not in cmd:
        sys.exit(0)

    try:
        tokens = shlex.split(cmd)
    except ValueError:
        sys.exit(0)

    brand = resolve_brand(opt(tokens, "--brand"), opt(tokens, "--data-dir") or opt(tokens, "-d"))
    data_dir = opt(tokens, "--data-dir") or opt(tokens, "-d")
    fname = target_filename(brand, data_dir)
    if not fname:
        sys.exit(0)

    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or ".").resolve()
    out = Path(opt(tokens, "--output-dir") or opt(tokens, "-o") or "output")
    if not out.is_absolute():
        out = root / out
    target = out / fname

    if not target.exists():
        sys.exit(0)

    try:
        html = target.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        sys.exit(0)

    found = [m for m in MANUAL_MARKERS if m in html]
    if not found:
        sys.exit(0)

    deny(
        f"차단: {target.name} 에 수동 섹션이 이미 있습니다 (감지: {', '.join(found)}).\n"
        f"--force-html 로 재생성하면 이 섹션들이 전부 사라집니다.\n\n"
        f"의도한 것이라면 → 사용자에게 먼저 확인받고, 승인 시 이 훅을 우회할 방법을 안내하세요.\n"
        f"Notion 배포만 원한다면 → --force-html 를 빼고 --notion 만 쓰세요 (기존 HTML 보호)."
    )


if __name__ == "__main__":
    main()
