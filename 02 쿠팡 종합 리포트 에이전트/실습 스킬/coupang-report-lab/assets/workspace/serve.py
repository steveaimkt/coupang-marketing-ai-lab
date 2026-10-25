"""
리포트를 로컬 웹(http://localhost)으로 보여 준다. 파이썬 내장 http.server 만 쓴다 (설치 없음).

  python3 serve.py                 결과물 목록 http://localhost:{포트}/ 를 연다 (서버가 없으면 띄운다)
  python3 serve.py --latest        가장 최근 결과물 폴더의 리포트를 연다
  python3 serve.py 결과물/2026-10-20_0608/노을뷰티_광고리포트_2026-10-20.html
  python3 serve.py --no-open       주소만 보여 준다
  python3 serve.py --stop          서버를 끈다

뿌리는 이 폴더의 결과물/ 이다. 포트는 8770 부터 빈 곳을 찾는다. 이미 떠 있으면 그 서버를 다시 쓴다.
서버 정보는 이 폴더의 .serve.json 에 둔다. 내 컴퓨터(127.0.0.1)에서만 열린다.
"""
import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE / "결과물"
STATE = HERE / ".serve.json"
FIRST_PORT = 8770
HOST = "127.0.0.1"


def _alive(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://{HOST}:{port}/", timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False


def _free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((HOST, port))
            return True
        except OSError:
            return False


def _read_state():
    try:
        st = json.loads(STATE.read_text(encoding="utf-8"))
        if Path(st.get("root", "")) == ROOT and _alive(int(st["port"])):
            return st
    except Exception:
        pass
    return None


def ensure_server() -> int:
    """떠 있으면 그 포트, 없으면 새로 띄운 포트. 못 띄우면 예외."""
    st = _read_state()
    if st:
        return int(st["port"])
    ROOT.mkdir(exist_ok=True)
    port = next((p for p in range(FIRST_PORT, FIRST_PORT + 30) if _free(p)), None)
    if port is None:
        raise RuntimeError("빈 포트를 찾지 못했습니다 (8770~8799 사용 중)")
    kw = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(ROOT))
    if os.name == "nt":
        kw["creationflags"] = 0x00000008 | 0x00000200      # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    proc = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", HOST, "--directory", str(ROOT)], **kw)
    for _ in range(50):
        if _alive(port):
            STATE.write_text(json.dumps({"port": port, "pid": proc.pid, "root": str(ROOT)}, ensure_ascii=False), encoding="utf-8")
            return port
        time.sleep(0.1)
    proc.terminate()
    raise RuntimeError("서버가 응답하지 않습니다")


def url_for(port: int, target: Path = None) -> str:
    base = f"http://localhost:{port}/"
    if target is None:
        return base
    rel = Path(target).resolve().relative_to(ROOT)
    return base + "/".join(urllib.parse.quote(p) for p in rel.parts)


def show(target: Path = None, open_browser: bool = True) -> str:
    """target(결과물 안 파일)을 로컬 웹 주소로 연다. 서버를 못 띄우면 file:// 로 대신 연다."""
    try:
        url = url_for(ensure_server(), target)
    except Exception as e:
        url = (Path(target).resolve().as_uri() if target else ROOT.resolve().as_uri())
        print(f"  로컬 웹을 띄우지 못해 파일로 엽니다 ({e})")
    print(f"  주소: {urllib.parse.unquote(url)}")
    if open_browser:
        webbrowser.open(url)
    return url


def stop():
    try:
        st = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        print("떠 있는 리포트 서버가 없습니다.")
        return
    try:
        os.kill(int(st["pid"]), signal.SIGTERM)
        print(f"리포트 서버를 껐습니다 (포트 {st['port']}).")
    except Exception:
        print("서버가 이미 꺼져 있습니다.")
    STATE.unlink(missing_ok=True)


def latest_report():
    dirs = sorted([d for d in ROOT.iterdir() if d.is_dir() and not d.name.startswith(".")], key=lambda d: d.name) if ROOT.exists() else []
    for d in reversed(dirs):
        htmls = sorted(d.glob("*.html"))
        if htmls:
            return htmls[0]
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?", help="결과물 안 리포트 html (없으면 목록)")
    ap.add_argument("--latest", action="store_true", help="가장 최근 결과물 폴더의 리포트")
    ap.add_argument("--no-open", action="store_true", help="브라우저를 열지 않고 주소만")
    ap.add_argument("--stop", action="store_true", help="서버를 끈다")
    args = ap.parse_args()
    if args.stop:
        stop()
        return
    target = None
    if args.latest:
        target = latest_report()
        if not target:
            sys.exit("결과물/ 에 리포트가 없습니다. 리포트를 먼저 만드세요.")
    elif args.target:
        target = Path(args.target)
        if not target.is_absolute():
            target = HERE / target
        if not target.exists():
            sys.exit(f"파일이 없습니다: {args.target}")
    show(target, open_browser=not args.no_open)
    print("  끄려면: python3 serve.py --stop")


if __name__ == "__main__":
    main()
