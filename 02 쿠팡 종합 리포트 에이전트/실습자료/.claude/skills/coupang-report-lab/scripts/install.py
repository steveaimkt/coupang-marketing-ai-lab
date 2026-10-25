"""
2부 실습 설치 도구 · CLAUDE.md 로 기준을 먼저 잡고, 그다음 스킬과 서브에이전트를 넣는다.

  python3 .claude/skills/coupang-report-lab/scripts/install.py claude-md --brand 노을뷰티 --trend 30 --concentration 70
  python3 .claude/skills/coupang-report-lab/scripts/install.py skill-agent

순서를 바꿀 수 없다. CLAUDE.md 가 없으면 skill-agent 는 멈춘다. 이미 있는 파일은 덮어쓰지 않는다.
"""
import argparse
import shutil
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB.parents[2]          # 실습자료/


def claude_md(args):
    dest = ROOT / "CLAUDE.md"
    if dest.exists():
        sys.exit(f"CLAUDE.md 가 이미 있습니다. 덮어쓰지 않습니다. 기준을 바꾸려면 「판단 기준」 줄만 고치세요: {dest}")
    text = (LAB / "assets/CLAUDE.md").read_text(encoding="utf-8")
    text = text.replace("{{BRAND}}", args.brand).replace("{{TREND}}", str(args.trend)).replace("{{CONC}}", str(args.concentration))
    dest.write_text(text, encoding="utf-8")
    print(f"CLAUDE.md 를 만들었습니다: {dest.name}")
    print(f"  판단 기준 · 브랜드 {args.brand} · 주문 변화 {args.trend}% · 매출 편중 {args.concentration}%")
    print("  스킬과 서브에이전트는 아직 넣지 않았습니다.")


def skill_agent(_args):
    if not (ROOT / "CLAUDE.md").exists():
        sys.exit("CLAUDE.md 가 없습니다. 기준을 먼저 잡아야 합니다: install.py claude-md")
    pairs = [(LAB / "assets/skills/coupang-report", ROOT / ".claude/skills/coupang-report"),
             (LAB / "assets/agents/리포트검토.md", ROOT / ".claude/agents/리포트검토.md")]
    for src, dst in pairs:
        if dst.exists():
            print(f"  이미 있음 · 그대로 둡니다: {dst.relative_to(ROOT)}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        (shutil.copytree if src.is_dir() else shutil.copy2)(src, dst)
        print(f"  넣었습니다: {dst.relative_to(ROOT)}")
    print("단계형 스킬 coupang-report · 검토 서브에이전트 리포트검토 준비 완료.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("claude-md")
    c.add_argument("--brand", default="노을뷰티")
    c.add_argument("--trend", type=int, default=30, help="주문 변화 기준 %%")
    c.add_argument("--concentration", type=int, default=70, help="매출 편중 기준 %%")
    sub.add_parser("skill-agent")
    args = ap.parse_args()
    {"claude-md": claude_md, "skill-agent": skill_agent}[args.cmd](args)


if __name__ == "__main__":
    main()
