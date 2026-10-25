"""
2부 실습 설치 도구 · 폴더를 먼저 만들고, CLAUDE.md 로 기준을 잡고, 그다음 스킬과 서브에이전트를 넣는다.

  python3 .claude/skills/coupang-report-lab/scripts/install.py folders            (Step 0)
  python3 .claude/skills/coupang-report-lab/scripts/install.py folders --no-sample
  python3 .claude/skills/coupang-report-lab/scripts/install.py claude-md --brand 노을뷰티 --trend 30 --concentration 70 --roas-risk 200 --roas-good 300
  python3 .claude/skills/coupang-report-lab/scripts/install.py skill-agent

작업 폴더는 이 스킬이 들어 있는 폴더(.claude/skills/ 의 두 칸 위)다. 이름은 무엇이든 된다.
다른 곳에서 돌릴 때는 --workspace 로 작업 폴더를 준다.
순서를 바꿀 수 없다. CLAUDE.md 가 없으면 skill-agent 는 멈춘다. 이미 있는 파일은 덮어쓰지 않는다.
"""
import argparse
import shutil
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
WORKSPACE_SRC = LAB / "assets/workspace"
SAMPLE_PARTS = ("리포트 자료", "보관")     # --no-sample 이면 이 둘은 넣지 않는다
SKIP = {".DS_Store", "__pycache__"}


def default_root():
    """.claude/skills/coupang-report-lab 에 풀려 있으면 그 두 칸 위, 아니면 지금 폴더."""
    if LAB.parent.name == "skills" and LAB.parents[1].name == ".claude":
        return LAB.parents[2]
    return Path.cwd()


ROOT = default_root()


def folders(args):
    made, kept = [], []
    for src in sorted(WORKSPACE_SRC.rglob("*")):
        rel = src.relative_to(WORKSPACE_SRC)
        if SKIP & set(rel.parts):
            continue
        if args.no_sample and rel.parts[0] in SAMPLE_PARTS:
            continue
        dst = ROOT / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        if dst.exists():
            kept.append(rel)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        made.append(rel)
    if args.no_sample:
        (ROOT / "리포트 자료").mkdir(exist_ok=True)

    def count(prefix):
        return sum(1 for r in made if str(r).startswith(prefix))

    print(f"작업 폴더: {ROOT.name}/")
    print(f"  리포트 생성기 · 파이썬 {sum(1 for r in made if r.suffix == '.py' and len(r.parts) == 1)}개 · requirements.txt · .env.example")
    if args.no_sample:
        print("  리포트 자료/ · 비어 있음 (Step 1 에서 내 브랜드 폴더를 만든다)")
    else:
        print(f"  리포트 자료/노을뷰티/2026-10-20/ · 샘플 {count('리포트 자료')}개")
        print(f"  보관/2026-11-09/ · 2회차 샘플 {count('보관')}개")
    print("  결과물/ · 비어 있음")
    print(f"  .claude/ · 훅 {count('.claude/hooks')}개 · 규칙 {count('.claude/rules')}개 · settings.json")
    print(f"새로 넣은 파일 {len(made)}개 · 이미 있어서 그대로 둔 파일 {len(kept)}개")
    for r in kept:
        print(f"  그대로 둠: {r}")
    print("훅과 settings.json 은 새 세션부터 켜집니다 (Step 3 에서 새 세션을 엽니다).")


def claude_md(args):
    dest = ROOT / "CLAUDE.md"
    if dest.exists():
        sys.exit(f"CLAUDE.md 가 이미 있습니다. 덮어쓰지 않습니다. 기준을 바꾸려면 「판단 기준」 줄만 고치세요: {dest}")
    text = (LAB / "assets/CLAUDE.md").read_text(encoding="utf-8")
    text = text.replace("{{BRAND}}", args.brand).replace("{{TREND}}", str(args.trend)).replace("{{CONC}}", str(args.concentration))
    text = (text.replace("{{ROAS_RISK}}", str(args.roas_risk)).replace("{{ROAS_GOOD}}", str(args.roas_good))
                .replace("{{ROAS_TARGET}}", str(args.target_roas) if args.target_roas else "없음"))
    dest.write_text(text, encoding="utf-8")
    print(f"CLAUDE.md 를 만들었습니다: {dest.name}")
    print(f"  판단 기준 · 브랜드 {args.brand} · 주문 변화 {args.trend}% · 매출 편중 {args.concentration}%")
    print(f"  광고 기준 · 적자 위험 ROAS {args.roas_risk}% 미만 · 양호 {args.roas_good}% 이상 · 목표 ROAS {args.target_roas or '없음'}")
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
    global ROOT
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", help="작업 폴더 (기본: 이 스킬이 풀린 폴더의 두 칸 위)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("folders")
    f.add_argument("--no-sample", action="store_true", help="샘플 자료 없이 만든다 (내 자료로 할 때)")
    c = sub.add_parser("claude-md")
    c.add_argument("--brand", default="노을뷰티")
    c.add_argument("--trend", type=int, default=30, help="주문 변화 기준 %%")
    c.add_argument("--concentration", type=int, default=70, help="매출 편중 기준 %%")
    c.add_argument("--roas-risk", type=int, default=200, help="ROAS(전체 매출 기준)가 이 %% 미만이면 적자 위험")
    c.add_argument("--roas-good", type=int, default=300, help="ROAS 가 이 %% 이상이면 양호")
    c.add_argument("--target-roas", type=int, default=None, help="다음 달 목표 ROAS %% (없으면 양호 기준과 지금+50 중 큰 값)")
    sub.add_parser("skill-agent")
    args = ap.parse_args()
    if args.workspace:
        ROOT = Path(args.workspace).resolve()
    if args.cmd == "claude-md" and args.roas_risk >= args.roas_good:
        sys.exit("적자 위험 기준은 양호 기준보다 작아야 합니다 (예 200 · 300).")
    {"folders": folders, "claude-md": claude_md, "skill-agent": skill_agent}[args.cmd](args)


if __name__ == "__main__":
    main()
