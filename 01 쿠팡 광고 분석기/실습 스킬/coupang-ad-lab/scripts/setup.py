"""S3 에서 분석 스킬 coupang-ad-dashboard 를 작업 폴더에 설치한다. 분석기는 S4 에서 만든다.

  python3 .claude/skills/coupang-ad-lab/scripts/setup.py --workspace . [--title "노을뷰티 쿠팡 광고 분석"]

CLAUDE.md 가 먼저 있어야 한다. 판단 기준은 CLAUDE.md 에서 읽는다.

읽는 자리는 「데이터/ 안 가장 최근 날짜 폴더의 매출 성장 광고 보고서」다. 파일 이름은 받은 그대로 둔다.
"""
import argparse
from pathlib import Path
import re
import shutil
import yaml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--input', default='데이터/*/*pa_daily_keyword*.xlsx')
    parser.add_argument('--attribution-days', type=int, choices=(1, 14), default=14)
    parser.add_argument('--target-roas', type=float, default=None)
    parser.add_argument('--waste', type=int, default=None, help='낭비 기준 광고비 (원)')
    parser.add_argument('--title', default=None, help='분석기 제목')
    parser.add_argument('--sheet')
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    lab = Path(__file__).resolve().parents[1]
    import importlib.util
    spec = importlib.util.spec_from_file_location('verify', lab / 'assets/dashboard/verify.py')
    verify = importlib.util.module_from_spec(spec); spec.loader.exec_module(verify)
    try:
        source = verify.resolve_input(workspace, args.input)
    except (FileNotFoundError, ValueError) as e:
        parser.error(str(e))
    if source.suffix.lower() not in ('.xlsx', '.csv'):
        parser.error(f'xlsx 또는 csv 파일이어야 합니다: {source.name}')
    if args.target_roas is not None and args.target_roas < 0:
        parser.error('목표 ROAS 는 0 이상이거나 비워 두어야 합니다.')

    if not (workspace / 'CLAUDE.md').exists():
        parser.error('CLAUDE.md 가 없습니다. 기준을 먼저 잡아야 합니다: scripts/claude_md.py')
    dest = workspace / '.claude/skills/coupang-ad-dashboard'
    if dest.exists():
        parser.error(f'분석 스킬이 이미 있습니다. 덮어쓰지 않습니다. config.md 만 고쳐 다시 돌리세요: {dest}')

    config = {}
    for block in re.findall(r'```yaml\n(.*?)```', (lab / 'assets/analyzer-config.md').read_text(encoding='utf-8'), re.S):
        config.update(yaml.safe_load(block))
    config.update(input_file=args.input, file_type=source.suffix[1:].lower(),
                  attribution_days=args.attribution_days, target_roas_pct=args.target_roas,
                  sheet_name=args.sheet)
    if args.waste is not None:
        config['waste_cost_krw'] = args.waste
    if args.title:
        config['dashboard_title'] = args.title

    dest.mkdir(parents=True)
    shutil.copy2(lab / 'assets/analyzer-skill.md', dest / 'SKILL.md')
    shutil.copy2(lab / 'assets/analyzer-reference.md', dest / 'reference.md')
    shutil.copytree(lab / 'assets/dashboard', dest / 'assets/dashboard')
    (dest / 'config.md').write_text(
        '# 쿠팡 광고 분석 설정\n\n상대 경로는 작업 폴더 기준입니다. 말로 바꾸면 클로드 코드가 이 값을 고칩니다.\n\n```yaml\n'
        + yaml.safe_dump(config, allow_unicode=True, sort_keys=False) + '```\n', encoding='utf-8')
    print(f'분석 스킬을 만들었습니다: {dest}')
    print('  SKILL.md · config.md · reference.md · assets/dashboard/')
    print(f'지금 읽을 파일: {source.relative_to(workspace)}')
    print('분석기는 아직 만들지 않았습니다.')


if __name__ == '__main__':
    main()
