"""
쿠팡 종합 리포트 - 데이터 로딩 및 분석 모듈
매월 로우 데이터를 읽어 분석 결과를 딕셔너리로 반환합니다.
"""

import calendar
import pandas as pd
import numpy as np
from pathlib import Path

CLAUDE_MD = Path(__file__).with_name("CLAUDE.md")
_DEFAULTS = {"브랜드": "노을뷰티", "주문변화_기준_pct": 30, "매출편중_기준_pct": 70,
             "ROAS_위험_기준_pct": 200, "ROAS_양호_기준_pct": 300, "목표_ROAS_pct": None}


def SETTINGS() -> dict:
    """판단 기준 · CLAUDE.md 의 「판단 기준」 줄을 매번 읽는다. 기준을 바꾸면 CLAUDE.md 한 줄만 고친다."""
    import re
    s = dict(_DEFAULTS)
    if CLAUDE_MD.exists():
        for m in re.finditer(r"^\s*[-*]?\s*`?(브랜드|주문변화_기준_pct|매출편중_기준_pct|ROAS_위험_기준_pct|ROAS_양호_기준_pct|목표_ROAS_pct)`?\s*[:=]\s*([^\s#|]+)",
                             CLAUDE_MD.read_text(encoding="utf-8"), re.M):
            k, v = m.group(1), m.group(2).strip("`\"'")
            if k == "브랜드":
                s[k] = v
            elif v in ("없음", "null", "none", "None", "-"):
                s[k] = None
            else:
                s[k] = float(v) if "." in v else int(v)
    return s


def load_ad_report(file_path: str) -> pd.DataFrame:
    """광고 리포트 로딩 (CSV 또는 XLSX, 3컬럼 간단 형식)"""
    ext = Path(file_path).suffix.lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(file_path, engine="openpyxl")
    else:
        df = pd.read_csv(file_path, encoding="utf-8-sig")
    df.columns = ["날짜", "광고비", "광고매출"]
    df["날짜"] = pd.to_datetime(df["날짜"])
    df["광고비"] = pd.to_numeric(df["광고비"], errors="coerce").fillna(0).astype(int)
    df["광고매출"] = pd.to_numeric(df["광고매출"], errors="coerce").fillna(0).astype(int)
    df["ROAS"] = df.apply(
        lambda r: round(r["광고매출"] / r["광고비"] * 100, 1) if r["광고비"] > 0 else 0,
        axis=1,
    )
    df["요일"] = df["날짜"].dt.day_name()
    df["주차"] = df["날짜"].dt.isocalendar().week.astype(int)
    return df


def load_ad_creative_report(creative_path: str = None, keyword_path: str = None) -> pd.DataFrame:
    """광고 리포트 합산 로딩 (nca_daily_creative + pa_daily_keyword → 날짜별 합계)

    두 파일의 광고비/매출을 날짜별로 합산하여 하나의 광고 DataFrame을 반환합니다.
    - nca_daily_creative: 컬럼 '집행 광고비', '첫구매를 통한 광고 전환 매출'
    - pa_daily_keyword: 컬럼 '광고비', '총 전환매출액(14일)'
    creative_path가 None이면 매출 성장 광고 보고서만으로 광고 데이터를 구성합니다.
    """
    parts = []

    # 1) 신규 구매 고객 확보 광고 보고서 (있을 때만)
    if creative_path:
        cr = pd.read_excel(creative_path, engine="openpyxl")
        cr["집행 광고비"] = pd.to_numeric(cr["집행 광고비"], errors="coerce").fillna(0).astype(int)
        cr["첫구매를 통한 광고 전환 매출"] = pd.to_numeric(cr["첫구매를 통한 광고 전환 매출"], errors="coerce").fillna(0).astype(int)
        if "날짜" in cr.columns:
            cr_daily = cr.groupby("날짜").agg(
                광고비=("집행 광고비", "sum"),
                광고매출=("첫구매를 통한 광고 전환 매출", "sum"),
            ).reset_index()
            cr_daily["날짜"] = pd.to_datetime(cr_daily["날짜"], format="%Y%m%d")
        else:
            # nca_total_creative: 날짜 없는 합산 리포트 → 매출 성장 광고 보고서 날짜 기준으로 배분
            cr_total_ad = int(cr["집행 광고비"].sum())
            cr_total_rev = int(cr["첫구매를 통한 광고 전환 매출"].sum())
            if keyword_path:
                kw_tmp = pd.read_excel(keyword_path, engine="openpyxl")
                kw_dates = pd.to_numeric(kw_tmp["날짜"], errors="coerce").dropna().unique()
                n_days = len(kw_dates)
                if n_days > 0:
                    cr_daily = pd.DataFrame({
                        "날짜": pd.to_datetime([str(int(d)) for d in sorted(kw_dates)], format="%Y%m%d"),
                        "광고비": [cr_total_ad // n_days] * n_days,
                        "광고매출": [cr_total_rev // n_days] * n_days,
                    })
                else:
                    cr_daily = pd.DataFrame({"날짜": pd.Series(dtype="datetime64[ns]"), "광고비": pd.Series(dtype=int), "광고매출": pd.Series(dtype=int)})
            else:
                cr_daily = pd.DataFrame({"날짜": pd.Series(dtype="datetime64[ns]"), "광고비": pd.Series(dtype=int), "광고매출": pd.Series(dtype=int)})
        if not cr_daily.empty:
            parts.append(cr_daily)

    # 2) 매출 성장 광고 보고서 (있으면 합산)
    if keyword_path:
        kw = pd.read_excel(keyword_path, engine="openpyxl")
        kw["광고비"] = pd.to_numeric(kw["광고비"], errors="coerce").fillna(0).astype(int)
        kw["총 전환매출액(14일)"] = pd.to_numeric(kw["총 전환매출액(14일)"], errors="coerce").fillna(0).astype(int)
        kw_daily = kw.groupby("날짜").agg(
            광고비=("광고비", "sum"),
            광고매출=("총 전환매출액(14일)", "sum"),
        ).reset_index()
        kw_daily["날짜"] = pd.to_datetime(kw_daily["날짜"], format="%Y%m%d")
        parts.append(kw_daily)

    # 합산
    merged = pd.concat(parts, ignore_index=True)
    daily = merged.groupby("날짜").agg(
        광고비=("광고비", "sum"),
        광고매출=("광고매출", "sum"),
    ).reset_index().sort_values("날짜").reset_index(drop=True)

    daily["ROAS"] = daily.apply(
        lambda r: round(r["광고매출"] / r["광고비"] * 100, 1) if r["광고비"] > 0 else 0,
        axis=1,
    )
    daily["요일"] = daily["날짜"].dt.day_name()
    daily["주차"] = daily["날짜"].dt.isocalendar().week.astype(int)
    return daily


#: 빈 값을 0으로 채운 자리를 기록한다. 리포트에 그대로 표시된다.
#: 0으로 채우는 것 자체는 유지한다. 다만 조용히 채우지 않는다.
DATA_GAPS = []


def reset_data_gaps():
    """한 번 실행 = 한 벌의 기록. 리포트 생성 시작 시 비운다."""
    DATA_GAPS.clear()


def _record_gaps(raw, df, cols, source):
    """0으로 채우기 직전에 빈 칸을 세어 DATA_GAPS 에 남긴다."""
    for col in cols:
        if col not in raw.columns:
            continue
        na = pd.to_numeric(
            raw[col].astype(str).str.replace(",", "").str.replace("%", ""),
            errors="coerce",
        ).isna()
        if not na.any():
            continue
        when = []
        if "날짜" in df.columns:
            idx = [i for i in na[na].index if i in df.index]
            when = [str(d)[:10] for d in df.loc[idx, "날짜"]]
        DATA_GAPS.append({
            "자료": source,
            "칸": col,
            "건수": int(na.sum()),
            "날짜": when,
        })


def load_daily_sales(file_path: str) -> pd.DataFrame:
    """일별 판매 데이터 로딩 (DAILY_SUMMARY_METRICS)"""
    df = pd.read_excel(file_path, engine="openpyxl")
    # 마지막 행이 합계일 수 있으므로 확인
    if pd.isna(df.iloc[-1]["날짜"]) or df.iloc[-1]["날짜"] == "":
        summary_row = df.iloc[-1].copy()
        df = df.iloc[:-1].copy()
    else:
        summary_row = None

    df["날짜"] = pd.to_datetime(df["날짜"])
    numeric_cols = ["방문자", "조회", "장바구니", "주문", "판매량"]
    _record_gaps(df, df, numeric_cols + ["구매전환율", "매출(원)"], "일별 판매")
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # 전환율 처리 (문자열 '%' 제거)
    df["구매전환율"] = (
        df["구매전환율"]
        .astype(str)
        .str.replace("%", "")
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0)
    )

    # 방문자나 조회가 0인데 주문이 있는 날은 전환율을 낼 수 없다 (나누는 값이 0).
    # 그날은 전환율 계산에서 빼고, 표에는 「방문자 0 · 계산 제외」 로 적는다.
    df["전환율제외"] = ((df["방문자"] == 0) | (df["조회"] == 0)) & (df["주문"] > 0)
    df.loc[df["전환율제외"], "구매전환율"] = 0.0

    # 매출 처리 (문자열일 수 있음)
    df["매출"] = (
        df["매출(원)"]
        .astype(str)
        .str.replace(",", "")
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0)
        .astype(int)
    )

    df["요일"] = df["날짜"].dt.day_name()
    df["주차"] = df["날짜"].dt.isocalendar().week.astype(int)

    return df, summary_row


def load_product_sales(file_path: str) -> pd.DataFrame:
    """제품별 판매 데이터 로딩 (VENDOR_ITEM_METRICS)"""
    df = pd.read_excel(file_path, engine="openpyxl")

    numeric_cols = ["매출(원)", "주문", "판매량", "방문자", "조회", "장바구니",
                    "총 매출(원)", "총 판매수", "총 취소 금액(원)", "총 취소된 상품수", "즉시 취소된 상품수"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # 전환율 처리
    df["구매전환율"] = (
        df["구매전환율"]
        .astype(str)
        .str.replace("%", "")
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0)
    )

    # 아이템위너 비율 처리
    if "아이템위너 비율(%)" in df.columns:
        df["아이템위너비율"] = pd.to_numeric(df["아이템위너 비율(%)"], errors="coerce").fillna(0)

    return df


def analyze_product_trends(kw_df: pd.DataFrame, products: dict) -> dict:
    """키워드 데이터의 날짜별 상품 매출로 제품 트렌드 분석

    - 최근 7일 매출 급등/급락 제품
    - 판매량 상위/하위 5개
    - 판매 추세 변화 제품 (30% 이상 증감)
    """
    result = {}

    # --- 판매량 상위/하위 (제품별 데이터 기반, 항상 가능) ---
    all_products = [p for p in products.get("상품별요약", []) if p["매출"] > 0]
    result["판매량상위5"] = sorted(all_products, key=lambda p: p["판매량"], reverse=True)[:5]
    result["판매량하위5"] = sorted(all_products, key=lambda p: p["판매량"])[:5]

    # --- 키워드 데이터 없으면 트렌드 분석 불가 ---
    if kw_df is None or kw_df.empty or "날짜" not in kw_df.columns:
        result["매출급등"] = []
        result["매출급락"] = []
        result["판매증가추세"] = []
        result["판매감소추세"] = []
        return result

    # 날짜별 상품별 매출/주문 집계
    kw = kw_df.copy()
    kw["총 전환매출액(14일)"] = pd.to_numeric(kw["총 전환매출액(14일)"], errors="coerce").fillna(0)
    kw["총 주문수(14일)"] = pd.to_numeric(kw["총 주문수(14일)"], errors="coerce").fillna(0)

    daily_product = kw.groupby(["날짜", "광고집행 상품명"]).agg(
        매출=("총 전환매출액(14일)", "sum"),
        주문=("총 주문수(14일)", "sum"),
    ).reset_index()

    # 상품명 정리 (옵션 정보 제거: 콤마 이전 부분)
    daily_product["상품명"] = daily_product["광고집행 상품명"].str.split(",").str[0].str.strip()
    daily_product = daily_product.groupby(["날짜", "상품명"]).agg(매출=("매출", "sum"), 주문=("주문", "sum")).reset_index()

    dates_sorted = sorted(daily_product["날짜"].unique())
    total_days = len(dates_sorted)

    if total_days < 7:
        result["매출급등"] = []
        result["매출급락"] = []
        result["판매증가추세"] = []
        result["판매감소추세"] = []
        return result

    # 최근 7일 vs 이전 기간
    recent_7 = dates_sorted[-7:]
    earlier = dates_sorted[:-7]

    recent_df = daily_product[daily_product["날짜"].isin(recent_7)].groupby("상품명").agg(
        최근매출=("매출", "sum"), 최근주문=("주문", "sum")).reset_index()
    earlier_df = daily_product[daily_product["날짜"].isin(earlier)].groupby("상품명").agg(
        이전매출=("매출", "sum"), 이전주문=("주문", "sum")).reset_index()

    merged = pd.merge(recent_df, earlier_df, on="상품명", how="outer").fillna(0)

    # 이전 기간을 7일 기준으로 정규화
    earlier_days = len(earlier) if len(earlier) > 0 else 1
    merged["이전매출_7일환산"] = (merged["이전매출"] / earlier_days * 7).round(0)
    merged["이전주문_7일환산"] = (merged["이전주문"] / earlier_days * 7).round(0)

    # 변화율 계산
    merged["매출변화율"] = merged.apply(
        lambda r: round((r["최근매출"] - r["이전매출_7일환산"]) / r["이전매출_7일환산"] * 100, 1)
        if r["이전매출_7일환산"] > 0 else (100.0 if r["최근매출"] > 0 else 0), axis=1)
    merged["주문변화율"] = merged.apply(
        lambda r: round((r["최근주문"] - r["이전주문_7일환산"]) / r["이전주문_7일환산"] * 100, 1)
        if r["이전주문_7일환산"] > 0 else (100.0 if r["최근주문"] > 0 else 0), axis=1)

    # 매출 급등 TOP 5 (최근 매출 > 0, 변화율 높은 순)
    rising = merged[(merged["최근매출"] > 0) & (merged["매출변화율"] > 0)].sort_values("매출변화율", ascending=False)
    result["매출급등"] = [
        {"상품명": r["상품명"], "최근7일매출": int(r["최근매출"]), "이전7일매출": int(r["이전매출_7일환산"]), "변화율": r["매출변화율"]}
        for _, r in rising.head(5).iterrows()
    ]

    # 매출 급락 TOP 5 (이전 매출 > 0, 변화율 낮은 순)
    falling = merged[(merged["이전매출_7일환산"] > 0) & (merged["매출변화율"] < 0)].sort_values("매출변화율")
    result["매출급락"] = [
        {"상품명": r["상품명"], "최근7일매출": int(r["최근매출"]), "이전7일매출": int(r["이전매출_7일환산"]), "변화율": r["매출변화율"]}
        for _, r in falling.head(5).iterrows()
    ]

    # 판매 추세 변화 (기준 % 이상 증감, 알림 대상) · 기준은 CLAUDE.md 「판단 기준」
    th = SETTINGS()["주문변화_기준_pct"]
    result["추세기준"] = th
    result["판매증가추세"] = [
        {"상품명": r["상품명"], "최근7일주문": int(r["최근주문"]), "이전7일주문": int(r["이전주문_7일환산"]), "변화율": r["주문변화율"]}
        for _, r in merged[(merged["주문변화율"] >= th) & (merged["최근주문"] > 0)].sort_values("주문변화율", ascending=False).head(5).iterrows()
    ]
    result["판매감소추세"] = [
        {"상품명": r["상품명"], "최근7일주문": int(r["최근주문"]), "이전7일주문": int(r["이전주문_7일환산"]), "변화율": r["주문변화율"]}
        for _, r in merged[(merged["주문변화율"] <= -th) & (merged["이전주문_7일환산"] > 0)].sort_values("주문변화율").head(5).iterrows()
    ]

    return result


def load_keyword_report(file_path: str) -> pd.DataFrame:
    """광고 키워드/지면 상세 리포트 로딩 (pa_daily_keyword)"""
    df = pd.read_excel(file_path, engine="openpyxl")

    # 날짜 처리 (20260101 형식)
    df["날짜"] = pd.to_datetime(df["날짜"].astype(str).str.replace(r"\.0$", "", regex=True), format="%Y%m%d")

    # 숫자 컬럼 변환
    num_cols = ["노출수", "클릭수", "광고비",
                "총 주문수(1일)", "직접 주문수(1일)", "간접 주문수(1일)",
                "총 판매수량(1일)", "직접 판매수량(1일)", "간접 판매수량(1일)",
                "총 전환매출액(1일)", "직접 전환매출액(1일)", "간접 전환매출액(1일)",
                "총 주문수(14일)", "총 판매수량(14일)", "총 전환매출액(14일)"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # 클릭률 숫자 변환
    if "클릭률" in df.columns:
        df["클릭률"] = pd.to_numeric(df["클릭률"], errors="coerce").fillna(0)

    return df


def analyze_keyword_data(kw_df: pd.DataFrame) -> dict:
    """키워드/지면 데이터 분석"""
    result = {}

    # ---- 지면별 분석 (검색 영역 / 비검색 영역) ----
    placement = kw_df.groupby("광고 노출 지면").agg(
        노출수=("노출수", "sum"),
        클릭수=("클릭수", "sum"),
        광고비=("광고비", "sum"),
        주문수=("총 주문수(1일)", "sum"),
        매출=("총 전환매출액(1일)", "sum"),
    ).reset_index()
    placement["CTR"] = (placement["클릭수"] / placement["노출수"] * 100).round(2).fillna(0)
    placement["ROAS"] = (placement["매출"] / placement["광고비"] * 100).round(1).fillna(0)
    placement["CPC"] = (placement["광고비"] / placement["클릭수"]).round(0).fillna(0)
    result["지면별"] = placement.to_dict("records")

    # ---- 키워드별 분석 (검색 키워드만, '-' 제외) ----
    kw_search = kw_df[kw_df["키워드"] != "-"].copy()
    if not kw_search.empty:
        kw_summary = kw_search.groupby("키워드").agg(
            노출수=("노출수", "sum"),
            클릭수=("클릭수", "sum"),
            광고비=("광고비", "sum"),
            주문수=("총 주문수(1일)", "sum"),
            매출=("총 전환매출액(1일)", "sum"),
        ).reset_index()
        kw_summary["CTR"] = (kw_summary["클릭수"] / kw_summary["노출수"] * 100).round(2).fillna(0)
        kw_summary["ROAS"] = (kw_summary["매출"] / kw_summary["광고비"] * 100).round(1).fillna(0)
        kw_summary["CPC"] = (kw_summary["광고비"] / kw_summary["클릭수"]).round(0).fillna(0)
        kw_summary["전환율"] = (kw_summary["주문수"] / kw_summary["클릭수"] * 100).round(2).fillna(0)

        # Top 키워드 (매출순)
        result["키워드_매출순"] = kw_summary.sort_values("매출", ascending=False).head(20).to_dict("records")
        # Top 키워드 (클릭순)
        result["키워드_클릭순"] = kw_summary.sort_values("클릭수", ascending=False).head(20).to_dict("records")
        # Top 키워드 (노출순)
        result["키워드_노출순"] = kw_summary.sort_values("노출수", ascending=False).head(20).to_dict("records")
        # 고효율 키워드 (ROAS 높은 + 매출 발생)
        efficient = kw_summary[kw_summary["매출"] > 0].sort_values("ROAS", ascending=False).head(15)
        result["키워드_고효율"] = efficient.to_dict("records")
        # 저효율 키워드 (광고비 높으나 매출 0)
        # 표에는 상위 15개만 싣되, 합계·개수는 전체 기준으로 낸다.
        # (head(15) 결과를 합산하면 낭비 광고비가 실제의 일부만 표기된다)
        wasteful_all = kw_summary[(kw_summary["광고비"] > 0) & (kw_summary["매출"] == 0)]
        wasteful = wasteful_all.sort_values("광고비", ascending=False).head(15)
        result["키워드_낭비"] = wasteful.to_dict("records")

        result["총키워드수"] = len(kw_summary)
        result["매출발생키워드수"] = len(kw_summary[kw_summary["매출"] > 0])
        result["낭비키워드수"] = len(wasteful_all)
        result["낭비키워드광고비"] = int(wasteful_all["광고비"].sum()) if not wasteful_all.empty else 0
    else:
        result["키워드_매출순"] = []
        result["키워드_클릭순"] = []
        result["키워드_노출순"] = []
        result["키워드_고효율"] = []
        result["키워드_낭비"] = []
        result["총키워드수"] = 0
        result["매출발생키워드수"] = 0
        result["낭비키워드수"] = 0
        result["낭비키워드광고비"] = 0

    # ---- 캠페인별 분석 ----
    campaign = kw_df.groupby("캠페인명").agg(
        노출수=("노출수", "sum"),
        클릭수=("클릭수", "sum"),
        광고비=("광고비", "sum"),
        주문수=("총 주문수(1일)", "sum"),
        매출=("총 전환매출액(1일)", "sum"),
    ).reset_index()
    campaign["CTR"] = (campaign["클릭수"] / campaign["노출수"] * 100).round(2).fillna(0)
    campaign["ROAS"] = (campaign["매출"] / campaign["광고비"] * 100).round(1).fillna(0)
    campaign = campaign.sort_values("광고비", ascending=False)
    result["캠페인별"] = campaign.to_dict("records")

    # ---- 총계 ----
    result["총노출수"] = int(kw_df["노출수"].sum())
    result["총클릭수"] = int(kw_df["클릭수"].sum())
    result["총광고비"] = int(kw_df["광고비"].sum())
    result["총주문수"] = int(kw_df["총 주문수(1일)"].sum())
    result["총매출"] = int(kw_df["총 전환매출액(1일)"].sum())
    result["평균CTR"] = round(result["총클릭수"] / result["총노출수"] * 100, 2) if result["총노출수"] > 0 else 0
    result["평균CPC"] = round(result["총광고비"] / result["총클릭수"]) if result["총클릭수"] > 0 else 0
    result["전체ROAS"] = round(result["총매출"] / result["총광고비"] * 100, 1) if result["총광고비"] > 0 else 0

    return result


def analyze_data(ad_df: pd.DataFrame = None, daily_df: pd.DataFrame = None, product_df: pd.DataFrame = None,
                 kw_df: pd.DataFrame = None, target_sales: int = None, kw_trend_df: pd.DataFrame = None,
                 next_target_sales: int = None) -> dict:
    """데이터를 종합 분석하여 리포트용 딕셔너리 반환"""

    result = {}
    # 기간 이름표 · 한 달 안이면 「2026년 10월」, 두 달에 걸치면 기간 그대로 「10/21~11/09」
    _first_d = daily_df["날짜"].min()
    _last_d = daily_df["날짜"].max()
    if (_first_d.year, _first_d.month) == (_last_d.year, _last_d.month):
        month_str = _first_d.strftime("%Y년 %m월")
    else:
        month_str = f'{_first_d.strftime("%m/%d")}~{_last_d.strftime("%m/%d")}'
    # 다음 달 · 기간 끝 날짜가 든 달의 다음 달
    next_month = _last_d + pd.DateOffset(months=1)
    next_month_str = f"{next_month.month}월"
    result["월"] = month_str
    result["다음월"] = next_month_str
    result["기간"] = f'{daily_df["날짜"].min().strftime("%Y.%m.%d")} ~ {daily_df["날짜"].max().strftime("%Y.%m.%d")}'
    result["일수"] = len(daily_df)
    # 0으로 채운 빈 칸이 있었다면 그대로 넘긴다. 리포트 맨 위에 표시된다.
    result["결측"] = [dict(g) for g in DATA_GAPS]

    # ========== 1. 광고 성과 분석 ==========
    ad = {}
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    if ad_df is not None and not ad_df.empty:
        ad["사용"] = True
        ad["총광고비"] = int(ad_df["광고비"].sum())
        ad["총광고매출"] = int(ad_df["광고매출"].sum())
        # ROAS는 판매 분석 후 전체매출/광고비 기준으로 재계산 (아래에서 설정)
        ad["ROAS"] = 0
        ad["일평균광고비"] = int(ad["총광고비"] / len(ad_df))
        ad["일평균광고매출"] = int(ad["총광고매출"] / len(ad_df))
        ad["광고비최대일"] = ad_df.loc[ad_df["광고비"].idxmax(), "날짜"].strftime("%m/%d")
        ad["광고비최대금액"] = int(ad_df["광고비"].max())
        ad["광고비최소일"] = ad_df.loc[ad_df["광고비"].idxmin(), "날짜"].strftime("%m/%d")
        ad["광고비최소금액"] = int(ad_df["광고비"].min())
        ad["ROAS최고일"] = ad_df.loc[ad_df["ROAS"].idxmax(), "날짜"].strftime("%m/%d")
        ad["ROAS최고값"] = float(ad_df["ROAS"].max())
        ad["ROAS최저일"] = ad_df.loc[ad_df["ROAS"].idxmin(), "날짜"].strftime("%m/%d")
        ad["ROAS최저값"] = float(ad_df["ROAS"].min())

        # 주간별 광고 성과
        weekly_ad = ad_df.groupby("주차").agg(
            광고비=("광고비", "sum"),
            광고매출=("광고매출", "sum"),
        ).reset_index()
        weekly_ad["ROAS"] = (weekly_ad["광고매출"] / weekly_ad["광고비"] * 100).round(1)
        ad["주간별"] = weekly_ad.to_dict("records")

        # 요일별 광고 효율
        weekday_ad = ad_df.groupby("요일").agg(
            광고비=("광고비", "mean"),
            광고매출=("광고매출", "mean"),
        ).reset_index()
        weekday_ad["요일순서"] = weekday_ad["요일"].map({d: i for i, d in enumerate(weekday_order)})
        weekday_ad = weekday_ad.sort_values("요일순서")
        weekday_ad["ROAS"] = (weekday_ad["광고매출"] / weekday_ad["광고비"] * 100).round(1)
        ad["요일별"] = weekday_ad.to_dict("records")

        # 일별 데이터 (차트용)
        ad["일별"] = ad_df[["날짜", "광고비", "광고매출", "ROAS"]].copy()
        ad["일별"]["날짜str"] = ad["일별"]["날짜"].dt.strftime("%m/%d")
        ad["일별"] = ad["일별"].to_dict("records")
    else:
        ad["사용"] = False
        ad["총광고비"] = 0
        ad["총광고매출"] = 0
        ad["ROAS"] = 0
        ad["일평균광고비"] = 0
        ad["일평균광고매출"] = 0
        ad["주간별"] = []
        ad["요일별"] = []
        ad["일별"] = []

    result["광고"] = ad

    # ========== 2. 판매 성과 분석 ==========
    sales = {}
    sales["총매출"] = int(daily_df["매출"].sum())
    sales["총주문"] = int(daily_df["주문"].sum())
    sales["총판매량"] = int(daily_df["판매량"].sum())
    sales["총방문자"] = int(daily_df["방문자"].sum())
    sales["총조회"] = int(daily_df["조회"].sum())
    sales["총장바구니"] = int(daily_df["장바구니"].sum())
    # 일별 전환율의 단순 평균이 아니라 총주문/총조회 (주간·일자별 합계와 같은 식)
    # 방문자·조회 0인 날(전환율제외)의 주문은 나누는 값이 없으니 분자에서도 뺀다
    if "전환율제외" not in daily_df.columns:
        daily_df["전환율제외"] = False
    _cvr_df = daily_df[~daily_df["전환율제외"]]
    _tot_view = float(_cvr_df["조회"].sum())
    sales["평균전환율"] = round(float(_cvr_df["주문"].sum()) / _tot_view * 100, 2) if _tot_view else 0.0
    sales["전환율제외일"] = daily_df.loc[daily_df["전환율제외"], "날짜"].dt.strftime("%m/%d").tolist()
    sales["일평균매출"] = int(sales["총매출"] / len(daily_df))
    sales["일평균주문"] = round(sales["총주문"] / len(daily_df), 1)
    sales["일평균방문자"] = int(sales["총방문자"] / len(daily_df))

    # 퍼널 분석
    sales["조회당장바구니율"] = round(sales["총장바구니"] / sales["총조회"] * 100, 2) if sales["총조회"] > 0 else 0
    sales["장바구니당주문율"] = round(sales["총주문"] / sales["총장바구니"] * 100, 2) if sales["총장바구니"] > 0 else 0
    sales["방문당주문율"] = round(sales["총주문"] / sales["총방문자"] * 100, 2) if sales["총방문자"] > 0 else 0

    # 매출 최고/최저일
    sales["매출최고일"] = daily_df.loc[daily_df["매출"].idxmax(), "날짜"].strftime("%m/%d")
    sales["매출최고금액"] = int(daily_df["매출"].max())
    sales["매출최저일"] = daily_df.loc[daily_df["매출"].idxmin(), "날짜"].strftime("%m/%d")
    sales["매출최저금액"] = int(daily_df["매출"].min())

    # 전환율 최고/최저일
    sales["전환율최고일"] = daily_df.loc[daily_df["구매전환율"].idxmax(), "날짜"].strftime("%m/%d")
    sales["전환율최고값"] = float(daily_df["구매전환율"].max())

    # 주간별 판매 성과
    weekly_sales = daily_df.groupby("주차").agg(
        매출=("매출", "sum"),
        주문=("주문", "sum"),
        방문자=("방문자", "sum"),
        조회=("조회", "sum"),
        일수=("주문", "size"),
    ).reset_index()
    # 일별 전환율의 단순 평균이 아니라 주간 총주문/총조회로 계산한다 (합계 행과 같은 식)
    # 방문자·조회 0인 날의 주문은 분자에서 뺀다
    _wk_cvr = _cvr_df.groupby("주차").agg(주문=("주문", "sum"), 조회=("조회", "sum"))
    weekly_sales["전환율"] = weekly_sales["주차"].map(
        lambda w: round(_wk_cvr.loc[w, "주문"] / _wk_cvr.loc[w, "조회"] * 100, 2)
        if w in _wk_cvr.index and _wk_cvr.loc[w, "조회"] > 0 else 0.0)
    sales["주간별"] = weekly_sales.to_dict("records")

    # 요일별 판매 성과
    weekday_sales = daily_df.groupby("요일").agg(
        매출=("매출", "mean"),
        주문=("주문", "mean"),
        방문자=("방문자", "mean"),
    ).reset_index()
    # 요일 전환율은 방문자·조회 0인 날을 빼고 평균한다
    _wd_cvr = _cvr_df.groupby("요일")["구매전환율"].mean()
    weekday_sales["전환율"] = weekday_sales["요일"].map(_wd_cvr).fillna(0)
    weekday_sales["요일순서"] = weekday_sales["요일"].map({d: i for i, d in enumerate(weekday_order)})
    weekday_sales = weekday_sales.sort_values("요일순서")
    sales["요일별"] = weekday_sales.to_dict("records")

    # 일별 데이터 (차트용)
    daily_chart = daily_df[["날짜", "방문자", "조회", "장바구니", "주문", "구매전환율", "판매량", "매출", "전환율제외"]].copy()
    daily_chart["날짜str"] = daily_chart["날짜"].dt.strftime("%m/%d")
    sales["일별"] = daily_chart.to_dict("records")

    result["판매"] = sales

    # ========== ROAS 재계산 (전체 매출 / 총 광고비) ==========
    if ad["사용"] and ad["총광고비"] > 0:
        ad["ROAS"] = round(sales["총매출"] / ad["총광고비"] * 100, 1)

    # ========== 월간 예상치 (일평균 × 해당월 일수) ==========
    first_date = daily_df["날짜"].min()
    days_in_month = calendar.monthrange(first_date.year, first_date.month)[1]
    data_days = len(daily_df)
    # 예상 기간 이름표 · 첫날부터 그 달 일수만큼. 한 달 안이면 「2026년 10월」, 아니면 「10/21~11/20」
    _fc_end = first_date + pd.Timedelta(days=days_in_month - 1)
    if first_date.day == 1:
        fc_label = first_date.strftime("%Y년 %m월")
    else:
        fc_label = f'{first_date.strftime("%m/%d")}~{_fc_end.strftime("%m/%d")}'

    forecast = {}
    forecast["기간라벨"] = fc_label
    forecast["해당월일수"] = days_in_month
    forecast["데이터일수"] = data_days
    forecast["잔여일수"] = max(0, days_in_month - data_days)

    # 예상 매출 = 가중 일평균 × 해당월 일수
    # 최근 7일 가중치 적용 (데이터 7일 이상일 때): 전체평균 50% + 최근7일평균 50%
    # 주문·방문자는 버리지 않고 반올림한다 (일평균은 소수 그대로 써서 마지막에 한 번만 반올림)
    _avg_orders = sales["총주문"] / data_days
    _avg_visitors = sales["총방문자"] / data_days
    if data_days >= 7:
        recent_7 = daily_df.sort_values("날짜").tail(7)
        recent_avg_sales = int(recent_7["매출"].mean())
        recent_avg_orders = float(recent_7["주문"].mean())
        recent_avg_visitors = float(recent_7["방문자"].mean())
        weighted_avg_sales = int(sales["일평균매출"] * 0.5 + recent_avg_sales * 0.5)
        weighted_avg_orders = _avg_orders * 0.5 + recent_avg_orders * 0.5
        weighted_avg_visitors = _avg_visitors * 0.5 + recent_avg_visitors * 0.5
    else:
        weighted_avg_sales = sales["일평균매출"]
        weighted_avg_orders = _avg_orders
        weighted_avg_visitors = _avg_visitors

    remaining_days = max(0, days_in_month - data_days)
    forecast["예상매출"] = int(sales["총매출"] + weighted_avg_sales * remaining_days)
    forecast["예상주문"] = int(round(sales["총주문"] + weighted_avg_orders * remaining_days))
    forecast["예상방문자"] = int(round(sales["총방문자"] + weighted_avg_visitors * remaining_days))

    # 예상 광고비/광고매출 (광고 데이터 있을 때만)
    if ad["사용"]:
        forecast["예상광고비"] = int(ad["총광고비"] + ad["일평균광고비"] * remaining_days)
        forecast["예상광고매출"] = int(ad["총광고매출"] + ad["일평균광고매출"] * remaining_days)
        # 예상 ROAS = 예상 전체 매출 / 예상 광고비
        forecast["예상ROAS"] = round(forecast["예상매출"] / forecast["예상광고비"] * 100, 1) if forecast["예상광고비"] > 0 else 0
    else:
        forecast["예상광고비"] = 0
        forecast["예상광고매출"] = 0
        forecast["예상ROAS"] = 0

    result["예상"] = forecast

    # ========== 목표 매출 달성 분석 ==========
    if target_sales and target_sales > 0:
        tgt = {}
        tgt["기간라벨"] = fc_label
        tgt["목표매출"] = target_sales
        tgt["현재매출"] = sales["총매출"]
        tgt["달성률"] = round(sales["총매출"] / target_sales * 100, 1)
        tgt["잔여매출"] = max(0, target_sales - sales["총매출"])
        tgt["잔여일수"] = max(0, days_in_month - data_days)

        # 최근 3일 분석
        recent = daily_df.sort_values("날짜").tail(3)
        tgt["최근3일매출"] = [
            {"날짜": r["날짜"].strftime("%m/%d"), "매출": int(r["매출"])}
            for _, r in recent.iterrows()
        ]
        tgt["최근3일평균"] = int(recent["매출"].mean())

        # 목표 일매출
        if tgt["잔여일수"] > 0:
            tgt["목표일매출"] = int(tgt["잔여매출"] / tgt["잔여일수"])
            tgt["목표대비최근비율"] = round(tgt["목표일매출"] / tgt["최근3일평균"] * 100, 1) if tgt["최근3일평균"] > 0 else 0
        else:
            tgt["목표일매출"] = 0
            tgt["목표대비최근비율"] = 0

        # 광고 전략 (광고 데이터가 있을 때)
        if ad["사용"] and ad["총광고비"] > 0:
            current_daily_ad = ad["일평균광고비"]
            # 목표 달성을 위한 필요 일매출 증가율
            growth_needed = tgt["목표일매출"] / sales["일평균매출"] if sales["일평균매출"] > 0 else 0
            # 남은 기간 하루 광고비 = 지금 하루 광고비 × (남은 기간 하루 필요 매출 ÷ 지금 하루 매출)
            #                     = 남은 기간 하루 필요 매출 ÷ 지금 ROAS(전체 매출 기준)
            # 지금 효율 그대로 남은 날에 필요한 매출만 낼 때 드는 하루 광고비다.
            # 지금보다 적게 나오면 「광고비를 줄이라」 가 아니라 「지금 속도로 목표를 넘긴다」 는 뜻이다.
            tgt["광고전략"] = {
                "현재일평균광고비": current_daily_ad,
                "권장일광고비": int(current_daily_ad * growth_needed),
                "매출증가필요율": round((growth_needed - 1) * 100, 1),
                "현재ROAS": ad["ROAS"],
            }

        result["목표"] = tgt
    else:
        result["목표"] = None

    # ========== 3. 제품별 분석 ==========
    products = {}

    # 상품명 기준 그룹핑 (동일 상품의 옵션/판매방식 합산)
    product_summary = product_df.groupby("상품명").agg(
        매출=("매출(원)", "sum"),
        주문=("주문", "sum"),
        판매량=("판매량", "sum"),
        방문자=("방문자", "sum"),
        조회=("조회", "sum"),
        장바구니=("장바구니", "sum"),
        총매출=("총 매출(원)", "sum"),
        총판매수=("총 판매수", "sum"),
        취소금액=("총 취소 금액(원)", "sum"),
        취소수=("총 취소된 상품수", "sum"),
    ).reset_index()
    # 전환율은 리포트 전체에서 한 가지 식 · 주문 ÷ 조회
    product_summary["전환율"] = product_summary.apply(
        lambda r: round(r["주문"] / r["조회"] * 100, 2) if r["조회"] > 0 else 0,
        axis=1,
    )
    product_summary = product_summary.sort_values("매출", ascending=False)
    products["상품별요약"] = product_summary.to_dict("records")

    # 아이템위너 분석
    if "아이템위너비율" in product_df.columns:
        iw = product_df[["상품명", "아이템위너비율", "매출(원)"]].copy()
        iw_summary = iw.groupby("상품명").agg(
            아이템위너비율=("아이템위너비율", "mean"),
            매출=("매출(원)", "sum"),
        ).reset_index().sort_values("매출", ascending=False)
        products["아이템위너"] = iw_summary.to_dict("records")
        products["평균아이템위너비율"] = round(iw["아이템위너비율"].mean(), 1)
    else:
        products["아이템위너"] = []
        products["평균아이템위너비율"] = 0

    # 판매방식별 분석
    channel_summary = product_df.groupby("판매방식").agg(
        매출=("매출(원)", "sum"),
        주문=("주문", "sum"),
        판매량=("판매량", "sum"),
        방문자=("방문자", "sum"),
    ).reset_index()
    products["판매방식별"] = channel_summary.to_dict("records")

    # 카테고리별 분석
    category_summary = product_df.groupby("카테고리").agg(
        매출=("매출(원)", "sum"),
        주문=("주문", "sum"),
        방문자=("방문자", "sum"),
    ).reset_index()
    products["카테고리별"] = category_summary.to_dict("records")

    # 옵션별 상세 (상위 매출순)
    option_detail = product_df[["옵션명", "상품명", "판매방식", "매출(원)", "주문", "판매량",
                                 "방문자", "조회", "장바구니", "구매전환율", "아이템위너비율"]].copy()
    option_detail = option_detail.sort_values("매출(원)", ascending=False)
    products["옵션별상세"] = option_detail.to_dict("records")

    # 취소 분석
    cancel_products = product_df[product_df["총 취소된 상품수"] < 0].copy()
    if not cancel_products.empty:
        products["취소현황"] = cancel_products[["상품명", "옵션명", "총 취소 금액(원)", "총 취소된 상품수"]].to_dict("records")
    else:
        products["취소현황"] = []

    result["제품"] = products

    # ========== 4. 광고 vs 판매 교차 분석 ==========
    cross = {}
    cross["광고매출합계"] = ad["총광고매출"]
    cross["인사이트매출합계"] = sales["총매출"]
    cross["광고비대비매출비율"] = round(sales["총매출"] / ad["총광고비"] * 100, 1) if ad["총광고비"] > 0 else 0
    cross["순이익추정"] = sales["총매출"] - ad["총광고비"]

    if ad_df is not None and not ad_df.empty:
        # 일별 광고비 vs 판매 상관관계
        merged = pd.merge(
            ad_df[["날짜", "광고비", "광고매출"]],
            daily_df[["날짜", "방문자", "주문", "매출"]],
            on="날짜",
            how="inner",
        )
        if len(merged) > 2:
            cross["광고비_방문자_상관"] = round(merged["광고비"].corr(merged["방문자"]), 3)
            cross["광고비_주문_상관"] = round(merged["광고비"].corr(merged["주문"]), 3)
            cross["광고비_매출_상관"] = round(merged["광고비"].corr(merged["매출"]), 3)
        else:
            cross["광고비_방문자_상관"] = 0
            cross["광고비_주문_상관"] = 0
            cross["광고비_매출_상관"] = 0

        # 일별 통합 데이터 (광고 + 판매 병합)
        merged_daily = pd.merge(
            ad_df[["날짜", "광고비", "광고매출", "ROAS"]],
            daily_df[["날짜", "방문자", "조회", "장바구니", "주문", "구매전환율", "판매량", "매출", "전환율제외"]],
            on="날짜",
            how="outer",
        ).fillna(0).sort_values("날짜")
        merged_daily["전환율제외"] = merged_daily["전환율제외"].astype(bool)
        merged_daily["날짜str"] = merged_daily["날짜"].dt.strftime("%m/%d")
        merged_daily["요일"] = merged_daily["날짜"].dt.day_name()
        cross["일별통합"] = merged_daily.to_dict("records")
    else:
        cross["광고비_방문자_상관"] = 0
        cross["광고비_주문_상관"] = 0
        cross["광고비_매출_상관"] = 0
        cross["일별통합"] = []

    result["교차분석"] = cross

    # ========== 5. 키워드/지면 분석 (데이터 있을 때만) ==========
    if kw_df is not None and not kw_df.empty:
        result["키워드"] = analyze_keyword_data(kw_df)
    else:
        result["키워드"] = None

    # ========== 제품 트렌드 분석 (키워드 데이터 기반 날짜별 상품 매출) ==========
    result["제품트렌드"] = analyze_product_trends(kw_trend_df if kw_trend_df is not None else kw_df, products)

    # ========== 6. 광고 운영 분석 & 전략 (키워드 데이터 기반) ==========
    ad_ops = {}
    kw_result = result.get("키워드")
    if kw_result and kw_result.get("총광고비", 0) > 0:
        ad_ops["사용"] = True
        # 전체 광고 데이터(크리에이티브+키워드 합산)가 있으면 그 기준으로 통일
        # (Executive Summary 등 다른 섹션과 총광고비/ROAS 불일치 방지)
        if result["광고"].get("사용"):
            ad_ops["총광고비"] = result["광고"]["총광고비"]
            ad_ops["광고전환매출"] = result["광고"]["총광고매출"]
            ad_ops["ROAS_전체매출"] = result["광고"]["ROAS"]
        else:
            ad_ops["총광고비"] = kw_result["총광고비"]
            ad_ops["광고전환매출"] = kw_result["총매출"]
            ad_ops["ROAS_전체매출"] = round(sales["총매출"] / kw_result["총광고비"] * 100, 1) if kw_result["총광고비"] > 0 else 0
        ad_ops["전체매출"] = sales["총매출"]
        ad_ops["ROAS_광고전환"] = kw_result["전체ROAS"]
        # 노출/클릭/CTR/CPC/CVR은 검색광고(매출 성장 광고 보고서) 기준
        ad_ops["노출수"] = kw_result["총노출수"]
        ad_ops["클릭수"] = kw_result["총클릭수"]
        ad_ops["CTR"] = kw_result["평균CTR"]
        ad_ops["CPC"] = kw_result["평균CPC"]
        ad_ops["총주문수"] = kw_result.get("총주문수", 0)
        ad_ops["CVR"] = round(ad_ops["총주문수"] / ad_ops["클릭수"] * 100, 2) if ad_ops["클릭수"] > 0 else 0

        days = result["일수"]
        ad_ops["일평균광고비"] = int(ad_ops["총광고비"] / days) if days > 0 else 0
        ad_ops["일평균매출"] = sales["일평균매출"]

        # ---- 다음월 목표 설정 (룰 기반) ----
        # 월매출 범위는 항상 "월광고비 범위 × 목표ROAS"로 산출한다.
        # 광고비/매출 범위를 독립적인 축소율로 만들면 상·하한이 어긋나
        # "매출 ÷ ROAS ≠ 광고비"가 되므로(과거 버그), 동일 기준으로 묶어 일치를 보장.
        target = {}
        current_roas = ad_ops["ROAS_전체매출"]
        _st = SETTINGS()
        # 목표 ROAS · CLAUDE.md 에 적혀 있으면 그 값, 없으면 「양호 기준」과 「지금 + 50」 중 큰 값
        target["목표ROAS"] = int(_st["목표_ROAS_pct"]) if _st["목표_ROAS_pct"] else max(int(_st["ROAS_양호_기준_pct"]), int(current_roas + 50))
        if next_target_sales and next_target_sales > 0:
            # 사용자가 다음달 목표 매출을 명시한 경우: 그 값을 단일 기준으로 고정.
            # 월광고비 = 목표매출 ÷ 목표ROAS 로 산출해 "매출 ÷ ROAS = 광고비" 일치 보장.
            target["월매출"] = next_target_sales
            target["월광고비"] = int(next_target_sales * 100 / target["목표ROAS"])
            target["월매출범위"] = fmt_money_simple(next_target_sales)
            target["월광고비범위"] = fmt_money_simple(target["월광고비"])
        else:
            # 룰 기반 추정: 월매출 범위는 항상 "월광고비 범위 × 목표ROAS"로 산출.
            # 운영 플랜의 예산 판정과 같은 기준 · 양호 이상이면 늘리고, 보통이면 지금 하루 광고비를 유지하고, 위험이면 줄인다
            if current_roas >= SETTINGS()["ROAS_양호_기준_pct"]:
                ad_low = int(ad_ops["총광고비"] * 2)
                ad_high = int(ad_ops["총광고비"] * 2.5)
            elif current_roas >= SETTINGS()["ROAS_위험_기준_pct"]:
                _nm = daily_df["날짜"].max() + pd.DateOffset(months=1)
                ad_low = ad_high = int(ad_ops["일평균광고비"] * calendar.monthrange(_nm.year, _nm.month)[1])
            else:
                ad_low = ad_high = ad_ops["총광고비"]
            target["월광고비"] = ad_high
            sales_low = int(ad_low * target["목표ROAS"] / 100)
            sales_high = int(ad_high * target["목표ROAS"] / 100)
            target["월매출"] = sales_high
            if ad_low != ad_high:
                target["월광고비범위"] = f'{fmt_money_simple(ad_low)}~{fmt_money_simple(ad_high)}'
                target["월매출범위"] = f'{fmt_money_simple(sales_low)}~{fmt_money_simple(sales_high)}'
            else:
                target["월광고비범위"] = fmt_money_simple(ad_high)
                target["월매출범위"] = fmt_money_simple(sales_high)
        ad_ops["목표"] = target

        # ---- 운영 인사이트 ----
        op_insights = []
        efficiency = round(ad_ops["전체매출"] / ad_ops["총광고비"], 1) if ad_ops["총광고비"] > 0 else 0
        op_insights.append(f'광고비 {fmt_money_simple(ad_ops["총광고비"])}으로 전체 매출 {fmt_money_simple(ad_ops["전체매출"])}을 발생시킨 상태')
        # 판정은 핵심 인사이트 · 개선사항 · 운영 플랜과 같은 기준(CLAUDE.md 두 줄)으로 한다
        _risk = SETTINGS()["ROAS_위험_기준_pct"]
        _good = SETTINGS()["ROAS_양호_기준_pct"]
        if current_roas >= _good:
            op_insights.append(f"광고비 1원당 전체 매출 {efficiency}원 · ROAS {current_roas}%로 양호 기준 {_good}% 이상")
        elif current_roas >= _risk:
            op_insights.append(f"광고비 1원당 전체 매출 {efficiency}원 · ROAS {current_roas}%로 보통 수준 (위험 기준 {_risk}% 이상, 양호 기준 {_good}% 미만)")
        else:
            op_insights.append(f"광고비 1원당 전체 매출 {efficiency}원 · ROAS {current_roas}%로 위험 기준 {_risk}% 미만, 적자 위험")
        if ad_ops["CVR"] >= 2:
            op_insights.append(f'검색광고 전환율(CVR · 주문 ÷ 클릭 · 1일 전환 기준)이 {ad_ops["CVR"]}%로 안정적이며, 상품 경쟁력은 검증된 상태')
        elif ad_ops["CVR"] >= 1:
            op_insights.append(f'검색광고 전환율(CVR · 주문 ÷ 클릭 · 1일 전환 기준)이 {ad_ops["CVR"]}%로 보통 수준, 상세페이지 최적화로 개선 여지 있음')
        else:
            op_insights.append(f'검색광고 전환율(CVR · 주문 ÷ 클릭 · 1일 전환 기준)이 {ad_ops["CVR"]}%로 낮은 수준, 상품/상세페이지 전반적 점검 필요')
        ad_ops["인사이트"] = op_insights

        # ---- 목표 달성 운영 방향 ----
        directions = []
        directions.append("전체 캠페인을 고르게 키우는 방식은 비효율")
        directions.append("이미 성과가 검증된 캠페인과 상품에 예산을 집중")
        directions.append("장기간 성과가 없는 캠페인은 과감히 정리")
        ad_ops["운영방향"] = directions

        # ---- 실행 체크포인트 ----
        checkpoints = []
        checkpoints.append("캠페인별 성과 표에서 광고 전환 ROAS가 높은 캠페인 예산 우선 증액")
        checkpoints.append("오래 돌려도 성과가 안 나는 캠페인 정리")
        checkpoints.append("캠페인 수를 줄여 남은 캠페인이 빨리 자리 잡게 하기")
        checkpoints.append(f'주 1회 ROAS(전체 매출 기준)가 목표 {target["목표ROAS"]}%에 가까워지는지 보고 예산 재배분 점검')
        ad_ops["체크포인트"] = checkpoints
    else:
        ad_ops["사용"] = False
    result["광고운영"] = ad_ops

    # ========== 7. 개선사항 & 운영플랜 자동 생성 ==========
    result["개선사항"] = generate_improvements(result)
    result["운영플랜"] = generate_operation_plan(result)

    # ========== 7. 핵심 인사이트 & 필수 확인사항 ==========
    result["인사이트"] = generate_key_insights(result)
    result["필수확인"] = generate_must_checks(result)

    return result


def generate_key_insights(data: dict) -> list:
    """데이터 기반 핵심 인사이트 자동 생성"""
    insights = []
    ad = data["광고"]
    sales = data["판매"]
    products = data["제품"]
    cross = data["교차분석"]

    day_kr = {
        "Monday": "월", "Tuesday": "화", "Wednesday": "수",
        "Thursday": "목", "Friday": "금", "Saturday": "토", "Sunday": "일",
    }

    # 1. 매출 구조 인사이트
    top_products = [p for p in products["상품별요약"] if p["매출"] > 0]
    if top_products:
        top = top_products[0]
        # 분자(제품 파일)와 분모(일별 합계)의 기간이 다르면 비율이 부풀려진다.
        # 제품 파일은 기간 합산이라 날짜 절단이 안 되므로, 제품 비율은 제품 파일 합계로 나눈다.
        product_total = sum(p["매출"] for p in products["상품별요약"]) or sales["총매출"]
        top_ratio = round(top["매출"] / product_total * 100, 1) if product_total > 0 else 0
        if top_ratio > SETTINGS()["매출편중_기준_pct"]:
            insights.append({
                "유형": "warning",
                "제목": "매출 편중 위험",
                "내용": f'전체 매출의 {top_ratio}%가 "{top["상품명"]}" 단일 상품에 집중되어 있습니다. 해당 제품의 판매 이슈 발생 시 전체 매출에 큰 타격이 예상됩니다.',
            })
        elif top_ratio > 50:
            insights.append({
                "유형": "info",
                "제목": "주력 상품 매출 비중",
                "내용": f'"{top["상품명"]}"이 전체 매출의 {top_ratio}%를 차지합니다. 주력 상품 유지 + 신규 상품 육성 전략이 필요합니다.',
            })

    # 2. 광고 효율 인사이트 (광고 데이터 있을 때만)
    if ad.get("사용"):
        if ad["ROAS"] >= SETTINGS()["ROAS_양호_기준_pct"]:
            insights.append({
                "유형": "positive",
                "제목": f'ROAS(전체매출 기준) {ad["ROAS"]}% 달성',
                "내용": f'광고비 {fmt_money_simple(ad["총광고비"])} 투자 대비 전체 매출 {fmt_money_simple(sales["총매출"])}을 기록했습니다 (광고 전환매출은 14일 기준 {fmt_money_simple(ad["총광고매출"])}). 현재 광고 효율이 양호하며, 예산 증액 시 추가 매출 확보가 기대됩니다.',
            })
        elif ad["ROAS"] < SETTINGS()["ROAS_위험_기준_pct"]:
            insights.append({
                "유형": "danger",
                "제목": f'광고 ROAS {ad["ROAS"]}%로 적자 위험',
                "내용": f'광고비 {fmt_money_simple(ad["총광고비"])} 대비 전체 매출이 {fmt_money_simple(sales["총매출"])}으로, ROAS(전체 매출 기준)가 위험 기준 {SETTINGS()["ROAS_위험_기준_pct"]}%에 못 미칩니다 (광고로 생긴 매출은 14일 기준 {fmt_money_simple(ad["총광고매출"])}). 수익성 확보를 위해 저효율 캠페인 즉시 점검이 필요합니다.',
            })

    # 3. 전환율 인사이트 - 퍼널 분석
    funnel_drop = round((1 - sales["총주문"] / sales["총방문자"]) * 100, 1) if sales["총방문자"] > 0 else 0
    cart_to_order = sales["장바구니당주문율"]
    view_to_cart = sales["조회당장바구니율"]
    if view_to_cart < 5:
        insights.append({
            "유형": "warning",
            "제목": f"조회 대비 장바구니 전환율 {view_to_cart}%로 낮음",
            "내용": f"총 {sales['총조회']:,}회 조회 중 장바구니 추가는 {sales['총장바구니']:,}건에 불과합니다. 상품 상세페이지의 매력도(이미지, 가격, 리뷰) 점검이 시급합니다.",
        })

    # 4. 매출 추세 인사이트 (전반기 vs 후반기)
    daily = sales["일별"]
    mid = len(daily) // 2
    first_half_revenue = sum(d["매출"] for d in daily[:mid])
    second_half_revenue = sum(d["매출"] for d in daily[mid:])
    if second_half_revenue > first_half_revenue * 1.2:
        growth = round((second_half_revenue / first_half_revenue - 1) * 100, 1) if first_half_revenue > 0 else 0
        insights.append({
            "유형": "positive",
            "제목": f"후반기 매출 {growth}% 성장",
            "내용": f"기간 전반기 매출 {fmt_money_simple(first_half_revenue)} → 후반기 {fmt_money_simple(second_half_revenue)}으로 상승 추세입니다. 현재 전략이 효과를 내고 있습니다.",
        })
    elif first_half_revenue > second_half_revenue * 1.2:
        decline = round((1 - second_half_revenue / first_half_revenue) * 100, 1) if first_half_revenue > 0 else 0
        insights.append({
            "유형": "danger",
            "제목": f"후반기 매출 {decline}% 하락",
            "내용": f"기간 전반기 매출 {fmt_money_simple(first_half_revenue)} → 후반기 {fmt_money_simple(second_half_revenue)}으로 하락 추세입니다. 원인 파악 및 대응이 필요합니다.",
        })

    # 5. 취소/반품 인사이트
    cancel_data = products.get("취소현황", [])
    if cancel_data:
        total_cancel_amount = sum(abs(c["총 취소 금액(원)"]) for c in cancel_data)
        # 취소 금액도 제품 파일 출처이므로 분모를 제품 파일 합계로 맞춘다.
        product_total = sum(p["매출"] for p in products["상품별요약"]) or sales["총매출"]
        cancel_ratio = round(total_cancel_amount / product_total * 100, 1) if product_total > 0 else 0
        if cancel_ratio > 5:
            insights.append({
                "유형": "danger",
                "제목": f"취소/반품율 {cancel_ratio}% - 즉시 대응 필요",
                "내용": f"총 취소 금액 {fmt_money_simple(int(total_cancel_amount))}으로 매출의 {cancel_ratio}%에 해당합니다. 취소 사유 분석 및 상품 품질/설명 개선이 시급합니다.",
            })

    # 6. 광고-매출 연관성 인사이트 (광고 데이터 있을 때만)
    if ad.get("사용") and cross["광고비_매출_상관"] < 0.2:
        insights.append({
            "유형": "warning",
            "제목": "광고비 증가가 매출로 연결되지 않음",
            "내용": f'광고비와 매출 간 상관계수가 {cross["광고비_매출_상관"]}로 매우 낮습니다. 광고 타겟이 실제 구매 고객층과 일치하는지, 유입 키워드가 적절한지 재점검이 필요합니다.',
        })

    # 7. 요일별 패턴 인사이트
    weekday_sales = sales["요일별"]
    best_day = max(weekday_sales, key=lambda x: x["매출"])
    worst_day = min(weekday_sales, key=lambda x: x["매출"])
    best_name = day_kr.get(best_day["요일"], best_day["요일"])
    worst_name = day_kr.get(worst_day["요일"], worst_day["요일"])
    if best_day["매출"] > worst_day["매출"] * 2 and worst_day["매출"] > 0:
        insights.append({
            "유형": "info",
            "제목": f"요일별 매출 편차 큼 ({best_name}요일 > {worst_name}요일)",
            "내용": f"{best_name}요일 평균 매출이 {worst_name}요일 대비 2배 이상 높습니다. 고매출 요일에 광고비를 집중 배분하면 효율을 높일 수 있습니다.",
        })

    return insights


def generate_must_checks(data: dict) -> list:
    """이번 달 필수 확인사항 자동 생성"""
    checks = []
    ad = data["광고"]
    sales = data["판매"]
    products = data["제품"]
    cross = data["교차분석"]
    next_month = data["다음월"]

    # 1. 주력 상품 아이템위너 확인
    top_products = [p for p in products["상품별요약"] if p["매출"] > 0]
    if top_products:
        checks.append({
            "항목": "주력 상품 아이템위너 유지 여부",
            "설명": f'매출 1위 "{top_products[0]["상품명"]}"의 아이템위너 상태를 확인하세요. 아이템위너 상실 시 매출 급감이 예상됩니다.',
            "중요도": "필수",
        })

    # 2. 마이너스 매출 제품 확인
    negative_products = [p for p in products["상품별요약"] if p["매출"] < 0]
    if negative_products:
        names = ", ".join([f'"{p["상품명"]}"' for p in negative_products])
        checks.append({
            "항목": "마이너스 매출(반품 초과) 제품 점검",
            "설명": f"{names} 제품에서 판매보다 반품/취소가 많아 마이너스 매출이 발생했습니다. 상품 품질 및 고객 클레임을 확인하세요.",
            "중요도": "긴급",
        })

    # 3. 매출 0원 + 방문자 많은 제품
    # 라벨이 "10명 이상"이므로 필터도 >= 10 이어야 한다.
    # 과거 > 20 이라 같은 사안이 필수확인 1건 / 개선사항 3개로 갈렸다.
    zero_revenue_high_traffic = [p for p in products["상품별요약"] if p["매출"] <= 0 and p["방문자"] >= 10]
    if zero_revenue_high_traffic:
        names = ", ".join([f'"{p["상품명"]}"' for p in zero_revenue_high_traffic[:3]])
        checks.append({
            "항목": f"트래픽 유입 중 미전환 제품(방문 10명 이상) {len(zero_revenue_high_traffic)}건",
            "설명": f"{names} 등의 제품에 방문자가 유입되지만 구매가 발생하지 않습니다. 가격/재고/상세페이지를 확인하세요.",
            "중요도": "높음",
        })

    # 4. 광고비 대비 순이익 (광고 데이터 있을 때만)
    if ad.get("사용"):
        net_profit = cross["순이익추정"]
        if net_profit < 0:
            checks.append({
                "항목": "광고비가 매출보다 많음",
                "설명": f"매출({fmt_money_simple(sales['총매출'])}) - 광고비({fmt_money_simple(ad['총광고비'])}) = {fmt_money_simple(net_profit)}. 원가를 빼기 전부터 손해입니다. 광고비 조정이 필요합니다.",
                "중요도": "긴급",
            })
        else:
            profit_margin = round(net_profit / sales["총매출"] * 100, 1) if sales["총매출"] > 0 else 0
            checks.append({
                "항목": f"광고비를 뺀 매출 비율 {profit_margin}% 확인",
                "설명": f"매출 {fmt_money_simple(sales['총매출'])} - 광고비 {fmt_money_simple(ad['총광고비'])} = {fmt_money_simple(net_profit)}. 원가 · 수수료 · 배송비는 빠지지 않은 값입니다. 이것들을 뺀 실제 이익을 따로 확인하세요.",
                "중요도": "높음",
            })

    # 5. 전환율 하락 구간 확인
    daily = sales["일별"]
    low_cvr_days = [d for d in daily if d["구매전환율"] <= 0 and d["방문자"] > 50]
    if len(low_cvr_days) >= 3:
        dates = ", ".join([d["날짜str"] for d in low_cvr_days[:5]])
        checks.append({
            "항목": f"전환율 0% 이하 일수 {len(low_cvr_days)}일",
            "설명": f"{dates} 등의 날짜에 전환율이 0% 이하였습니다. 해당 시점의 재고 부족, 가격 변동, 경쟁사 프로모션 등을 확인하세요.",
            "중요도": "높음",
        })

    # 6. 다음달 시즌 대비
    checks.append({
        "항목": f"{next_month} 시즌 상품 전략 수립",
        "설명": f"{next_month} 계절/이벤트에 맞는 상품 구성 및 프로모션 계획을 사전에 준비하세요. 광고 소재 업데이트도 함께 진행하세요.",
        "중요도": "중간",
    })

    return checks


def fmt_money_simple(value: int) -> str:
    """인사이트 텍스트용 간단 금액 포맷"""
    if abs(value) >= 100000000:
        return f"{value / 100000000:,.1f}억원"
    if abs(value) >= 10000:
        man = value / 10000
        if man == int(man):
            return f"{int(man):,}만원"
        return f"{man:,.1f}만원"
    return f"{value:,}원"


def generate_improvements(data: dict) -> list:
    """데이터 기반 개선사항 자동 생성"""
    improvements = []
    ad = data["광고"]
    sales = data["판매"]
    products = data["제품"]
    cross = data["교차분석"]
    next_month = data["다음월"]

    # 1. ROAS 분석 (광고 데이터 있을 때만)
    if ad.get("사용"):
        if ad["ROAS"] < SETTINGS()["ROAS_위험_기준_pct"]:
            improvements.append({
                "카테고리": "광고 효율",
                "현황": f'ROAS(전체 매출 기준) {ad["ROAS"]}%로 위험 기준 {SETTINGS()["ROAS_위험_기준_pct"]}% 미만, 광고비 대비 매출 효율이 낮음',
                "개선안": "저효율 키워드 정리 및 고전환 키워드 집중 투자 필요. 광고 소재 A/B 테스트 진행 권장",
                "우선순위": "높음",
            })
        elif ad["ROAS"] < SETTINGS()["ROAS_양호_기준_pct"]:
            improvements.append({
                "카테고리": "광고 효율",
                "현황": f'ROAS(전체 매출 기준) {ad["ROAS"]}%로 보통 수준',
                "개선안": f"양호 기준 ROAS {SETTINGS()['ROAS_양호_기준_pct']}% 이상 달성을 위한 키워드 최적화 및 입찰가 조정 필요",
                "우선순위": "중간",
            })
        else:
            improvements.append({
                "카테고리": "광고 효율",
                "현황": f'ROAS(전체 매출 기준) {ad["ROAS"]}%로 양호한 수준',
                "개선안": "현재 캠페인 유지하면서 점진적 예산 확대 검토",
                "우선순위": "낮음",
            })

    # 2. 전환율 분석
    if sales["평균전환율"] < 1.5:
        improvements.append({
            "카테고리": "구매 전환율",
            "현황": f'평균 전환율(주문/조회) {sales["평균전환율"]}%로 개선 필요',
            "개선안": "상품 상세페이지 개선, 리뷰 관리 강화, 가격 경쟁력 점검 필요",
            "우선순위": "높음",
        })
    else:
        improvements.append({
            "카테고리": "구매 전환율",
            "현황": f'평균 전환율(주문/조회) {sales["평균전환율"]}%',
            "개선안": "전환율 유지하면서 트래픽 확대에 집중",
            "우선순위": "중간",
        })

    # 3. 제품 포트폴리오 분석
    top_products = [p for p in products["상품별요약"] if p["매출"] > 0]
    zero_products = [p for p in products["상품별요약"] if p["매출"] <= 0 and p["방문자"] >= 10]
    if zero_products:
        names = ", ".join([p["상품명"] for p in zero_products[:3]])
        improvements.append({
            "카테고리": "제품 관리",
            "현황": f"방문자 10명 이상인데 매출 0원인 제품 {len(zero_products)}개 존재 ({names})",
            "개선안": "해당 제품의 가격/상세페이지/재고 점검. 개선 불가 시 광고 중단 검토",
            "우선순위": "높음",
        })

    # 4. 취소/반품 분석
    cancel_data = products.get("취소현황", [])
    if cancel_data:
        total_cancel = sum(abs(c["총 취소 금액(원)"]) for c in cancel_data)
        improvements.append({
            "카테고리": "취소/반품",
            "현황": f"총 취소 금액 {total_cancel:,}원 발생",
            "개선안": "취소 사유 분석 후 상품 설명 보완, 품질 개선, 배송 프로세스 점검 필요",
            "우선순위": "높음",
        })

    # 5. 요일별 효율 차이 (광고 데이터 있을 때만)
    if ad.get("사용") and ad["요일별"]:
        weekday_ad = ad["요일별"]
        best_day = max(weekday_ad, key=lambda x: x["ROAS"])
        worst_day = min(weekday_ad, key=lambda x: x["ROAS"])
        day_kr = {
            "Monday": "월", "Tuesday": "화", "Wednesday": "수",
            "Thursday": "목", "Friday": "금", "Saturday": "토", "Sunday": "일"
        }
        if best_day["ROAS"] - worst_day["ROAS"] > 100:
            improvements.append({
                "카테고리": "광고 스케줄링",
                "현황": f'요일별 광고 전환 ROAS(광고로 생긴 매출 14일 ÷ 광고비) 편차 큼 (최고: {day_kr.get(best_day["요일"], best_day["요일"])}요일 {best_day["ROAS"]}%, 최저: {day_kr.get(worst_day["요일"], worst_day["요일"])}요일 {worst_day["ROAS"]}%)',
                "개선안": f'{day_kr.get(best_day["요일"], best_day["요일"])}요일 광고비 증액, {day_kr.get(worst_day["요일"], worst_day["요일"])}요일 광고비 감액하여 요일별 차등 운영',
                "우선순위": "중간",
            })

    # 6. 상관관계 기반 (광고 데이터 있을 때만)
    if ad.get("사용") and cross["광고비_매출_상관"] < 0.3:
        improvements.append({
            "카테고리": "광고-매출 연관성",
            "현황": f'광고비와 매출 간 상관계수 {cross["광고비_매출_상관"]}로 낮음',
            "개선안": "광고 타겟팅 재점검 필요. 현재 광고가 실제 구매로 연결되지 않는 구조일 수 있음",
            "우선순위": "높음",
        })

    return improvements


def generate_operation_plan(data: dict) -> list:
    """데이터 기반 다음달 운영 플랜 자동 생성"""
    plans = []
    ad = data["광고"]
    sales = data["판매"]
    products = data["제품"]
    next_month = data["다음월"]

    # 1. 광고 예산 플랜 (광고 데이터 있을 때만)
    if ad.get("사용"):
        # 판정은 핵심 인사이트 · 개선사항과 같은 기준(CLAUDE.md 두 줄)으로 한다
        if ad["ROAS"] >= SETTINGS()["ROAS_양호_기준_pct"]:
            budget_direction = "유지 또는 10~20% 증액"
            budget_detail = f"지금 ROAS(전체 매출 기준) {ad['ROAS']}%가 양호 기준 {SETTINGS()['ROAS_양호_기준_pct']}% 이상이므로 예산을 점진적으로 확대하여 매출 성장 추진"
        elif ad["ROAS"] >= SETTINGS()["ROAS_위험_기준_pct"]:
            budget_direction = "유지하며 고효율 캠페인 위주로 조정"
            budget_detail = f"지금 ROAS(전체 매출 기준) {ad['ROAS']}%는 보통 수준이므로 전체 예산은 유지하고, 고효율 캠페인에 먼저 늘리고 저효율 캠페인은 줄임"
        else:
            budget_direction = "효율화 후 재배분"
            budget_detail = f"지금 ROAS(전체 매출 기준) {ad['ROAS']}%가 위험 기준 {SETTINGS()['ROAS_위험_기준_pct']}% 미만이므로 ROAS 개선 후 예산 증액 검토. 비효율 캠페인 중단 및 고효율 캠페인에 예산 집중"

        # 목표 ROAS는 광고운영 섹션의 target["목표ROAS"]와 동일 값을 사용해 일치 보장
        target_roas = data.get("광고운영", {}).get("목표", {}).get("목표ROAS", max(int(ad['ROAS'] + 30), 200))
        plans.append({
            "영역": "광고 예산",
            "목표": f"{next_month} 광고 예산 {budget_direction}",
            "세부계획": budget_detail,
            "KPI": f"ROAS(전체 매출 기준) {target_roas}% 이상 달성",
        })

        # 2. 키워드/타겟팅 플랜
        plans.append({
            "영역": "광고 키워드",
            "목표": "고전환 키워드 발굴 및 최적화",
            "세부계획": "이번 기간 성과 데이터 기반 상위 전환 키워드 분석, 신규 롱테일 키워드 테스트, 경쟁사 키워드 모니터링",
            "KPI": f"구매전환율(주문/조회) {round(sales['평균전환율'] + 0.5, 2)}% 이상 달성",
        })

    # 3. 주력 제품 플랜
    top_product = products["상품별요약"][0] if products["상품별요약"] else None
    if top_product and top_product["매출"] > 0:
        plans.append({
            "영역": "주력 제품 육성",
            "목표": f'"{top_product["상품명"]}" 매출 확대',
            "세부계획": "리뷰 관리 강화, 상세페이지 최적화, 프로모션/쿠폰 활용, 아이템위너 유지",
            "KPI": f"주력 제품 매출 이번 기간 대비 20% 성장",
        })

    # 4. 제품 포트폴리오 관리
    active_products = [p for p in products["상품별요약"] if p["방문자"] > 0]
    selling_products = [p for p in products["상품별요약"] if p["매출"] > 0]
    plans.append({
        "영역": "제품 포트폴리오",
        "목표": f"활성 제품 {len(active_products)}개 중 매출 발생 제품 비율 확대",
        "세부계획": f"현재 매출 발생 제품 {len(selling_products)}개 → 비매출 제품 원인 분석 후 개선 또는 정리",
        "KPI": f"매출 발생 제품 {len(selling_products) + 2}개 이상",
    })

    # 5. 전환율 개선 플랜
    plans.append({
        "영역": "전환율 개선",
        "목표": f"구매전환율 {sales['평균전환율']}% → {sales['평균전환율'] + 0.5}% 이상",
        "세부계획": "상품 상세페이지 개선(이미지/영상 추가), 고객 리뷰 관리, 적정 가격 유지, 프로모션 활용",
        "KPI": f"전환율 {sales['평균전환율'] + 0.5}% 이상",
    })

    # 6. 취소율 관리
    cancel_data = products.get("취소현황", [])
    if cancel_data:
        plans.append({
            "영역": "취소/반품 관리",
            "목표": "취소율 감소",
            "세부계획": "취소 사유별 대응 방안 수립, 상품 설명 정확성 강화, 배송 품질 개선",
            "KPI": "취소율 이번 기간 대비 50% 감소",
        })

    return plans
