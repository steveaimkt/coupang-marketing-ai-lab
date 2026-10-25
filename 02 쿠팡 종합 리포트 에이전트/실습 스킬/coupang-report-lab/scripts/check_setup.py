"""
2부 실습 설치 점검 · 이 실습에 필요한 것을 한 번에 보고, 없으면 설치한다.

  python3 .claude/skills/coupang-report-lab/scripts/check_setup.py                    점검표와 설치 명령
  python3 .claude/skills/coupang-report-lab/scripts/check_setup.py --install          없는 부품 설치 뒤 다시 점검
  python3 .claude/skills/coupang-report-lab/scripts/check_setup.py --os windows --plan 윈도우 파워셸 명령만 보여 준다 (시험용 · 설치하지 않음)

윈도우 파워셸에서는 맨 앞 python3 를 py (없으면 python) 로 바꿔 친다.

운영체제를 보고 설치 명령을 만든다 (맥은 터미널 zsh, 윈도우는 파워셸).
  파이썬 부품   맥 python3 -m pip install -r requirements.txt · 윈도우 py -m pip install -r requirements.txt
  python 자체   맥 brew install python (Homebrew 가 없으면 Homebrew 설치 한 줄 · 비밀번호는 수강생이 터미널 앱에서 직접)
                윈도우 winget install -e --id Python.Python.3.12
설치 순서 · ① 지금 python3 에 requirements.txt 그대로 → ② 막히면 버전 고정 없이 →
③ 그래도 막히면 작업 폴더 안 .venv 를 만들어 그 안에 설치 (맥 .venv/bin/python · 윈도우 .venv\\Scripts\\python).
.venv 를 쓰게 되면 마지막 줄에 알린다.
python 이 3.9 보다 낮으면 python 설치 명령을 보여 주고 멈춘다. python 이 아예 없으면 이 도구가 돌지 않는다.
그때는 SKILL.md Step 0 의 「python 이 없을 때」 를 따른다.
표준 라이브러리만 쓴다. 이어서 돌아왔을 때 몇 번이고 다시 돌려도 된다.
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]

# (가져오는 이름, 설치 이름, 어디에 쓰나)
PARTS = [
    ("pandas", "pandas", "엑셀 읽기 · 계산"),
    ("numpy", "numpy", "계산"),
    ("openpyxl", "openpyxl", ".xlsx 읽기"),
    ("plotly", "plotly", "리포트 차트"),
    ("kaleido", "kaleido", "노션에 넣을 차트 그림"),
    ("notion_client", "notion-client", "노션 발행 (Step 6)"),
    ("requests", "requests", "노션 파일 올리기 (Step 6)"),
]
MIN_PY = (3, 9)
BREW_INSTALL = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
WINGET_PY = "winget install -e --id Python.Python.3.12"
OS_NAME = {"mac": "맥 · 터미널", "windows": "윈도우 · 파워셸"}


def detect_os():
    return "windows" if os.name == "nt" else "mac"


def py_word(osname):
    """수강생 화면에 적는 파이썬 명령 이름."""
    if osname != "windows":
        return "python3"
    if os.name == "nt" and not shutil.which("py") and shutil.which("python"):
        return "python"
    return "py"


def venv_word(osname):
    return r".venv\Scripts\python" if osname == "windows" else ".venv/bin/python"


def has_brew():
    return bool(shutil.which("brew") or Path("/opt/homebrew/bin/brew").exists() or Path("/usr/local/bin/brew").exists())


def python_plan(osname, brew):
    """python 자체를 설치하는 명령 (무엇, 명령, 메모)."""
    if osname == "windows":
        return [("python", WINGET_PY, "winget 이 없으면 마이크로소프트 스토어에서 「앱 설치 관리자」 를 먼저 설치한다 · 설치 뒤 Code 탭에서 새 세션")]
    if brew:
        return [("python", "brew install python", "설치 뒤 Code 탭에서 새 세션을 연다")]
    return [("Homebrew", BREW_INSTALL, "수강생이 터미널 앱에서 직접 친다 · 맥 로그인 비밀번호를 묻는다"),
            ("python", "brew install python", "Homebrew 설치가 끝난 뒤 · 설치 뒤 Code 탭에서 새 세션")]


def parts_plan(osname):
    py = py_word(osname)
    return [("파이썬 부품", f"{py} -m pip install -r requirements.txt",
             f"막히면 {py} -m venv .venv 를 만들고 {venv_word(osname)} -m pip install -r requirements.txt")]


def show_plan(osname, items):
    if not items:
        return
    print()
    print(f"설치 명령 ({OS_NAME[osname]})")
    for what, cmd, note in items:
        print(f"  {what}  ·  {cmd}")
        if note:
            print(f"      {note}")


def default_root():
    if LAB.parent.name == "skills" and LAB.parents[1].name == ".claude":
        return LAB.parents[2]
    return Path.cwd()


def venv_python(root):
    win = root / ".venv/Scripts/python.exe"
    return win if win.exists() else root / ".venv/bin/python"


def probe(python):
    """그 파이썬에서 부품마다 버전을 읽는다. 없으면 None."""
    code = (
        "import importlib, importlib.metadata as md, json\n"
        f"pairs = {[(p[0], p[1]) for p in PARTS]!r}\n"
        "out = {}\n"
        "for n, d in pairs:\n"
        "    try:\n"
        "        m = importlib.import_module(n)\n"
        "        try:\n"
        "            out[n] = md.version(d)\n"
        "        except Exception:\n"
        "            out[n] = getattr(m, '__version__', '버전 모름')\n"
        "    except Exception:\n"
        "        out[n] = None\n"
        "print(json.dumps(out))\n"
    )
    import json
    try:
        r = subprocess.run([str(python), "-c", code], capture_output=True, text=True, timeout=120)
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {p[0]: None for p in PARTS}


def find_chrome():
    cands = []
    if sys.platform == "darwin":
        cands = ["/Applications/Google Chrome.app", str(Path.home() / "Applications/Google Chrome.app")]
    elif os.name == "nt":
        for base in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")):
            if base:
                cands.append(str(Path(base) / "Google/Chrome/Application/chrome.exe"))
    found = [c for c in cands if Path(c).exists()]
    if found:
        return found[0]
    return next((shutil.which(n) for n in ("google-chrome", "chromium", "chrome") if shutil.which(n)), None)


def env_state(root):
    env = root / ".env"
    if not env.exists():
        return "나중에 · 선택"
    keys = {}
    for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            keys[k.strip()] = bool(v.strip())
    have = [k for k in ("NOTION_API_KEY", "NOTION_PAGE_ID", "SLACK_WEBHOOK_URL", "DISCORD_WEBHOOK_URL") if keys.get(k)]
    return ("있음 · " + " · ".join(have)) if have else "나중에 · 선택 (값이 비어 있음)"


def table(python, root):
    """한 줄에 하나 · 「있음 · 버전」 / 「없음」. 맨 앞 두 글자로 줄을 맞춘다."""
    ver = probe(python)
    pyver = platform.python_version() if python == Path(sys.executable) else f"{platform.python_version()} · .venv"
    rows = [("있음", f"python3 {pyver}", "실행")]
    missing = []
    for mod, pkg, use in PARTS:
        v = ver.get(mod)
        rows.append(("있음", f"{pkg} {v}", use) if v else ("없음", pkg, use))
        if not v:
            missing.append(pkg)
    rows.append(("있음", "로컬 웹 서버 (파이썬 내장 http.server)", "리포트를 http://localhost 로 보기 · 설치 없음"))
    rows.append(("있음", "크롬 브라우저", "리포트 열어 보기 · 노션 차트 그림") if find_chrome()
                else ("선택", "크롬 브라우저 없음", "없어도 리포트는 나온다 · 노션 차트 그림만 빠진다"))
    env = env_state(root)
    rows.append(("나중", "노션 키 · 웹훅 (.env) " + env, "Step 6 노션 · Step 7 메신저 · 설치가 아니라 직접 넣는다"))
    print("설치 점검표")
    for mark, what, use in rows:
        print(f"  {mark}  {what}  ·  {use}")
    return missing


def pip_install(python, args):
    r = subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "-q", *args],
                       capture_output=True, text=True)
    return r.returncode == 0, (r.stderr or r.stdout).strip().splitlines()[-3:]


def install(root):
    req = root / "requirements.txt"
    if not req.exists():
        req = LAB / "assets/workspace/requirements.txt"
    loose = [p[1] for p in PARTS]
    py = Path(sys.executable)
    tries = [("지금 python3 · requirements.txt 그대로", py, ["-r", str(req)]),
             ("지금 python3 · 버전 고정 없이", py, loose)]
    for label, python, args in tries:
        ok, tail = pip_install(python, args)
        print(f"  설치 시도 · {label} · {'됨' if ok else '막힘'}")
        if ok:
            return python
    vpy = venv_python(root)
    if not vpy.exists():
        print("  작업 폴더 안에 .venv 를 만듭니다")
        r = subprocess.run([sys.executable, "-m", "venv", str(root / ".venv")], capture_output=True, text=True)
        if r.returncode != 0:
            print("  .venv 를 만들지 못했습니다:", (r.stderr or "").strip().splitlines()[-1:] or "")
            return None
        vpy = venv_python(root)
    for label, args in (("requirements.txt 그대로", ["-r", str(req)]), ("버전 고정 없이", loose)):
        ok, tail = pip_install(vpy, args)
        print(f"  설치 시도 · .venv · {label} · {'됨' if ok else '막힘'}")
        if ok:
            return vpy
    print("  설치가 막혔습니다. 마지막 메시지:")
    for t in tail:
        print("   ", t)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--install", action="store_true", help="없는 부품을 설치한 뒤 다시 점검한다")
    ap.add_argument("--workspace", help="작업 폴더 (기본: 이 스킬이 풀린 폴더의 두 칸 위)")
    ap.add_argument("--os", choices=("auto", "mac", "windows"), default="auto", help="설치 명령을 만들 운영체제 (기본 auto · 시험용으로 바꿀 수 있다)")
    ap.add_argument("--plan", action="store_true", help="지금 상태와 상관없이 모든 설치 명령만 보여 준다 (설치하지 않는다)")
    args = ap.parse_args()
    root = Path(args.workspace).resolve() if args.workspace else default_root()
    real = detect_os()
    osname = real if args.os == "auto" else args.os
    brew = has_brew() if osname == "mac" else False

    if args.plan:
        if args.install:
            ap.error("--plan 은 명령만 보여 줍니다. --install 과 함께 쓰지 않습니다.")
        print(f"설치 명령 전체 · {OS_NAME[osname]} · 시험용 (설치하지 않습니다)")
        show_plan(osname, python_plan(osname, brew) + parts_plan(osname))
        sys.exit(0)
    if args.install and osname != real:
        ap.error("--os 는 명령 문자열을 시험할 때만 바꿉니다. --install 은 이 컴퓨터 운영체제로만 돕니다.")

    if sys.version_info < MIN_PY:
        print(f"python3 · {platform.python_version()} · 3.9 이상이 필요합니다.")
        show_plan(osname, python_plan(osname, brew))
        print("이 명령으로 새 python 을 설치한 뒤 Code 탭에서 새 세션을 열고 이 점검을 다시 돌립니다.")
        sys.exit(2)

    vpy = venv_python(root)
    python = vpy if vpy.exists() else Path(sys.executable)
    print(f"운영체제 · {OS_NAME[osname]}")
    missing = table(python, root)

    if missing and args.install:
        print()
        print("없는 부품을 설치합니다: " + " · ".join(missing))
        got = install(root)
        print()
        if got:
            python = got
            missing = table(python, root)

    if missing:
        show_plan(osname, parts_plan(osname))
    print()
    if missing:
        print("없음 · " + " · ".join(missing))
        print("없는 부품이 있습니다. --install 을 붙여 돌리면 위 명령으로 설치합니다." if not args.install
              else "설치하지 못했습니다. 위 메시지를 붙여 넣고 「이게 안 되는데 왜 그런지 찾아줘」 라고 해 주세요.")
        sys.exit(1)
    if python != Path(sys.executable):
        print(f"이 폴더는 .venv 를 씁니다. 이 뒤 명령은 {py_word(osname)} 대신 {venv_word(osname)} 으로 실행합니다.")
    print("모두 있음 · 부품 준비됨")


if __name__ == "__main__":
    main()
