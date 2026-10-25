"""Step 0 · 이 실습 전체에서 쓰는 설치 항목을 한 번에 점검하고, 운영체제에 맞는 설치 명령을 보여 준다.

  python3 .claude/skills/coupang-ad-lab/scripts/check_setup.py --workspace .                         점검표와 설치 명령
  python3 .claude/skills/coupang-ad-lab/scripts/check_setup.py --workspace . --install               없는 것을 설치한 뒤 다시 점검
  python3 .claude/skills/coupang-ad-lab/scripts/check_setup.py --workspace . --install --later-node  파이썬 부품만 지금 · node 는 Step 7 전에
  python3 .claude/skills/coupang-ad-lab/scripts/check_setup.py --os windows --plan                   윈도우 파워셸 명령만 보여 준다 (시험용 · 설치하지 않음)

윈도우 파워셸에서는 맨 앞 python3 를 py (없으면 python) 로 바꿔 친다.

점검하는 것
  python3                  모든 도구가 파이썬으로 돈다 (3.9 이상)                  Step 1~6 에 꼭 필요
  openpyxl · PyYAML        requirements.txt 의 파이썬 부품 (엑셀 읽기 · 설정 읽기)   Step 1~6 에 꼭 필요
  node · npm               넷리파이 CLI 를 설치하고 돌린다                          Step 7 에만 쓴다
  netlify-cli              Step 7 배포 (로그인은 Step 7 에서 한다)                  Step 7 에만 쓴다
  playwright (선택)        분석기 탭을 자동으로 눌러 보는 도구. 없어도 실습은 된다

설치 명령 (맥은 터미널 zsh, 윈도우는 파워셸)
  파이썬 부품   맥 python3 -m pip install -r requirements.txt · 윈도우 py -m pip install -r requirements.txt
                막히면 작업 폴더 안에 .venv 를 만들고 거기에 설치한다 (맥 .venv/bin/python · 윈도우 .venv\\Scripts\\python)
  python 자체   맥 brew install python · 윈도우 winget install -e --id Python.Python.3.12
  node · npm    맥 brew install node · 윈도우 winget install -e --id OpenJS.NodeJS.LTS
  netlify-cli   npm install -g netlify-cli · 막히면 설치하지 않고 npx -y netlify-cli 로 대신 쓴다
  맥에 Homebrew 가 없으면 Homebrew 설치 한 줄만 보여 준다. 비밀번호를 물으므로 수강생이 터미널 앱에서 직접 친다.
  python 이 아예 없으면 이 도구가 돌지 않는다. SKILL.md Step 0 의 「python 이 없을 때」 를 따른다.

마지막 줄
  모두 있음                                        끝 코드 0
  Step 1 진행 가능 · Step 7 전까지 설치: …          끝 코드 0 (node · npm · netlify-cli 만 없을 때)
  없는 것 N개 · …                                  끝 코드 1
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

PY_PARTS = (('openpyxl', 'openpyxl', '엑셀 읽기'), ('PyYAML', 'yaml', '설정 읽기'))
STEP7 = ('node', 'npm', 'netlify-cli')
REQ_REL = '.claude/skills/coupang-ad-lab/requirements.txt'
BREW_INSTALL = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
WINGET_PY = ['winget', 'install', '-e', '--id', 'Python.Python.3.12',
             '--accept-source-agreements', '--accept-package-agreements']
WINGET_NODE = ['winget', 'install', '-e', '--id', 'OpenJS.NodeJS.LTS',
               '--accept-source-agreements', '--accept-package-agreements']
OS_NAME = {'mac': '맥 · 터미널', 'windows': '윈도우 · 파워셸'}


def width_of(text):
    return sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in text)


def pad(text, width):
    return text + ' ' * max(0, width - width_of(text))


def run(cmd, timeout=180, env=None):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        return p.returncode, (p.stdout + p.stderr).strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError, OSError) as e:
        return 127, str(e)


def first_line(text):
    return text.splitlines()[0].strip() if text else ''


def last_line(text):
    return text.splitlines()[-1].strip() if text else ''


def detect_os():
    return 'windows' if os.name == 'nt' else 'mac'


def extra_dirs(osname):
    """설치 직후에는 PATH 에 아직 없을 수 있는 자리. 새 세션부터는 PATH 로 잡힌다."""
    if osname == 'windows':
        dirs = [Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'nodejs']
        if os.environ.get('APPDATA'):
            dirs.append(Path(os.environ['APPDATA']) / 'npm')
        return [str(d) for d in dirs]
    return ['/opt/homebrew/bin', '/usr/local/bin']


def find_tool(name, osname):
    """(경로, PATH 에 있나). PATH 에 없고 설치 자리에만 있으면 새 세션부터 바로 쓰인다."""
    path = shutil.which(name)
    if path:
        return path, True
    path = shutil.which(name, path=os.pathsep.join(extra_dirs(osname)))
    return (path, False) if path else (None, False)


def tool_env(path):
    """방금 설치해 PATH 에 없는 node 도 돌도록 그 폴더를 앞에 붙인다."""
    env = dict(os.environ)
    if path:
        env['PATH'] = str(Path(path).parent) + os.pathsep + env.get('PATH', '')
    return env


def venv_python(workspace, osname):
    return workspace / ('.venv/Scripts/python.exe' if osname == 'windows' else '.venv/bin/python')


def python_for(workspace, osname):
    """작업 폴더에 .venv 가 있으면 그것을, 없으면 지금 파이썬을 쓴다."""
    venv = venv_python(workspace, osname)
    return (str(venv), True) if venv.exists() else (sys.executable, False)


def py_word(osname):
    """수강생 화면에 적는 파이썬 명령 이름."""
    if osname != 'windows':
        return 'python3'
    if os.name == 'nt' and not shutil.which('py') and shutil.which('python'):
        return 'python'
    return 'py'


def venv_word(osname):
    return r'.venv\Scripts\python' if osname == 'windows' else '.venv/bin/python'


def py_part_version(python, module):
    code = (f"import importlib.metadata as m, importlib.util as u, sys\n"
            f"spec = u.find_spec('{module}')\n"
            f"if spec is None: sys.exit(1)\n"
            f"dist = {{'yaml': 'PyYAML'}}.get('{module}', '{module}')\n"
            f"print(m.version(dist))")
    rc, out = run([python, '-c', code], timeout=60)
    return first_line(out) if rc == 0 else None


def netlify_cmd(osname):
    path, on_path = find_tool('netlify', osname)
    if path:
        rc, out = run([path, '--version'], timeout=60, env=tool_env(find_tool('node', osname)[0]))
        if rc == 0:
            return path, first_line(out), on_path
    return None, None, False


def playwright_version(osname):
    node, _ = find_tool('node', osname)
    if not node:
        return None
    env = tool_env(node)
    rc, out = run([node, '-e', "console.log(require('playwright/package.json').version)"], timeout=60, env=env)
    if rc == 0:
        return first_line(out)
    npm, _ = find_tool('npm', osname)
    if npm:
        rc, root = run([npm, 'root', '-g'], timeout=60, env=env)
        if rc == 0:
            pkg = str(Path(first_line(root)) / 'playwright/package.json')
            rc, out = run([node, '-e', f"console.log(require({pkg!r}).version)"], timeout=60, env=env)
            if rc == 0:
                return first_line(out)
    return None


def check(workspace, osname, npx_note):
    """줄 = (이름, 상태, 있나, 종류, 쓰는 곳). 종류 · need (Step 1~6) · step7 · optional."""
    rows = []
    py, in_venv = python_for(workspace, osname)
    ok = sys.version_info >= (3, 9)
    rows.append(('python3', f'있음 · {platform.python_version()}' if ok else f'오래됨 · {platform.python_version()} (3.9 이상 필요)',
                 ok, 'need', '모든 도구가 파이썬으로 돈다'))
    for dist, module, role in PY_PARTS:
        v = py_part_version(py, module)
        where = ' · .venv' if in_venv else ''
        rows.append((dist, f'있음 · {v}{where}' if v else '없음', bool(v), 'need', role))
    later = '없음 · Step 7 전까지 설치'
    fresh = ' · 새 세션부터 바로 쓰임'
    node_path, _ = find_tool('node', osname)
    for tool, role in (('node', 'Step 7 · 넷리파이 CLI 를 돌린다'), ('npm', 'Step 7 · 넷리파이 CLI 를 설치한다')):
        path, on_path = find_tool(tool, osname)
        v = None
        if path:
            rc, out = run([path, '--version'], timeout=60, env=tool_env(node_path))
            v = first_line(out) if rc == 0 else None
        rows.append((tool, (f'있음 · {v}' + ('' if on_path else fresh)) if v else later, bool(v), 'step7', role))
    path, v, on_path = netlify_cmd(osname)
    if v:
        rows.append(('netlify-cli', f'있음 · {v.split()[0]}' + ('' if on_path else fresh), True, 'step7', 'Step 7 배포'))
    elif npx_note:
        rows.append(('netlify-cli', f'npx 로 대신 · {npx_note}', True, 'step7', 'Step 7 배포 · netlify 대신 npx -y netlify-cli 로 친다'))
    else:
        rows.append(('netlify-cli', later, False, 'step7', 'Step 7 배포'))
    pv = playwright_version(osname)
    rows.append(('playwright', f'있음 · {pv}' if pv else '없음 · 없어도 됨', True, 'optional', '선택 · 분석기 탭 자동 확인'))
    return rows, py, in_venv


def plan(osname, missing, has_brew, has_winget):
    """없는 항목마다 (무엇, 명령, 메모). missing 은 이름 목록."""
    py = py_word(osname)
    req = REQ_REL.replace('/', '\\') if osname == 'windows' else REQ_REL
    out = []
    if 'python3' in missing:
        if osname == 'windows':
            out.append(('python', ' '.join(WINGET_PY[:5]), '설치 뒤 Code 탭에서 새 세션을 연다' if has_winget
                        else 'winget 이 없다 · 마이크로소프트 스토어에서 「앱 설치 관리자」 를 먼저 설치한다'))
        elif has_brew:
            out.append(('python', 'brew install python', '설치 뒤 Code 탭에서 새 세션을 연다'))
        else:
            out.append(('Homebrew', BREW_INSTALL, '수강생이 터미널 앱에서 직접 친다 · 맥 로그인 비밀번호를 묻는다'))
            out.append(('python', 'brew install python', 'Homebrew 설치가 끝난 뒤'))
    if any(d in missing for d, _, _ in PY_PARTS):
        out.append(('파이썬 부품', f'{py} -m pip install -r {req}',
                    f'막히면 {py} -m venv .venv 를 만들고 {venv_word(osname)} -m pip install -r {req}'))
    if 'node' in missing or 'npm' in missing:
        if osname == 'windows':
            out.append(('node · npm', ' '.join(WINGET_NODE[:5]), '설치 뒤 PATH 는 새 세션부터 잡힌다' if has_winget
                        else 'winget 이 없다 · 마이크로소프트 스토어에서 「앱 설치 관리자」 를 먼저 설치한다'))
        elif has_brew:
            out.append(('node · npm', 'brew install node', '설치 뒤 PATH 는 새 세션부터 잡힌다'))
        else:
            if not any(r[0] == 'Homebrew' for r in out):
                out.append(('Homebrew', BREW_INSTALL, '수강생이 터미널 앱에서 직접 친다 · 맥 로그인 비밀번호를 묻는다'))
            out.append(('node · npm', 'brew install node', 'Homebrew 설치가 끝난 뒤'))
    if 'netlify-cli' in missing:
        note = '막히면 npx -y netlify-cli 로 대신 쓴다'
        if osname == 'windows':
            note += ' · 파워셸이 스크립트 실행을 막으면 npm.cmd 로 치거나, 승인 뒤 Set-ExecutionPolicy -Scope CurrentUser RemoteSigned'
        out.append(('netlify-cli', 'npm install -g netlify-cli', note))
    return out


def show_plan(osname, items):
    if not items:
        return
    print()
    print(f'설치 명령 ({OS_NAME[osname]})')
    w = max(width_of(i[0]) for i in items) + 3
    for what, cmd, note in items:
        print('  ' + pad(what, w) + cmd)
        if note:
            print('  ' + pad('', w) + '· ' + note)


def show(rows, in_venv, osname, has_brew, has_winget, stop=()):
    w1 = max(width_of(r[0]) for r in rows) + 3
    w2 = max(width_of(r[1]) for r in rows) + 3
    print(pad('항목', w1) + pad('상태', w2) + '쓰는 곳')
    for name, state, ok, kind, role in rows:
        mark = '' if ok else ('  ← Step 7 전까지' if kind == 'step7' else '  ← 설치 필요')
        print(pad(name, w1) + pad(state, w2) + role + mark)
    need = [r[0] for r in rows if not r[2] and r[3] == 'need']
    later = [r[0] for r in rows if not r[2] and r[3] == 'step7']
    print()
    py = py_word(osname)
    if in_venv:
        print(f'파이썬 명령: {venv_word(osname)} (작업 폴더 안 .venv 를 씁니다. 이후 {py} 대신 이 명령을 씁니다)')
    else:
        print(f'파이썬 명령: {py}')
    netlify = next(r for r in rows if r[0] == 'netlify-cli')
    if netlify[1].startswith('npx'):
        print('넷리파이 명령: npx -y netlify-cli')
    elif netlify[2]:
        print('넷리파이 명령: netlify' + (' (파워셸이 막으면 netlify.cmd)' if osname == 'windows' else ''))
    show_plan(osname, plan(osname, need + later, has_brew, has_winget))
    for line in stop:
        print('멈춤 · ' + line)
    print()
    if need:
        print(f'없는 것 {len(need + later)}개 · ' + ' · '.join(need + later))
    elif later:
        print('Step 1 진행 가능 · Step 7 전까지 설치: ' + ' · '.join(later))
    else:
        print('모두 있음')
    return need, later


def install(workspace, rows, osname, has_brew, has_winget, later_node):
    by = {r[0]: r for r in rows}
    stop = []
    if not by['python3'][2]:
        cmd = ' '.join(WINGET_PY[:5]) if osname == 'windows' else 'brew install python'
        stop.append(f'python3 가 오래됐습니다. 새 버전을 설치한 뒤 Code 탭에서 새 세션을 열어 주세요: {cmd}')

    lab = Path(__file__).resolve().parents[1]
    req = lab / 'requirements.txt'
    npx_note = None
    if any(not by[d][2] for d, _, _ in PY_PARTS):
        py, in_venv = python_for(workspace, osname)
        print(f'파이썬 부품 설치 · {py_word(osname)} -m pip install -r requirements.txt')
        rc, out = run([py, '-m', 'pip', 'install', '-q', '-r', str(req)], timeout=600)
        if rc != 0 and not in_venv:
            print('  막혔습니다. 작업 폴더 안에 .venv 를 만들어 거기에 설치합니다.')
            print('  ' + last_line(out))
            rc, out = run([sys.executable, '-m', 'venv', str(workspace / '.venv')], timeout=300)
            if rc == 0:
                rc, out = run([str(venv_python(workspace, osname)), '-m', 'pip', 'install', '-q', '-r', str(req)], timeout=600)
        print('  설치함' if rc == 0 else '  설치하지 못했습니다 · ' + last_line(out))

    step7_missing = [t for t in STEP7 if not by[t][2]]
    if step7_missing and later_node:
        print('node · npm · netlify-cli 는 지금 설치하지 않습니다. Step 7 전까지 설치합니다.')
        return stop, npx_note

    if not (by['node'][2] and by['npm'][2]):
        if osname == 'windows':
            if has_winget:
                print('node 설치 · ' + ' '.join(WINGET_NODE))
                rc, out = run(WINGET_NODE, timeout=1800)
                print('  설치함 · PATH 는 새 세션부터 잡힙니다' if rc == 0 else '  설치하지 못했습니다 · ' + last_line(out))
            else:
                stop.append('winget 이 없습니다. 마이크로소프트 스토어에서 「앱 설치 관리자」 를 설치한 뒤 다시 점검합니다')
        elif has_brew:
            print('node 설치 · brew install node')
            rc, out = run(['brew', 'install', 'node'], timeout=1800)
            print('  설치함 · PATH 는 새 세션부터 잡힙니다' if rc == 0 else '  설치하지 못했습니다 · ' + last_line(out))
        else:
            stop.append('Homebrew 가 없어 node 를 설치하지 못했습니다. 터미널 앱을 열고 Homebrew 설치 한 줄을 직접 친 뒤 (비밀번호는 거기서 직접) '
                        'Code 탭에서 새 세션을 열고 다시 점검합니다')

    npm, _ = find_tool('npm', osname)
    if not by['netlify-cli'][2] and npm:
        print('netlify-cli 설치 · npm install -g netlify-cli')
        env = tool_env(find_tool('node', osname)[0])
        rc, out = run([npm, 'install', '-g', 'netlify-cli'], timeout=900, env=env)
        if rc == 0 and netlify_cmd(osname)[1]:
            print('  설치함')
        else:
            print('  막혔습니다. 설치하지 않고 npx -y netlify-cli 로 대신 씁니다.')
            print('  ' + last_line(out))
            npx, _ = find_tool('npx', osname)
            rc, out = run([npx or 'npx', '-y', 'netlify-cli', '--version'], timeout=900, env=env)
            if rc == 0:
                lines = [l for l in out.splitlines() if l.startswith('netlify-cli/')]
                npx_note = lines[-1].split()[0].split('/')[1] if lines else '확인함'
                print(f'  npx 로 돌아갑니다 · {npx_note}')
            else:
                print('  npx 로도 돌지 않습니다 · ' + last_line(out))
    return stop, npx_note


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--workspace', type=Path, default=Path('.'))
    ap.add_argument('--install', action='store_true', help='없는 것을 설치한 뒤 다시 점검한다')
    ap.add_argument('--later-node', action='store_true', help='--install 때 node · npm · netlify-cli 는 건너뛴다 (Step 7 전에 설치)')
    ap.add_argument('--npx', action='store_true', help='netlify-cli 를 npx 로 대신 쓰기로 했다 (점검표에 반영)')
    ap.add_argument('--os', choices=('auto', 'mac', 'windows'), default='auto', help='설치 명령을 만들 운영체제 (기본 auto · 시험용으로 바꿀 수 있다)')
    ap.add_argument('--plan', action='store_true', help='지금 상태와 상관없이 모든 설치 명령만 보여 준다 (설치하지 않는다)')
    args = ap.parse_args()
    workspace = args.workspace.resolve()
    real = detect_os()
    osname = real if args.os == 'auto' else args.os
    has_brew = bool(shutil.which('brew') or find_tool('brew', 'mac')[0]) if osname == 'mac' else False
    has_winget = bool(shutil.which('winget')) if osname == 'windows' else False
    if osname != real:
        has_winget = True   # 시험용 · 명령 문자열만 만든다

    if args.plan:
        if args.install:
            ap.error('--plan 은 명령만 보여 줍니다. --install 과 함께 쓰지 않습니다.')
        print(f'설치 명령 전체 · {OS_NAME[osname]} · 시험용 (설치하지 않습니다)')
        show_plan(osname, plan(osname, ['python3', 'openpyxl', 'node', 'netlify-cli'], has_brew, has_winget))
        sys.exit(0)
    if args.install and osname != real:
        ap.error('--os 는 명령 문자열을 시험할 때만 바꿉니다. --install 은 이 컴퓨터 운영체제로만 돕니다.')

    npx_note = 'npx -y netlify-cli' if args.npx else None
    rows, py, in_venv = check(workspace, osname, npx_note)
    print(f'설치 점검표 · {OS_NAME[osname]}' + (' · 설치 전' if args.install else ''))
    need, later = show(rows, in_venv, osname, has_brew, has_winget)
    todo = need + ([] if args.later_node else later)
    if not args.install or not todo:
        sys.exit(1 if need else 0)

    print()
    stop, npx_found = install(workspace, rows, osname, has_brew, has_winget, args.later_node)
    if npx_found:
        npx_note = npx_found
    print()
    rows, py, in_venv = check(workspace, osname, npx_note)
    print('설치 점검표 · 설치 후')
    need, later = show(rows, in_venv, osname, has_brew, has_winget, stop)
    sys.exit(1 if need else 0)


if __name__ == '__main__':
    main()
