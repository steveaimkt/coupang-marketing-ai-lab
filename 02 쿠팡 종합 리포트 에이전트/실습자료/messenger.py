"""
메신저 요약 발송 · 리포트 숫자 다섯 줄을 슬랙 또는 디스코드 채널로 보낸다.

  python3 messenger.py --data-dir "리포트 자료/노을뷰티/2026-10-20" --dry-run   # 보내지 않고 보여만 준다
  python3 messenger.py --data-dir "리포트 자료/노을뷰티/2026-10-20"             # .env 의 웹훅으로 보낸다

사람이 리포트를 확인한 뒤에만 보낸다. 웹훅 주소는 .env 에만 둔다.
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_report import find_files_in_dir, read_env, resolve_brand  # noqa: E402
from data_loader import (analyze_data, load_ad_creative_report, load_daily_sales,  # noqa: E402
                         load_keyword_report, load_product_sales, reset_data_gaps)


def moved_text(tr: dict, brand: str, show: int = 3) -> str:
    """주문이 기준 넘게 변한 상품 · 변화가 큰 순서로 3개만 보이고 나머지는 「외 N개」 로 줄인다.
    요약에서는 상품명 앞 브랜드 이름을 뺀다."""
    moved = sorted(tr.get("판매증가추세", []) + tr.get("판매감소추세", []),
                   key=lambda p: abs(p.get("변화율", 0)), reverse=True)
    if not moved:
        return "없음"

    def short(name: str) -> str:
        return name[len(brand):].strip() if brand and name.startswith(brand) else name

    head = [f"{short(p['상품명'])} {p.get('변화율', 0):+.0f}%" for p in moved[:show]]
    rest = len(moved) - show
    return ", ".join(head) + (f" 외 {rest}개" if rest > 0 else "")


def summary_lines(data_dir: str, link: str = "") -> list:
    reset_data_gaps()
    f = find_files_in_dir(data_dir)
    creative = f.get("ad") if f.get("ad_type") == "creative" else None   # 신규 구매 고객 확보 광고 보고서
    ad = load_ad_creative_report(creative, f.get("keyword")) if (creative or f.get("keyword")) else None
    daily, _ = load_daily_sales(f["daily"])
    prod = load_product_sales(f["product"])
    kw = load_keyword_report(f["keyword"]) if f.get("keyword") else None
    s_, e_ = daily["날짜"].min(), daily["날짜"].max()     # 광고 합계는 판매 기간으로
    ad = ad[(ad["날짜"] >= s_) & (ad["날짜"] <= e_)] if ad is not None else None
    kw_p = kw[(kw["날짜"] >= s_) & (kw["날짜"] <= e_)] if kw is not None else None
    a = analyze_data(ad, daily, prod, kw_p, kw_trend_df=kw)
    brand = resolve_brand(None, data_dir) or ""
    top = (a.get("제품", {}).get("상품별요약") or [{}])[0]
    total = sum(p.get("매출", 0) for p in a.get("제품", {}).get("상품별요약", [])) or 1
    lines = [f"[{brand} 쿠팡 리포트 · {a['기간']}]",
             f"매출 {a['판매']['총매출']:,}원"
             + (f" · 광고비 {a['광고']['총광고비']:,}원 · ROAS {a['광고']['ROAS']}% (전체 매출 기준)" if a['광고'].get('사용') else "")]
    if top:
        lines.append(f"매출 1위 · {top.get('상품명', '')} {top.get('매출', 0) / total * 100:.1f}%")
    tr = a.get("제품트렌드", {})
    lines.append(f"주문 {tr.get('추세기준', 30)}% 넘게 변한 상품 · " + moved_text(tr, brand))
    lines.append(f"리포트 · {link}" if link else "리포트 · 노션 페이지 링크")
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--link", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    text = "\n".join(summary_lines(args.data_dir, args.link))
    print(text)
    if args.dry_run:
        print("\n(보내지 않았습니다 · --dry-run)")
        return
    env = read_env()
    url, kind = (env.get("SLACK_WEBHOOK_URL"), "slack") if env.get("SLACK_WEBHOOK_URL") else (env.get("DISCORD_WEBHOOK_URL"), "discord")
    if not url:
        sys.exit("\n.env 에 SLACK_WEBHOOK_URL 또는 DISCORD_WEBHOOK_URL 이 없습니다. .env.example 을 보세요.")
    body = {"text": text} if kind == "slack" else {"content": text}
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        print(f"\n{kind} 채널로 보냈습니다 · 응답 {r.status}")


if __name__ == "__main__":
    main()
