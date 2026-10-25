"""Step 0 · 작업 폴더에 실습 폴더를 만들고 샘플 자료를 넣는다.

  python3 .claude/skills/coupang-ad-lab/scripts/make_folders.py --workspace . [--no-samples] [--dry]

만드는 것
  데이터/2026-10-20/   샘플 1회차 (스킬 안 assets/samples/2026-10-20/ 에서 복사)
  보관/2026-11-09/     샘플 2회차 (3회 구동 2회차에 데이터/ 로 옮긴다)
  결과물/              분석기를 만들 때마다 날짜_시각 폴더가 쌓인다

--no-samples  샘플 없이 폴더만 만든다 (내 자료로 할 때). 데이터/ · 보관/ · 결과물/ 만 생긴다.
--dry         만들지 않고 만들 모양만 보여 준다.

이미 있는 폴더와 파일은 덮어쓰지 않는다. 몇 번 돌려도 같다.
"""
import argparse
import shutil
import sys
import unicodedata
from pathlib import Path

SAMPLES = (('데이터', '2026-10-20'), ('보관', '2026-11-09'))
NOTE = {
    '데이터': '원본 · 읽기만',
    '보관': '2회차 샘플 · 3회 구동 때 데이터/ 로 옮긴다',
    '결과물': '만들 때마다 날짜_시각 폴더가 쌓인다',
}


def width_of(text):
    return sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--workspace', type=Path, default=Path('.'))
    ap.add_argument('--no-samples', action='store_true', help='샘플 없이 폴더만 만든다')
    ap.add_argument('--dry', action='store_true', help='만들지 않고 모양만 보여 준다')
    args = ap.parse_args()

    workspace = args.workspace.resolve()
    lab = Path(__file__).resolve().parents[1]
    if lab.parent.name != 'skills' or lab.parent.parent.name != '.claude':
        sys.exit(f'실습 스킬이 .claude/skills/ 안에 있어야 합니다. 지금 자리: {lab}')

    made, kept = [], []

    def ensure_dir(path):
        if path.exists():
            kept.append(path)
        else:
            made.append(path)
            if not args.dry:
                path.mkdir(parents=True)

    for top in ('데이터', '보관', '결과물'):
        ensure_dir(workspace / top)

    if not args.no_samples:
        for top, day in SAMPLES:
            src_dir = lab / 'assets/samples' / day
            files = sorted(p for p in src_dir.glob('*.xlsx') if not p.name.startswith(('~$', '.')))
            if not files:
                sys.exit(f'샘플 자료가 없습니다: {src_dir}')
            ensure_dir(workspace / top / day)
            for src in files:
                dest = workspace / top / day / src.name
                if dest.exists():
                    kept.append(dest)
                else:
                    made.append(dest)
                    if not args.dry:
                        shutil.copy2(src, dest)

    # 모양 보여 주기
    print(f'{workspace.name}/')
    rows = []
    for top in ('데이터', '보관', '결과물'):
        sub = [day for t, day in SAMPLES if t == top and not args.no_samples]
        label = f'{top}/' + (f'{sub[0]}/' if sub else '')
        note = NOTE[top]
        if top == '데이터':
            note += ' · 샘플 1회차 파일' if not args.no_samples else ' · 날짜 폴더를 만들어 받은 파일을 넣는다'
        if top == '보관' and args.no_samples:
            note = '지난 자료나 남는 파일을 옮겨 두는 곳'
        rows.append((label, note))
    rows.append(('.claude/skills/', '실습 스킬'))
    width = max(width_of(r[0]) for r in rows) + 3
    for i, (label, note) in enumerate(rows):
        branch = '└──' if i == len(rows) - 1 else '├──'
        print(f'{branch} {label}{" " * (width - width_of(label))}{note}')
    print()
    word = '만들 것' if args.dry else '새로 만든 것'
    print(f'{word} {len(made)}개 · 이미 있어서 그대로 둔 것 {len(kept)}개')
    for p in made:
        print(f'  + {p.relative_to(workspace)}')
    for p in kept:
        print(f'  = {p.relative_to(workspace)} (그대로 둠)')
    if args.no_samples and not args.dry:
        print('데이터/ 안에 리포트 마지막 날짜로 폴더(예 2026-10-25)를 만들고 받은 파일을 이름 그대로 넣으세요.')


if __name__ == '__main__':
    main()
