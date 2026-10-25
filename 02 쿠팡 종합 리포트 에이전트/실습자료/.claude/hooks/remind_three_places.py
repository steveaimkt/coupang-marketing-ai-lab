#!/usr/bin/env python3
"""PostToolUse(Edit|Write): output/*.html 을 고쳤으면 나머지 2곳도 고치라고 알린다.

CLAUDE.md / SKILL.md 의 "수정 시 3곳 동시" 규칙:
  ① 로컬 HTML  ② Notion 페이지 블록  ③ Notion 다운로드 첨부 파일
①만 고치고 끝내는 것이 이 에이전트의 대표적 실수라 컨텍스트로 되짚어준다.

차단하지 않는다. 알림 전용.
"""
import json
import sys
from pathlib import Path


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    ti = payload.get("tool_input") or {}
    tr = payload.get("tool_response") or {}
    path = tr.get("filePath") or ti.get("file_path") or ""
    if not path:
        sys.exit(0)

    p = Path(path)
    if p.suffix.lower() != ".html" or "output" not in p.parts:
        sys.exit(0)

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                f"[3곳 동시 수정 규칙] 방금 {p.name} (로컬 HTML)을 수정했습니다. "
                f"리포트가 이미 Notion에 배포된 상태라면 나머지 2곳도 같은 내용으로 고쳐야 합니다: "
                f"② Notion 페이지의 해당 블록 (테이블 열 수 변경 시 기존 삭제 후 재생성), "
                f"③ Notion 페이지 상단의 HTML 다운로드 첨부 파일 (기존 file 블록 삭제 → 새 파일 업로드). "
                f"아직 배포 전이면 무시하세요."
            ),
        }
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
