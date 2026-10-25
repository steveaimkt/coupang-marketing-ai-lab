"""Step 2 · 작업 폴더에 CLAUDE.md 를 만든다. 분석 스킬보다 먼저 만든다.

  python3 .claude/skills/coupang-ad-lab/scripts/claude_md.py --workspace . --attribution-days 14 \
      [--waste 10000] [--star-roas 300] [--potential-roas 100] [--min-orders 3] [--target-roas 300] [--margin 40|null]

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
    ap.add_argument('--star-roas', type=int, default=300, help='효자 기준 ROAS (%%)')
    ap.add_argument('--potential-roas', type=int, default=100, help='가능성 검토 기준 ROAS (%%)')
    ap.add_argument('--min-orders', type=int, default=3, help='효자 최소 주문 수 (건)')
    ap.add_argument('--margin', default='40', help='마진율 (%%). 모르면 40. null 이면 손익분기 판정을 하지 않는다')
    args = ap.parse_args()
    if args.waste <= 0:
        ap.error('낭비 기준은 1원 이상이어야 합니다.')
    if not args.star_roas >= args.potential_roas >= 0:
        ap.error('효자 기준은 가능성 검토 기준 이상이고, 둘 다 0 이상이어야 합니다.')
    if args.target_roas is not None and args.target_roas < 0:
        ap.error('목표 ROAS 는 0 이상이거나 비워 두어야 합니다.')
    if args.min_orders < 1:
        ap.error('효자 최소 주문 수는 1건 이상이어야 합니다.')
    if str(args.margin).lower() in ('null', 'none', '없음', ''):
        margin = None
    else:
        try:
            margin = float(args.margin)
        except ValueError:
            ap.error('마진율은 숫자(예 40)나 null 로 적습니다.')
        if not 0 < margin <= 100:
            ap.error('마진율은 0보다 크고 100 이하여야 합니다.')
        margin = int(margin) if margin == int(margin) else margin
    dest = args.workspace.resolve() / 'CLAUDE.md'
    if dest.exists():
        sys.exit(f'CLAUDE.md 가 이미 있습니다. 덮어쓰지 않습니다. 기준을 바꾸려면 「판단 기준」 줄만 고치세요: {dest.name}')
    lab = Path(__file__).resolve().parents[1]
    text = (lab / 'assets/claude-md.md').read_text(encoding='utf-8')
    target = 'null' if args.target_roas is None else (int(args.target_roas) if args.target_roas == int(args.target_roas) else args.target_roas)
    text = text.replace('{{DAYS}}', str(args.attribution_days)).replace('{{WASTE}}', str(args.waste)).replace('{{TARGET}}', str(target))
    text = text.replace('{{STAR}}', str(args.star_roas)).replace('{{POTENTIAL}}', str(args.potential_roas))
    text = text.replace('{{MINORD}}', str(args.min_orders)).replace('{{MARGIN}}', 'null' if margin is None else str(margin))
    assert '{{' not in text, '채우지 못한 자리가 있습니다'
    dest.write_text(text, encoding='utf-8')
    print('CLAUDE.md 를 만들었습니다.')
    be = '판정 안 함' if margin is None else f'{10000 / margin:.1f}%'
    print(f'  판단 기준 · 전환 {args.attribution_days}일 · 낭비 {args.waste:,}원 · 효자 ROAS {args.star_roas}% · 주문 {args.min_orders}건 이상 · '
          f'가능성 검토 ROAS {args.potential_roas}% · 목표 ROAS {target}')
    print(f'  마진율 {"null" if margin is None else str(margin) + "%"} · 손익분기 ROAS {be}')
    print('  분석 스킬은 아직 만들지 않았습니다.')


if __name__ == '__main__':
    main()
