#!/usr/bin/env python3
"""PreToolUse(Bash): 내부 자료가 외부로 나가는 명령을 차단한다.

CLAUDE.md 규칙 · "내부 자료: GitHub 등 외부 업로드 금지".
보호 대상: .env (노션 키 · 웹훅), config.json, 리포트 자료/ (브랜드 원본 데이터), 결과물/ (리포트 결과물), output/ (옛 산출물 자리).

전송 동사 + 보호 대상이 같은 명령에 함께 있을 때만 차단한다.
로컬 작업(ls, cp, python 실행 등)은 영향 없다.
"""
import json
import re
import sys

# 외부로 내보내는 명령
EXFIL = [
    (r"\bgit\s+push\b", "git push"),
    (r"\bgh\s+(repo|gist|release)\b", "gh (GitHub CLI)"),
    (r"\bcurl\b.*(-T|--upload-file|-F\s|--form|-d\s|--data)", "curl 업로드"),
    (r"\bscp\b", "scp"),
    (r"\brsync\b.*::|\brsync\b.*@", "rsync (원격)"),
    (r"\baws\s+s3\b", "aws s3"),
    (r"\bgsutil\s+cp\b", "gsutil"),
    (r"\bnpx?\s+.*publish\b|\bnpm\s+publish\b", "npm publish"),
]

# 보호 대상 (git push 는 경로가 명령에 안 나타나므로 별도 처리)
SECRETS = [
    (".env", ".env (노션 키 · 웹훅 주소)"),
    ("config.json", "config.json (Notion API 키)"),
    ("리포트 자료", "리포트 자료/ (브랜드 원본 데이터)"),
    ("결과물", "결과물/ (리포트 결과물)"),
    ("output/", "output/ (옛 산출물 자리)"),
    ("credentials.json", "credentials.json"),
    ("token.json", "token.json"),
]


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
    if not cmd:
        sys.exit(0)

    verb = next((label for pat, label in EXFIL if re.search(pat, cmd)), None)
    if not verb:
        sys.exit(0)

    # git push / gh repo 는 저장소 전체가 나가므로 경로 언급 여부와 무관하게 차단
    if verb in ("git push", "gh (GitHub CLI)"):
        deny(
            f"차단: '{verb}'. 이 저장소는 외부 업로드가 금지된 내부 자료입니다 (CLAUDE.md).\n"
            f".env(노션 키 · 웹훅), 리포트 자료/, 결과물/ 이 포함될 수 있습니다.\n"
            f"정말 필요하면 사용자에게 직접 확인받으세요."
        )

    hit = [label for token, label in SECRETS if token in cmd]
    if hit:
        deny(
            f"차단: '{verb}' 명령에 내부 자료가 포함되어 있습니다: {', '.join(hit)}.\n"
            f"CLAUDE.md 규칙상 외부 전송 금지입니다. 사용자에게 직접 확인받으세요."
        )


if __name__ == "__main__":
    main()
