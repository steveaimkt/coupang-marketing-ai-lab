#!/usr/bin/env python3
"""
쿠팡 종합 리포트 자동 생성기

매월 3가지 로우 데이터를 분석하여 종합 리포트를 자동 생성합니다.
HTML 리포트 생성 + Notion 자동 업로드를 지원합니다.

사용법:
    python generate_report.py                              # HTML 리포트만 생성
    python generate_report.py --notion                     # 가장 최근 결과물 리포트를 Notion 에 업로드
    python generate_report.py --data-dir "2월 데이터"       # 다른 데이터 폴더 지정
    python generate_report.py --summary-only               # 숫자만 확인 (파일을 만들지 않는다)

결과물 자리:
    리포트를 만들 때마다 결과물/{자료 날짜}_{만든 시각 HHMM}/ 새 폴더에 넣는다.
    같은 이름 폴더가 있으면 _2, _3 을 붙인다. 이미 있는 리포트는 절대 덮어쓰지 않는다.
    가장 최근 결과물 = 결과물/ 안 폴더 이름순 마지막.

초기 설정:
    .env 에 NOTION_API_KEY / NOTION_PAGE_ID 기입 (.env.example 참고)

필요 파일:
    1) 일별 판매 데이터 (SELLER_INSIGHTS_DAILY_SUMMARY_METRICS_*.xlsx)
    2) 제품별 판매 데이터 (SELLER_INSIGHTS_VENDOR_ITEM_METRICS_*.xlsx)
    3) [선택] 광고 리포트 CSV (chart.csv) - 일별 광고비/매출
    4) [선택] 매출 성장 광고 보고서 XLSX (pa_daily_keyword_*.xlsx)
"""

import argparse
import json
import sys
import os
import webbrowser
from pathlib import Path

# 스크립트 디렉토리를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import load_ad_report, load_ad_creative_report, load_daily_sales, load_product_sales, load_keyword_report, analyze_data, reset_data_gaps
from report_template import generate_html_report

CONFIG_PATH = Path(os.path.dirname(os.path.abspath(__file__))) / "config.json"


ENV_PATH = Path(os.path.dirname(os.path.abspath(__file__))) / ".env"


def read_env() -> dict:
    """.env 의 KEY=VALUE 를 읽는다. 키는 파일에만 두고 화면에 띄우지 않는다."""
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def load_config() -> dict:
    env = read_env()
    if env.get("NOTION_API_KEY"):
        return {"notion": {"api_key": env.get("NOTION_API_KEY"), "database_id": env.get("NOTION_PAGE_ID", ""), "enabled": True}}
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
            # 필수 구조 검증
            for section in ["notion"]:
                if section not in config:
                    config[section] = {}
            return config
        except json.JSONDecodeError as e:
            print(f"  [오류] config.json 파싱 실패: {e}")
            print(f"  config.json 형식을 확인해주세요.")
            return {}
    return {}


def find_files_in_dir(data_dir: str) -> dict:
    """데이터 디렉토리에서 파일을 자동 탐색"""
    data_path = Path(data_dir)

    if not data_path.exists():
        print(f"[오류] 데이터 디렉토리를 찾을 수 없습니다: {data_dir}")
        sys.exit(1)

    files = {}

    # 광고 리포트 (선택): CSV 또는 nca_daily_creative XLSX
    csv_files = list(data_path.glob("*.csv"))
    creative_files = list(data_path.glob("*nca_daily_creative*.xlsx")) + list(data_path.glob("*nca_total_creative*.xlsx"))
    if csv_files:
        files["ad"] = str(csv_files[0])
        files["ad_type"] = "csv"
        print(f"  광고 리포트: {csv_files[0].name}")
    elif creative_files:
        files["ad"] = str(creative_files[0])
        files["ad_type"] = "creative"
        print(f"  광고 리포트: {creative_files[0].name} (크리에이티브)")
    else:
        files["ad"] = None
        files["ad_type"] = None
        print("  광고 리포트: 없음 (선택사항)")

    daily_files = list(data_path.glob("*DAILY*SUMMARY*METRICS*.xlsx"))
    if daily_files:
        files["daily"] = str(daily_files[0])
        print(f"  일별 판매: {daily_files[0].name}")
    else:
        print("[오류] 일별 판매 데이터(DAILY_SUMMARY_METRICS) 파일을 찾을 수 없습니다.")
        sys.exit(1)

    product_files = list(data_path.glob("*VENDOR*ITEM*METRICS*.xlsx"))
    if product_files:
        files["product"] = str(product_files[0])
        print(f"  제품별 판매: {product_files[0].name}")
    else:
        print("[오류] 제품별 판매 데이터(VENDOR_ITEM_METRICS) 파일을 찾을 수 없습니다.")
        sys.exit(1)

    # 매출 성장 광고 보고서 (선택)
    keyword_files = list(data_path.glob("*keyword*.xlsx")) + list(data_path.glob("*pa_daily*.xlsx"))
    # 중복 제거
    keyword_files = list({str(f): f for f in keyword_files}.values())
    if keyword_files:
        files["keyword"] = str(keyword_files[0])
        print(f"  매출 성장 광고 보고서: {keyword_files[0].name}")
    else:
        files["keyword"] = None
        print("  매출 성장 광고 보고서: 없음 (선택사항)")

    return files


RESULT_ROOT = "결과물"


def result_root(output_dir: str = None) -> Path:
    """결과물 뿌리 폴더. 상대 경로면 이 스크립트 폴더 기준."""
    root = Path(output_dir or RESULT_ROOT)
    if not root.is_absolute():
        root = Path(os.path.dirname(os.path.abspath(__file__))) / root
    return root


def result_folders(root: Path) -> list:
    """결과물/ 안의 리포트 폴더를 이름순으로. 파일(3회구동.md 등)은 뺀다."""
    if not root.exists():
        return []
    return sorted([d for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")], key=lambda d: d.name)


def latest_result_dir(root: Path, filename: str = None):
    """가장 최근 결과물 폴더 = 이름순 마지막.
    filename 을 주면 그 리포트가 들어 있는 폴더 중 이름순 마지막."""
    folders = result_folders(root)
    if filename:
        folders = [d for d in folders if (d / filename).exists()]
    return folders[-1] if folders else None


def new_result_dir(root: Path, date_code: str) -> Path:
    """결과물/{자료 날짜}_{HHMM}/ 를 새로 만든다. 같은 이름이 있으면 _2, _3."""
    from datetime import datetime
    base = f"{date_code}_{datetime.now().strftime('%H%M')}"
    cand, n = root / base, 2
    while cand.exists():
        cand = root / f"{base}_{n}"
        n += 1
    cand.mkdir(parents=True)
    return cand


def resolve_brand(brand_arg: str, data_dir: str) -> str:
    """브랜드명 결정: --brand 우선, 없으면 data-dir 경로에서 추출.

    "리포트 자료/노을뷰티/2026-10-20" → 노을뷰티 (끝이 날짜 폴더면 그 앞 세그먼트)
    "리포트 자료/노을뷰티"            → 노을뷰티
    """
    if brand_arg:
        return brand_arg
    if not data_dir:
        return None
    parts = Path(data_dir).parts
    if len(parts) < 2:
        return None
    last = parts[-1]
    import re
    is_date = last.isdigit() or len(last) == 6 or re.fullmatch(r"\d{4}-\d{2}-\d{2}", last)
    return parts[-2] if is_date else last


def main():
    parser = argparse.ArgumentParser(
        description="쿠팡 종합 리포트 자동 생성기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # 파일 지정
    parser.add_argument("--data-dir", "-d", help="데이터 파일 디렉토리 (기본: '리포트 자료')", default=None)
    # 출력 설정
    parser.add_argument("--output-dir", "-o", help="결과물 뿌리 폴더 (기본: '결과물'). 만들 때마다 그 안에 {자료 날짜}_{HHMM}/ 새 폴더", default=RESULT_ROOT)
    parser.add_argument("--result-dir", help="--notion 으로 올릴 결과물 폴더 (기본: 같은 리포트가 든 가장 최근 결과물 폴더)", default=None, dest="result_dir")
    parser.add_argument("--summary-only", help="숫자만 확인하고 파일은 만들지 않는다", action="store_true", dest="summary_only")
    parser.add_argument("--no-open", help="브라우저 자동 열기 비활성화", action="store_true")

    # 연동 옵션
    parser.add_argument("--notion", help="Notion에 리포트 업로드", action="store_true")
    parser.add_argument("--force-html", help="--notion 과 함께 쓰면 가장 최근 리포트 대신 새 리포트를 새 폴더에 만들어 올린다", action="store_true", dest="force_html")
    parser.add_argument("--report-title", help="Notion 리포트 페이지 제목 (기본: '쿠팡 종합 리포트 - {월}')")
    parser.add_argument("--target-sales", type=int, help="월 목표 매출 (예: 70000000)", default=None)
    parser.add_argument("--next-target-sales", type=int, help="다음달 목표 매출 (예: 50000000). 지정 시 다음월 목표를 이 값으로 고정", default=None, dest="next_target_sales")
    parser.add_argument("--brand", help="브랜드명 (Notion 브랜드 페이지 자동 생성, 미지정 시 data-dir에서 추출)")
    parser.add_argument("--end-date", help="분석 종료일 (YYYYMMDD 또는 MMDD, 해당 날짜까지만 포함)", default=None)

    args = parser.parse_args()
    config = load_config()

    # 브랜드명은 한 번만 결정하여 HTML 파일명 / Notion 페이지에 공통 사용
    brand = resolve_brand(args.brand, args.data_dir)

    # 연동 옵션 검증
    total_steps = 4
    if args.notion:
        total_steps += 1

    print("=" * 60)
    print("  쿠팡 종합 리포트 자동 생성기")
    print("=" * 60)

    outputs = []
    if True:
        outputs.append("HTML")
    if args.notion:
        outputs.append("Notion")
    print(f"  출력: {' + '.join(outputs)}")
    print()

    step = 1

    # ========== 1. 파일 찾기 ==========
    data_dir = args.data_dir or "리포트 자료"
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    data_path = Path(data_dir)
    if not data_path.is_absolute():
        data_path = script_dir / data_path
    print(f"[{step}/{total_steps}] 데이터 파일 탐색 중... ({data_path})")
    files = find_files_in_dir(str(data_path))
    step += 1
    print()

    # ========== 2. 데이터 로딩 ==========
    print(f"[{step}/{total_steps}] 데이터 로딩 중...")
    reset_data_gaps()  # 한 번 실행 = 한 벌의 빈 칸 기록
    try:
        ad_df = None
        if files.get("ad"):
            if files.get("ad_type") == "creative":
                ad_df = load_ad_creative_report(files["ad"], files.get("keyword"))
                src_label = "크리에이티브+키워드 합산" if files.get("keyword") else "크리에이티브"
                print(f"  광고 리포트: {len(ad_df)}일 데이터 로딩 완료 ({src_label})")
            else:
                ad_df = load_ad_report(files["ad"])
                print(f"  광고 리포트: {len(ad_df)}일 데이터 로딩 완료")
        elif files.get("keyword"):
            ad_df = load_ad_creative_report(None, files.get("keyword"))
            print(f"  광고 리포트: {len(ad_df)}일 데이터 로딩 완료 (키워드 단독)")
        else:
            print("  광고 리포트: 건너뜀 (파일 없음)")

        daily_df, daily_summary = load_daily_sales(files["daily"])
        print(f"  일별 판매: {len(daily_df)}일 데이터 로딩 완료")

        product_df = load_product_sales(files["product"])
        print(f"  제품별 판매: {len(product_df)}개 제품 데이터 로딩 완료")

        kw_df = None
        if files.get("keyword"):
            kw_df = load_keyword_report(files["keyword"])
            print(f"  매출 성장 광고 보고서: {len(kw_df)}행 데이터 로딩 완료")
    except Exception as e:
        print(f"\n[오류] 데이터 로딩 실패: {e}")
        sys.exit(1)

    # end-date 필터 적용
    if args.end_date:
        import pandas as pd
        ed = args.end_date.strip()
        if len(ed) == 4:  # MMDD → 올해 기준
            ed = f"{daily_df['날짜'].iloc[0].year}{ed}"
        end_dt = pd.to_datetime(ed, format="%Y%m%d")
        before_daily = len(daily_df)
        daily_df = daily_df[daily_df["날짜"] <= end_dt]
        if ad_df is not None:
            ad_df = ad_df[ad_df["날짜"] <= end_dt]
        if kw_df is not None and "날짜" in kw_df.columns:
            # load_keyword_report 는 날짜를 datetime 으로 변환해 돌려준다.
            # 여기서 to_numeric 을 쓰면 나노초 정수가 되어 전 행이 걸러진다(과거 버그).
            # 광고 운영·키워드·제품 트렌드 섹션이 통째로 사라지고도 종료코드 0 이라 눈에 안 띈다.
            before_kw = len(kw_df)
            if pd.api.types.is_datetime64_any_dtype(kw_df["날짜"]):
                kw_df = kw_df[kw_df["날짜"] <= end_dt]
            else:
                kw_df = kw_df[pd.to_numeric(kw_df["날짜"], errors="coerce") <= int(ed)]
            if before_kw > 0 and len(kw_df) == 0:
                print(f"  ⚠️  매출 성장 광고 보고서가 날짜 필터로 전부 제외됨 ({before_kw}행 → 0행). 광고 운영/키워드/제품 트렌드 섹션이 빠집니다.")
        print(f"  날짜 필터: ~{end_dt.strftime('%Y.%m.%d')} ({before_daily}일 → {len(daily_df)}일)")

    # 광고 합계는 판매 기간(일별 판매의 첫날~마지막 날)으로 자른다.
    # 매출 성장 광고 보고서가 판매 기간보다 길면(예 14일) 제품 트렌드 계산에만 전체를 쓴다.
    import pandas as _pd
    kw_trend_df = kw_df
    if daily_df is not None and not daily_df.empty:
        p_start, p_end = daily_df["날짜"].min(), daily_df["날짜"].max()
        if ad_df is not None and not ad_df.empty:
            ad_df = ad_df[(ad_df["날짜"] >= p_start) & (ad_df["날짜"] <= p_end)]
        if kw_df is not None and "날짜" in kw_df.columns and _pd.api.types.is_datetime64_any_dtype(kw_df["날짜"]):
            kw_period = kw_df[(kw_df["날짜"] >= p_start) & (kw_df["날짜"] <= p_end)]
            if len(kw_period) < len(kw_df):
                print(f"  광고 집계 기간을 판매 기간에 맞춤 ({len(kw_df)}행 → {len(kw_period)}행 · 트렌드는 전체 사용)")
            kw_df = kw_period

    step += 1
    print()

    # ========== 3. 데이터 분석 ==========
    print(f"[{step}/{total_steps}] 데이터 분석 중...")
    try:
        analysis = analyze_data(ad_df, daily_df, product_df, kw_df, kw_trend_df=kw_trend_df, target_sales=args.target_sales,
                                next_target_sales=args.next_target_sales)
        print(f"  분석 기간: {analysis['기간']}")
        for g in analysis.get('결측', []):
            when = f" ({', '.join(g['날짜'])})" if g.get('날짜') else ""
            print(f"  ⚠ 빈 칸: {g['자료']} · {g['칸']} {g['건수']}건{when} → 0으로 계산했습니다")
        print(f"  총 매출: {analysis['판매']['총매출']:,}원")
        if analysis['광고'].get('사용'):
            print(f"  총 광고비: {analysis['광고']['총광고비']:,}원")
            print(f"  ROAS(전체 매출 기준): {analysis['광고']['ROAS']}%")
        else:
            print("  광고 데이터: 없음 (광고 분석 생략)")
        print(f"  인사이트: {len(analysis.get('인사이트', []))}건 도출")
        print(f"  필수확인: {len(analysis.get('필수확인', []))}건 도출")
        print(f"  개선사항: {len(analysis['개선사항'])}건 도출")
        print(f"  운영플랜: {len(analysis['운영플랜'])}건 수립")
    except Exception as e:
        print(f"\n[오류] 데이터 분석 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    step += 1
    print()

    if args.summary_only:
        print("  숫자만 확인했습니다 (--summary-only · 파일을 만들지 않았습니다)")
        return None

    # ========== 4. HTML 리포트 생성 ==========
    print(f"[{step}/{total_steps}] HTML 리포트 생성 중...")
    try:
        html_content = generate_html_report(analysis)

        root = result_root(args.output_dir)

        # 자료 날짜 = 읽은 데이터 날짜 폴더 이름 (없으면 판매 마지막 날)
        date_code = Path(args.data_dir).parts[-1] if args.data_dir else None
        if not date_code or date_code == "리포트 자료":
            date_code = daily_df["날짜"].max().strftime("%Y-%m-%d")

        # 파일명: 브랜드_광고리포트_날짜.html (브랜드 없으면 기존 형식)
        if brand and args.data_dir:
            if len(date_code) == 6 and date_code.isdigit():
                date_display = f"20{date_code[:2]}.{date_code[2:4]}.{date_code[4:6]}"
            elif len(date_code) == 8 and date_code.isdigit():
                date_display = f"{date_code[:4]}.{date_code[4:6]}.{date_code[6:8]}"
            else:
                date_display = date_code
            filename = f"{brand}_광고리포트_{date_display}.html"
        else:
            month_str = analysis["월"].replace("년 ", "_").replace("월", "").replace("/", "").replace("~", "-")
            filename = f"쿠팡_종합리포트_{month_str}.html"

        # Notion 배포만 실행하면 새로 만들지 않고 가장 최근 결과물의 리포트를 올린다 (사람이 손본 섹션 유지)
        existing = None
        if args.notion and not args.force_html:
            if args.result_dir:
                rd = Path(args.result_dir)
                if not rd.is_absolute():
                    rd = script_dir / rd
                existing = rd if (rd / filename).exists() else None
                if existing is None:
                    print(f"  [오류] {rd} 에 {filename} 이 없습니다.")
                    sys.exit(1)
            else:
                existing = latest_result_dir(root, filename)

        if existing is not None:
            result_dir = existing
            filepath = result_dir / filename
            print(f"  기존 리포트를 그대로 올립니다: {filepath}")
        else:
            # 만들 때마다 새 폴더. 이미 있는 리포트는 덮어쓰지 않는다.
            result_dir = new_result_dir(root, date_code)
            filepath = result_dir / filename
            with open(filepath, "x", encoding="utf-8") as f:
                f.write(html_content)
            print(f"  결과물 폴더: {result_dir}")
            print(f"  HTML 리포트: {filepath}")
    except Exception as e:
        print(f"\n[오류] HTML 리포트 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    step += 1
    print()

    # ========== 5. Notion 업로드 (선택) ==========
    notion_url = None
    if args.notion:
        print(f"[{step}/{total_steps}] Notion 업로드 중...")
        notion_config = config.get("notion", {})

        if not notion_config.get("api_key") or not notion_config.get("database_id"):
            print("  [경고] Notion API가 설정되지 않았습니다.")
            print("  .env 의 NOTION_API_KEY / NOTION_PAGE_ID 를 확인하세요.")
        else:
            try:
                from notion_exporter import export_to_notion
                html_file = str(filepath) if 'filepath' in locals() else None
                notion_url = export_to_notion(analysis, config, title=args.report_title, brand_name=brand, html_path=html_file)
                print(f"  Notion 업로드 완료: {notion_url}")
                
                # HTML 리포트 옆에 Notion URL을 기록 (어느 HTML이 어느 Notion 페이지인지 추적용)
                if notion_url and 'filepath' in locals():
                    url_filepath = str(filepath) + ".url"
                    try:
                        with open(url_filepath, "w", encoding="utf-8") as url_f:
                            url_f.write(notion_url)
                        print(f"  Notion URL 저장 완료: {url_filepath}")
                    except Exception as e:
                        print(f"  [경고] Notion URL 파일 저장 실패: {e}")
            except Exception as e:
                print(f"  [오류] Notion 업로드 실패: {e}")
                import traceback
                traceback.print_exc()
        step += 1
        print()

    # ========== 결과 요약 ==========
    print("=" * 60)
    print("  리포트 생성 완료!")
    print("=" * 60)
    print(f"  폴더:   {result_dir}")
    print(f"  HTML:   {filepath}")
    if notion_url:
        print(f"  Notion: {notion_url}")
    print("=" * 60)

    # 브라우저에서 열기
    if not args.no_open:
        # 로컬 웹(http://localhost:8770~)으로 연다. 서버를 못 띄우면 serve.show() 가 file:// 로 대신 연다.
        try:
            from serve import show
            show(filepath)
        except Exception as e:
            print(f"  로컬 웹을 쓰지 못해 파일로 엽니다 ({e})")
            webbrowser.open(f"file://{filepath.resolve()}")

    return str(filepath)


if __name__ == "__main__":
    main()
