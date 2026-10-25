"""Step 2 · 작업 폴더에 CLAUDE.md 를 만든다. 분석 스킬보다 먼저 만든다.

  python3 .claude/skills/coupang-ad-lab/scripts/claude_md.py --workspace . --attribution-days 14 [--target-roas 300] [--waste 10000]

이미 있으면 덮어쓰지 않는다. 기준을 바꾸려면 CLAUDE.md 「판단 기준」 줄만 고친다.
"""
import argparse
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--workspace', type=Path, default=Path('.'))
    ap.add_argument('--attribution-days', type=int, choices=(1, 14), default=14)
    ap.add_argument('--target-roas', type=float, default=None)
    ap.add_argument('--waste', type=int, default=10000, help='낭비 기준 광고비 (원)')
    args = ap.parse_args()
    dest = args.workspace.resolve() / 'CLAUDE.md'
    if dest.exists():
        sys.exit(f'CLAUDE.md 가 이미 있습니다. 덮어쓰지 않습니다. 기준을 바꾸려면 「판단 기준」 줄만 고치세요: {dest.name}')
    lab = Path(__file__).resolve().parents[1]
    text = (lab / 'assets/claude-md.md').read_text(encoding='utf-8')
    target = 'null' if args.target_roas is None else (int(args.target_roas) if args.target_roas == int(args.target_roas) else args.target_roas)
    text = text.replace('{{DAYS}}', str(args.attribution_days)).replace('{{WASTE}}', str(args.waste)).replace('{{TARGET}}', str(target))
    dest.write_text(text, encoding='utf-8')
    print('CLAUDE.md 를 만들었습니다.')
    print(f'  판단 기준 · 전환 {args.attribution_days}일 · 낭비 {args.waste:,}원 · 효자 ROAS 300% · 목표 ROAS {target}')
    print('  분석 스킬은 아직 만들지 않았습니다.')


if __name__ == '__main__':
    main()
