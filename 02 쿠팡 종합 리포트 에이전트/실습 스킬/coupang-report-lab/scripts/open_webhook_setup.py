"""
Step 7 웹훅 준비 도우미 · 필요한 화면을 열어 주고, .env 에 넣은 주소가 맞는 꼴인지 본다.

  python3 .claude/skills/coupang-report-lab/scripts/open_webhook_setup.py --slack          슬랙 앱 만들기 페이지를 브라우저로 연다
  python3 .claude/skills/coupang-report-lab/scripts/open_webhook_setup.py --env            .env 가 없으면 .env.example 로 만들고 텍스트 편집기로 연다
  python3 .claude/skills/coupang-report-lab/scripts/open_webhook_setup.py --check slack    SLACK_WEBHOOK_URL 꼴 확인 (주소는 화면에 찍지 않는다)
  python3 .claude/skills/coupang-report-lab/scripts/open_webhook_setup.py --check discord
  --dry-run 을 붙이면 여는 명령만 보여 주고 열지 않는다.

디스코드는 특정 채널 설정을 밖에서 열 수 없어 순서만 안내한다 (SKILL.md Step 7).
맥은 open · open -e, 윈도우는 기본 브라우저 · notepad, 그 밖은 xdg-open 을 쓴다. 표준 라이브러리만 쓴다.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
SLACK_APPS = "https://api.slack.com/apps"
FORMS = {
    "slack": ("SLACK_WEBHOOK_URL", ("https://hooks.slack.com/services/",), "hooks.slack.com"),
    "discord": ("DISCORD_WEBHOOK_URL", ("https://discord.com/api/webhooks/", "https://discordapp.com/api/webhooks/"), "discord.com/api/webhooks"),
}


def default_root():
    if LAB.parent.name == "skills" and LAB.parents[1].name == ".claude":
        return LAB.parents[2]
    return Path.cwd()


def open_url_cmd(url):
    if sys.platform == "darwin":
        return ["open", url]
    if os.name == "nt":
        return ["cmd", "/c", "start", "", url]
    return ["xdg-open", url]


def open_text_cmd(path):
    if sys.platform == "darwin":
        return ["open", "-e", str(path)]
    if os.name == "nt":
        return ["notepad", str(path)]
    return ["xdg-open", str(path)]


def run(cmd, dry):
    print("  여는 명령: " + " ".join(f'"{c}"' if " " in c else c for c in cmd))
    if dry:
        print("  (열지 않았습니다 · --dry-run)")
        return
    try:
        subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("  열지 못했습니다. 직접 여세요.")


def make_env(root, dry):
    env, example = root / ".env", root / ".env.example"
    if env.exists():
        print(".env 가 이미 있습니다. 그대로 엽니다.")
    elif example.exists():
        if not dry:
            shutil.copy2(example, env)
        print(".env.example 을 복사해 .env 를 만들었습니다." if not dry else ".env.example 을 .env 로 복사합니다 (--dry-run 이라 만들지 않음).")
    else:
        sys.exit(".env.example 이 없습니다. Step 0 의 install.py folders 를 먼저 돌리세요.")
    return env


def check(root, kind):
    """주소 값을 찍지 않고 꼴만 본다. 0 맞음 · 1 고칠 것 있음."""
    key, prefixes, short = FORMS[kind]
    env = root / ".env"
    if not env.exists():
        print(f"없음 · .env 파일이 없습니다. --env 로 만들고 {key}= 뒤에 붙여 넣으세요.")
        return 1
    raw = None
    for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.strip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key:
            raw = v
    if raw is None:
        print(f"없음 · .env 에 {key}= 줄이 없습니다. 줄을 지우셨으면 .env.example 에서 다시 복사하세요.")
        return 1
    notes, value = [], raw
    if value != value.strip():
        notes.append("값 앞뒤에 공백이 있습니다 (보내기는 되지만 지우는 것이 안전합니다)")
        value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        notes.append("값이 따옴표로 감싸여 있습니다 (보내기는 되지만 따옴표를 지우는 것이 안전합니다)")
        value = value[1:-1].strip()
    if not value:
        print(f"비어 있음 · {key}= 뒤에 주소를 붙여 넣고 저장하세요.")
        return 1
    if " " in value or "\t" in value:
        print("고칠 것 · 주소 가운데에 공백이 있습니다. 주소를 한 줄로 다시 붙여 넣으세요.")
        return 1
    if not value.startswith(prefixes):
        other = "discord" if kind == "slack" else "slack"
        if value.startswith(FORMS[other][1]):
            print(f"고칠 것 · {'디스코드' if other == 'discord' else '슬랙'} 주소가 {key} 칸에 들어 있습니다. 맞는 칸으로 옮기세요.")
        else:
            print(f"고칠 것 · 값은 있지만 {short} 꼴이 아닙니다. {prefixes[0]} 로 시작하는 주소를 다시 복사하세요.")
        return 1
    print(f"값이 들어 있음 · {short} 꼴 맞음 · 길이 {len(value)}자")
    for n in notes:
        print("  참고 · " + n)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--slack", action="store_true", help="슬랙 앱 만들기 페이지를 연다")
    g.add_argument("--env", action="store_true", help=".env 를 만들고 텍스트 편집기로 연다")
    g.add_argument("--check", choices=["slack", "discord"], help=".env 의 주소 꼴을 확인한다")
    ap.add_argument("--dry-run", action="store_true", help="여는 명령만 보여 준다")
    ap.add_argument("--workspace", help="작업 폴더 (기본: 이 스킬이 풀린 폴더의 두 칸 위)")
    args = ap.parse_args()
    root = Path(args.workspace).resolve() if args.workspace else default_root()
    if args.slack:
        print(f"슬랙 앱 만들기 페이지를 엽니다: {SLACK_APPS}")
        run(open_url_cmd(SLACK_APPS), args.dry_run)
    elif args.env:
        env = make_env(root, args.dry_run)
        print(".env 를 텍스트 편집기로 엽니다. 주소를 붙여 넣고 저장하세요.")
        run(open_text_cmd(env), args.dry_run)
    else:
        sys.exit(check(root, args.check))


if __name__ == "__main__":
    main()
