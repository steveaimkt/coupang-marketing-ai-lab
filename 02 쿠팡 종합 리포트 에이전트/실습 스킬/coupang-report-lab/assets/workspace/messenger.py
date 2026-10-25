"""
메신저 요약 발송 · 리포트 숫자 다섯 줄을 슬랙 또는 디스코드 채널로 보낸다.

  python3 messenger.py --dry-run                 # 가장 최근 결과물로 · 보내지 않고 보여 주고 그 폴더에 남긴다
  python3 messenger.py                           # .env 의 웹훅으로 보낸다
  python3 messenger.py --test                    # 「{브랜드} 리포트 연결 확인」 한 줄만 보내 채널 도착을 본다
  python3 messenger.py --to discord              # .env 에 둘 다 있을 때 고른다 (slack | discord)
  python3 messenger.py --result-dir "결과물/2026-10-20_1405" --dry-run   # 결과물 폴더를 지정
  python3 messenger.py --data-dir "리포트 자료/노을뷰티/2026-10-20" --dry-run   # 자료 폴더를 직접 지정

따로 지정이 없으면 가장 최근 결과물 폴더(결과물/ 안 이름순 마지막)의 리포트를 쓴다.
--dry-run 으로 본 요약은 그 결과물 폴더에 메신저요약.txt 로 남긴다.
링크를 주지 않으면 그 폴더의 노션 주소 파일(*.html.url)을 쓴다.
사람이 리포트를 확인한 뒤에만 보낸다. 웹훅 주소는 .env 에만 둔다.
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_report import (find_files_in_dir, latest_result_dir, read_env,  # noqa: E402
                             resolve_brand, result_root)
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
    # 노션 주소가 없으면 빈 자리 문구를 보내지 않는다
    lines.append(f"리포트 · {link}" if link else "리포트는 첨부 파일로 공유합니다")
    return lines


HERE = Path(__file__).resolve().parent


def pick_result_dir(result_dir: str = None):
    """지정한 결과물 폴더, 없으면 가장 최근 결과물 폴더."""
    if result_dir:
        d = Path(result_dir)
        return d if d.is_absolute() else HERE / d
    return latest_result_dir(result_root())


def data_dir_from_result(rd: Path) -> str:
    """결과물/{자료 날짜}_{HHMM}/{브랜드}_광고리포트_….html → 리포트 자료/{브랜드}/{자료 날짜}"""
    htmls = sorted(rd.glob("*_광고리포트_*.html"))
    if not htmls:
        sys.exit(f"{rd} 에 리포트 HTML 이 없습니다. --data-dir 로 자료 폴더를 지정하세요.")
    brand = htmls[-1].name.split("_광고리포트_")[0]
    m = re.fullmatch(r"(.+)_\d{4}(_\d+)?", rd.name)   # 2026-10-20_1405 · 2026-10-20_1405_2
    date_code = m.group(1) if m else rd.name
    d = HERE / "리포트 자료" / brand / date_code
    if not d.exists():
        sys.exit(f"자료 폴더를 찾지 못했습니다: {d}. --data-dir 로 지정하세요.")
    return str(d)


WEBHOOK_KEYS = {"slack": ("SLACK_WEBHOOK_URL", "슬랙"), "discord": ("DISCORD_WEBHOOK_URL", "디스코드")}

# 실패 응답별 대처 (SKILL.md · reference.md 「안 되실 때」 표와 같게 둔다)
HTTP_HELP = {
    400: "형식이 맞지 않습니다. 주소 끝까지 다 복사했는지, 슬랙 주소를 디스코드 칸(또는 반대)에 넣지 않았는지 보세요",
    401: "주소가 틀렸거나 웹훅가 삭제되었습니다. 웹훅를 다시 만들어 주소를 새로 붙여 넣으세요",
    403: "권한이 없습니다. 슬랙은 워크스페이스 관리자 승인, 디스코드는 서버 관리 권한이 필요할 수 있습니다. 주소가 틀려도 이렇게 나올 수 있습니다",
    404: "주소가 틀렸거나 웹훅가 삭제되었습니다. 웹훅를 다시 만들어 주소를 새로 붙여 넣으세요",
    410: "웹훅가 꺼졌거나 삭제되었습니다. 다시 만드세요",
}


def pick_target(env: dict, to: str = None):
    """보낼 곳을 고른다. --to 가 없고 둘 다 있으면 슬랙을 고르되 화면에 알린다."""
    have = [k for k, (key, _) in WEBHOOK_KEYS.items() if env.get(key)]
    if to:
        key, label = WEBHOOK_KEYS[to]
        if not env.get(key):
            sys.exit(f"\n.env 에 {key} 가 비어 있습니다. {label} 웹훅 주소를 .env 에 직접 붙여 넣으세요.")
        return env[key], to, label
    if not have:
        sys.exit("\n.env 에 SLACK_WEBHOOK_URL 또는 DISCORD_WEBHOOK_URL 이 없습니다. .env.example 을 .env 로 복사하고 하나만 채우세요.")
    kind = have[0]
    if len(have) > 1:
        print("\n.env 에 슬랙과 디스코드가 둘 다 있습니다. 슬랙으로 보냅니다. 디스코드로 보내려면 --to discord")
    return env[WEBHOOK_KEYS[kind][0]], kind, WEBHOOK_KEYS[kind][1]


def send(url: str, kind: str, label: str, text: str):
    body = {"text": text} if kind == "slack" else {"content": text}
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": "coupang-report-lab/1.0"})   # 디스코드는 기본 이름을 막을 때가 있다
    print(f"\n{'슬랙으로' if kind == 'slack' else '디스코드로'} 보냅니다.")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            print(f"{label} 채널로 보냈습니다 · 응답 {r.status}. 채널에 도착했는지 확인하세요.")
    except urllib.error.HTTPError as e:
        detail = e.read()[:120].decode("utf-8", "ignore").strip()
        sys.exit(f"보내지 못했습니다 · 응답 {e.code} {detail}\n대처 · {HTTP_HELP.get(e.code, '오류 메시지를 붙여 넣고 「이게 안 되는데 왜 그런지 찾아줘」 라고 해 주세요')}")
    except urllib.error.URLError as e:
        sys.exit(f"보내지 못했습니다 · 연결 안 됨 ({e.reason})\n대처 · 인터넷 연결과 주소 앞부분(https://hooks.slack.com/… · https://discord.com/api/webhooks/…)을 확인하세요")


def brand_name(rd) -> str:
    if rd is not None:
        htmls = sorted(Path(rd).glob("*_광고리포트_*.html"))
        if htmls:
            return htmls[-1].name.split("_광고리포트_")[0]
    md = HERE / "CLAUDE.md"
    if md.exists():
        m = re.search(r"^- 브랜드:\s*(.+)$", md.read_text(encoding="utf-8"), re.M)
        if m:
            return m.group(1).strip()
    return "쿠팡"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=None, help="자료 폴더 (기본: 가장 최근 결과물의 자료 날짜 폴더)")
    ap.add_argument("--result-dir", default=None, help="결과물 폴더 (기본: 결과물/ 안 이름순 마지막)")
    ap.add_argument("--link", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--test", action="store_true", help="「{브랜드} 리포트 연결 확인」 한 줄만 보낸다")
    ap.add_argument("--to", choices=["slack", "discord"], help=".env 에 둘 다 있을 때 보낼 곳")
    args = ap.parse_args()
    rd = pick_result_dir(args.result_dir)
    if args.test:
        text = f"{brand_name(rd)} 리포트 연결 확인"
        print(text)
        if args.dry_run:
            print("\n(보내지 않았습니다 · --dry-run)")
            return
        send(*pick_target(read_env(), args.to), text)
        return
    if args.data_dir and not args.result_dir:
        rd = None                                      # 자료 폴더만 지정하면 결과물 폴더에 남기지 않는다
    data_dir = args.data_dir
    if not data_dir:
        if rd is None:
            sys.exit("결과물/ 에 리포트 폴더가 없습니다. 리포트를 먼저 만들거나 --data-dir 로 지정하세요.")
        data_dir = data_dir_from_result(rd)
    link = args.link
    if not link and rd is not None:
        urls = sorted(rd.glob("*.html.url"))
        if urls:
            link = urls[-1].read_text(encoding="utf-8").strip()
    text = "\n".join(summary_lines(data_dir, link))
    print(text)
    if args.dry_run:
        print("\n(보내지 않았습니다 · --dry-run)")
        if rd is not None:
            (rd / "메신저요약.txt").write_text(text + "\n", encoding="utf-8")
            print(f"요약을 남겼습니다: {rd / '메신저요약.txt'}")
        return
    send(*pick_target(read_env(), args.to), text)


if __name__ == "__main__":
    main()
