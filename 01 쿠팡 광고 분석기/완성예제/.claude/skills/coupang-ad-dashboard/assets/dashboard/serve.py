"""결과물을 로컬 웹(http://localhost)으로 보여 준다. 파이썬 내장 http.server 를 쓴다. 따로 설치할 것은 없다.

  python3 .claude/skills/coupang-ad-dashboard/assets/dashboard/serve.py --workspace .                    가장 최근 결과물을 연다
  python3 .claude/skills/coupang-ad-dashboard/assets/dashboard/serve.py --workspace . --dir 2026-10-20_1405   그 폴더를 연다
  python3 .claude/skills/coupang-ad-dashboard/assets/dashboard/serve.py --workspace . --list             쌓인 폴더 목록 화면을 연다
  python3 .claude/skills/coupang-ad-dashboard/assets/dashboard/serve.py --workspace . --stop             로컬 웹을 끈다

- 작업 폴더의 `결과물/` 을 뿌리로 띄운다. http://localhost:{포트}/ 에서 쌓인 폴더 목록이 보인다.
- 포트는 8765 부터 빈 곳을 찾는다. 막혀 있으면 다음 포트로 간다.
- 이미 떠 있으면 다시 띄우지 않고 주소만 연다. 뒤에서 돌기 때문에 대화는 멈추지 않는다.
- 띄운 정보는 작업 폴더의 `.serve.json` 에 남긴다. 끌 때 이 파일을 읽는다.
- 화면이 저장되지 않게(no-store) 보내므로 다시 만든 뒤에는 새로고침만 하면 새 화면이 나온다.
"""
import argparse
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

FIRST_PORT = 8765
LAST_PORT = 8800
RESULT_NAME = re.compile(r'^(\d{4}-\d{2}-\d{2}_\d{4})(?:_(\d+))?$')
STATE = '.serve.json'


def child(port, root):
    """뒤에서 도는 서버 본체."""
    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    class NoStore(SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header('Cache-Control', 'no-store')
            super().end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', port), partial(NoStore, directory=root))
    server.serve_forever()


def result_root(workspace):
    cfg = workspace / '.claude/skills/coupang-ad-dashboard/config.md'
    rel = '결과물'
    if cfg.exists():
        m = re.search(r'^output_directory:\s*[\'"]?([^\'"\n]+?)[\'"]?\s*$', cfg.read_text(encoding='utf-8'), re.M)
        if m:
            rel = m.group(1)
    p = Path(rel)
    return p if p.is_absolute() else workspace / p


def result_folders(base):
    found = [d for d in base.iterdir() if d.is_dir() and RESULT_NAME.match(d.name)] if base.is_dir() else []
    return sorted(found, key=lambda d: (RESULT_NAME.match(d.name)[1], int(RESULT_NAME.match(d.name)[2] or 1)))


def answers(port):
    try:
        with urllib.request.urlopen(f'http://localhost:{port}/', timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False


def pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, TypeError):
        return False


def read_state(workspace):
    try:
        return json.loads((workspace / STATE).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def start(workspace, root):
    state = read_state(workspace)
    if state and state.get('root') == str(root) and pid_alive(state.get('pid')) and answers(state['port']):
        return state['port'], False
    for port in range(FIRST_PORT, LAST_PORT + 1):
        if port_free(port):
            break
    else:
        sys.exit(f'{FIRST_PORT}~{LAST_PORT} 포트가 모두 쓰이고 있습니다. 쓰지 않는 프로그램을 닫고 다시 해 주세요.')
    proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--child', str(port), str(root)],
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    for _ in range(50):
        if answers(port):
            break
        time.sleep(0.1)
    else:
        proc.terminate()
        sys.exit(f'로컬 웹을 띄우지 못했습니다 (포트 {port}). 다시 한 번 해 주세요.')
    (workspace / STATE).write_text(json.dumps({'port': port, 'pid': proc.pid, 'root': str(root)}, ensure_ascii=False),
                                   encoding='utf-8')
    return port, True


def stop(workspace):
    state = read_state(workspace)
    if not state:
        print('켜 둔 로컬 웹이 없습니다.')
        return
    if pid_alive(state.get('pid')):
        os.kill(state['pid'], signal.SIGTERM)
    (workspace / STATE).unlink(missing_ok=True)
    print(f'로컬 웹을 껐습니다 (포트 {state.get("port")}).')


def main():
    if len(sys.argv) == 4 and sys.argv[1] == '--child':
        child(int(sys.argv[2]), sys.argv[3])
        return
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--workspace', type=Path, default=Path('.'))
    ap.add_argument('--dir', help='열 결과물 폴더 이름 (예 2026-10-20_1405). 비우면 가장 최근 결과물')
    ap.add_argument('--list', action='store_true', help='쌓인 폴더 목록 화면을 연다')
    ap.add_argument('--stop', action='store_true', help='로컬 웹을 끈다')
    ap.add_argument('--no-open', action='store_true', help='브라우저를 열지 않고 주소만 알려 준다')
    args = ap.parse_args()
    workspace = args.workspace.resolve()
    if args.stop:
        stop(workspace)
        return

    root = result_root(workspace)
    if not root.is_dir():
        sys.exit('결과물/ 폴더가 없습니다. Step 0 에서 폴더를 먼저 만드세요.')
    folders = result_folders(root)
    if args.list:
        target = ''
    elif args.dir:
        if not (root / args.dir / 'index.html').exists():
            sys.exit(f'결과물/{args.dir}/index.html 이 없습니다. 있는 폴더: ' + ', '.join(d.name for d in folders))
        target = args.dir
    else:
        if not folders:
            sys.exit('결과물이 아직 없습니다. "쿠팡 광고 분석해줘" 로 분석기부터 만드세요.')
        target = folders[-1].name

    port, fresh = start(workspace, root)
    url = f'http://localhost:{port}/' + (urllib.parse.quote(target) + '/' if target else '')
    shown = f'http://localhost:{port}/' + (target + '/' if target else '')
    if not args.no_open:
        webbrowser.open(url)
    print(f'{shown} 에서 열었습니다.' if not args.no_open else f'주소: {shown}')
    print(('로컬 웹을 새로 띄웠습니다' if fresh else '이미 떠 있는 로컬 웹을 그대로 썼습니다') + f' · 포트 {port}')
    print(f'쌓인 폴더 목록: http://localhost:{port}/ · 끄려면 --stop')


if __name__ == '__main__':
    main()
