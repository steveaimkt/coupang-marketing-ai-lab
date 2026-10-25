"""
쿠팡 종합 리포트 - HTML 리포트 생성 모듈 (Light Theme)
Plotly 차트 + 모던 카드 기반 밝은 테마 HTML 리포트를 생성합니다.
"""

from datetime import datetime

import plotly.graph_objects as go
from plotly.subplots import make_subplots


WEEKDAY_KR = {
    "Monday": "월", "Tuesday": "화", "Wednesday": "수",
    "Thursday": "목", "Friday": "금", "Saturday": "토", "Sunday": "일",
}

# 컬러 팔레트
C_PRIMARY = "#6C5CE7"      # 보라 (메인 브랜드)
C_PRIMARY_LIGHT = "#A29BFE" # 연보라
C_SECONDARY = "#00B894"    # 민트
C_ACCENT = "#F97316"       # 오렌지
C_DANGER = "#E17055"       # 레드 오렌지
C_WARNING = "#FDCB6E"      # 옐로우
C_INFO = "#74B9FF"         # 하늘색
C_SUCCESS = "#00B894"      # 그린 민트
C_TEXT = "#2D3436"         # 다크 텍스트
C_TEXT_SECONDARY = "#636E72" # 서브 텍스트
C_BG = "#F8F9FA"           # 배경
C_CARD = "#FFFFFF"         # 카드 배경
C_BORDER = "#E9ECEF"       # 테두리


def fmt_money(value: int) -> str:
    """금액 포맷팅 (만원 단위)"""
    if abs(value) >= 100000000:
        return f"{value / 100000000:,.1f}억원"
    if abs(value) >= 10000:
        man = value / 10000
        if man == int(man):
            return f"{int(man):,}만원"
        return f"{man:,.1f}만원"
    return f"{value:,}원"


def fmt_number(value) -> str:
    """숫자 포맷팅"""
    if isinstance(value, float):
        return f"{value:,.1f}"
    return f"{int(value):,}"


# ============================================================
#  차트 생성 함수들 (Light Theme)
# ============================================================

def _base_layout(**overrides):
    """차트 기본 레이아웃 생성 (오버라이드 가능)"""
    base = dict(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Noto Sans KR, -apple-system, sans-serif", color=C_TEXT, size=12),
        margin=dict(l=50, r=30, t=45, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
                    font=dict(size=11)),
        autosize=True,
    )
    base.update(overrides)
    return base


def create_ad_trend_chart(ad_data: dict) -> str:
    """일별 광고비 vs 매출 추이 차트"""
    daily = ad_data["일별"]
    dates = [d["날짜str"] for d in daily]
    ad_cost = [d["광고비"] for d in daily]
    ad_revenue = [d["광고매출"] for d in daily]
    roas = [d["ROAS"] for d in daily]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(name="광고비", x=dates, y=ad_cost,
               marker_color=C_DANGER, opacity=0.75),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(name="광고매출", x=dates, y=ad_revenue,
               marker_color=C_PRIMARY, opacity=0.75),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(name="ROAS(%)", x=dates, y=roas,
                   mode="lines+markers", line=dict(color=C_ACCENT, width=2.5),
                   marker=dict(size=5)),
        secondary_y=True,
    )

    fig.update_layout(**_base_layout(
        title=dict(text="일별 광고비 vs 광고매출 추이", font=dict(size=14, color=C_TEXT)),
        barmode="group",
        height=380,
    ))
    fig.update_yaxes(title_text="금액 (원)", secondary_y=False, gridcolor="#f0f0f0")
    fig.update_yaxes(title_text="ROAS (%)", secondary_y=True)
    fig.update_xaxes(gridcolor="#f0f0f0")

    return fig.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})


def create_sales_trend_chart(sales_data: dict) -> str:
    """일별 방문자/주문/전환율 추이 차트"""
    daily = sales_data["일별"]
    dates = [d["날짜str"] for d in daily]
    visitors = [d["방문자"] for d in daily]
    orders = [d["주문"] for d in daily]
    cvr = [d["구매전환율"] for d in daily]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(name="방문자", x=dates, y=visitors,
                   mode="lines", fill="tozeroy",
                   line=dict(color=C_INFO, width=1.5),
                   fillcolor="rgba(116,185,255,0.15)"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(name="주문", x=dates, y=orders,
               marker_color=C_PRIMARY, opacity=0.7),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(name="전환율(%)", x=dates, y=cvr,
                   mode="lines+markers", line=dict(color=C_ACCENT, width=2.5),
                   marker=dict(size=5)),
        secondary_y=True,
    )

    fig.update_layout(**_base_layout(
        title=dict(text="일별 방문자 / 주문 / 전환율 추이", font=dict(size=14, color=C_TEXT)),
        height=380,
    ))
    fig.update_yaxes(title_text="수 (명/건)", secondary_y=False, gridcolor="#f0f0f0")
    fig.update_yaxes(title_text="전환율 (%)", secondary_y=True)
    fig.update_xaxes(gridcolor="#f0f0f0")

    return fig.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})


def create_revenue_trend_chart(sales_data: dict) -> str:
    """일별 매출 추이 차트"""
    daily = sales_data["일별"]
    dates = [d["날짜str"] for d in daily]
    revenue = [d["매출"] for d in daily]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(name="매출", x=dates, y=revenue,
                   mode="lines+markers", fill="tozeroy",
                   line=dict(color=C_SUCCESS, width=2.5),
                   fillcolor="rgba(0,184,148,0.1)",
                   marker=dict(size=5)),
    )

    fig.update_layout(**_base_layout(
        title=dict(text="일별 매출 추이", font=dict(size=14, color=C_TEXT)),
        height=320,
        yaxis_title="매출 (원)",
    ))
    fig.update_yaxes(gridcolor="#f0f0f0")
    fig.update_xaxes(gridcolor="#f0f0f0")

    return fig.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})


def create_product_chart(product_data: dict) -> str:
    """제품별 매출 Top 차트"""
    products = [p for p in product_data["상품별요약"] if p["매출"] > 0]
    if not products:
        products = product_data["상품별요약"][:10]

    names = [p["상품명"] for p in products]
    revenues = [p["매출"] for p in products]
    orders = [p["주문"] for p in products]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(name="매출(원)", x=names, y=revenues,
               marker_color=C_PRIMARY, opacity=0.8),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(name="주문수", x=names, y=orders,
                   mode="lines+markers", line=dict(color=C_ACCENT, width=2.5),
                   marker=dict(size=8)),
        secondary_y=True,
    )

    fig.update_layout(**_base_layout(
        title=dict(text="제품별 매출 & 주문수", font=dict(size=14, color=C_TEXT)),
        height=380,
    ))
    fig.update_yaxes(gridcolor="#f0f0f0", secondary_y=False)
    fig.update_xaxes(gridcolor="#f0f0f0")

    return fig.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})


def create_funnel_chart(sales_data: dict) -> str:
    """판매 퍼널 차트"""
    stages = ["방문자", "조회", "장바구니", "주문"]
    values = [
        sales_data["총방문자"],
        sales_data["총조회"],
        sales_data["총장바구니"],
        sales_data["총주문"],
    ]

    fig = go.Figure(go.Funnel(
        y=stages,
        x=values,
        textposition="inside",
        textinfo="value+percent initial",
        marker=dict(color=[C_PRIMARY, C_INFO, C_ACCENT, C_SUCCESS]),
    ))

    fig.update_layout(**_base_layout(
        title=dict(text="판매 퍼널 분석", font=dict(size=14, color=C_TEXT)),
        height=320,
        margin=dict(l=100, r=30, t=45, b=30),
    ))

    return fig.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})


def create_weekday_chart(ad_data: dict, sales_data: dict) -> str:
    """요일별 광고 ROAS & 전환율 차트"""
    ad_weekday = ad_data["요일별"]
    sales_weekday = sales_data["요일별"]

    days = [WEEKDAY_KR.get(d["요일"], d["요일"]) for d in ad_weekday]
    roas = [d["ROAS"] for d in ad_weekday]
    cvr = [d["전환율"] for d in sales_weekday]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(name="ROAS(%)", x=days, y=roas,
               marker_color=C_PRIMARY, opacity=0.8),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(name="전환율(%)", x=days, y=cvr,
                   mode="lines+markers", line=dict(color=C_ACCENT, width=3),
                   marker=dict(size=8)),
        secondary_y=True,
    )

    fig.update_layout(**_base_layout(
        title=dict(text="요일별 광고 ROAS & 전환율", font=dict(size=14, color=C_TEXT)),
        height=320,
    ))
    fig.update_yaxes(gridcolor="#f0f0f0", secondary_y=False)
    fig.update_xaxes(gridcolor="#f0f0f0")

    return fig.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})


def create_ad_vs_sales_chart(cross_data: dict) -> str:
    """광고비 vs 매출 일별 추이 비교 차트"""
    daily = cross_data.get("일별통합", [])
    if not daily:
        return ""

    dates = [d["날짜str"] for d in daily]
    ad_cost = [d["광고비"] for d in daily]
    revenue = [d["매출"] for d in daily]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(name="광고비", x=dates, y=ad_cost,
                   mode="lines+markers",
                   line=dict(color=C_DANGER, width=2),
                   marker=dict(size=4)),
    )
    fig.add_trace(
        go.Scatter(name="매출", x=dates, y=revenue,
                   mode="lines+markers",
                   line=dict(color=C_PRIMARY, width=2),
                   marker=dict(size=4)),
    )

    fig.update_layout(**_base_layout(
        title=dict(text="광고비 vs 매출 일별 추이", font=dict(size=14, color=C_TEXT)),
        height=340,
    ))
    fig.update_yaxes(gridcolor="#f0f0f0")
    fig.update_xaxes(gridcolor="#f0f0f0")

    return fig.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})


def create_item_winner_chart(product_data: dict) -> str:
    """아이템위너 비율 차트"""
    iw_data = product_data.get("아이템위너", [])
    if not iw_data:
        return ""

    items = iw_data[:10]
    names = [d["상품명"] for d in items]
    rates = [d["아이템위너비율"] for d in items]

    colors = [C_SUCCESS if r >= 70 else C_ACCENT if r >= 40 else C_DANGER for r in rates]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(x=names, y=rates, marker_color=colors, opacity=0.85,
               text=[f"{r:.0f}%" for r in rates], textposition="outside"),
    )

    fig.update_layout(**_base_layout(
        title=dict(text="상품별 아이템위너 비율", font=dict(size=14, color=C_TEXT)),
        height=340,
        yaxis=dict(range=[0, 105], title="아이템위너 비율 (%)"),
    ))
    fig.update_yaxes(gridcolor="#f0f0f0")
    fig.update_xaxes(gridcolor="#f0f0f0")

    # 기준선 70%
    fig.add_hline(y=70, line_dash="dash", line_color=C_SUCCESS, opacity=0.5,
                  annotation_text="목표 70%", annotation_position="top right")

    return fig.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})


def create_placement_chart(kw_data: dict) -> str:
    """광고 노출 지면별 비교 차트"""
    placements = kw_data.get("지면별", [])
    if not placements:
        return ""

    names = [p["광고 노출 지면"] for p in placements]
    spend = [p["광고비"] for p in placements]
    revenue = [p["매출"] for p in placements]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="광고비", x=names, y=spend, marker_color=C_DANGER, opacity=0.75))
    fig.add_trace(go.Bar(name="전환매출", x=names, y=revenue, marker_color=C_PRIMARY, opacity=0.75))

    fig.update_layout(**_base_layout(
        title=dict(text="광고 노출 지면별 광고비 vs 매출", font=dict(size=14, color=C_TEXT)),
        barmode="group",
        height=340,
    ))
    fig.update_yaxes(gridcolor="#f0f0f0")

    return fig.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})


def create_keyword_chart(kw_data: dict) -> str:
    """Top 키워드 매출 차트"""
    keywords = kw_data.get("키워드_매출순", [])
    if not keywords:
        return ""

    top = keywords[:10]
    names = [k["키워드"][:15] + "..." if len(k["키워드"]) > 15 else k["키워드"] for k in top]
    revenue = [k["매출"] for k in top]
    spend = [k["광고비"] for k in top]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="전환매출", x=names, y=revenue, marker_color=C_PRIMARY, opacity=0.8))
    fig.add_trace(go.Bar(name="광고비", x=names, y=spend, marker_color=C_DANGER, opacity=0.6))

    fig.update_layout(**_base_layout(
        title=dict(text="Top 10 키워드 매출 vs 광고비", font=dict(size=14, color=C_TEXT)),
        barmode="group",
        height=380,
    ))
    fig.update_yaxes(gridcolor="#f0f0f0")

    return fig.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})


def create_campaign_chart(kw_data: dict) -> str:
    """캠페인별 성과 차트"""
    campaigns = kw_data.get("캠페인별", [])
    if not campaigns:
        return ""

    top = campaigns[:8]
    names = [c["캠페인명"][:20] + "..." if len(c["캠페인명"]) > 20 else c["캠페인명"] for c in top]
    spend = [c["광고비"] for c in top]
    revenue = [c["매출"] for c in top]
    roas = [c["ROAS"] for c in top]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(name="광고비", x=names, y=spend, marker_color=C_DANGER, opacity=0.7), secondary_y=False)
    fig.add_trace(go.Bar(name="전환매출", x=names, y=revenue, marker_color=C_PRIMARY, opacity=0.7), secondary_y=False)
    fig.add_trace(go.Scatter(name="ROAS(%)", x=names, y=roas, mode="lines+markers",
                             line=dict(color=C_ACCENT, width=2.5), marker=dict(size=7)),
                  secondary_y=True)

    fig.update_layout(**_base_layout(
        title=dict(text="캠페인별 광고비 / 매출 / ROAS", font=dict(size=14, color=C_TEXT)),
        barmode="group",
        height=380,
    ))
    fig.update_yaxes(gridcolor="#f0f0f0", secondary_y=False)
    fig.update_yaxes(title_text="ROAS (%)", secondary_y=True)

    return fig.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})


# ============================================================
#  HTML 리포트 생성
# ============================================================

def generate_html_report(data: dict) -> str:
    """분석 데이터를 기반으로 밝은 테마 HTML 리포트 생성"""

    # 광고 데이터 사용 여부
    ad_used = data["광고"].get("사용", False)

    # 차트 생성
    ad_trend_chart = create_ad_trend_chart(data["광고"]) if ad_used and data["광고"].get("일별") else ""
    sales_trend_chart = create_sales_trend_chart(data["판매"])
    revenue_trend_chart = create_revenue_trend_chart(data["판매"])
    product_chart = create_product_chart(data["제품"])
    funnel_chart = create_funnel_chart(data["판매"])
    weekday_chart = create_weekday_chart(data["광고"], data["판매"]) if ad_used and data["광고"].get("요일별") else ""
    ad_vs_sales_chart = create_ad_vs_sales_chart(data["교차분석"])
    item_winner_chart = create_item_winner_chart(data["제품"])

    # 키워드 차트 (데이터 있을 때만)
    kw_data = data.get("키워드")
    placement_chart = create_placement_chart(kw_data) if kw_data else ""
    keyword_chart = create_keyword_chart(kw_data) if kw_data else ""
    campaign_chart = create_campaign_chart(kw_data) if kw_data else ""

    ad = data["광고"]
    sales = data["판매"]
    products = data["제품"]
    cross = data["교차분석"]
    improvements = data["개선사항"]
    plans = data["운영플랜"]
    insights = data.get("인사이트", [])
    must_checks = data.get("필수확인", [])

    # ---- 인사이트 카드 ----
    insight_type_styles = {
        "positive": {"bg": "#E8F8F5", "border": C_SUCCESS, "icon": "check_circle", "color": "#00B894"},
        "warning": {"bg": "#FEF9E7", "border": "#F39C12", "icon": "warning", "color": "#F39C12"},
        "danger": {"bg": "#FDEDEC", "border": C_DANGER, "icon": "error", "color": C_DANGER},
        "info": {"bg": "#EBF5FB", "border": C_INFO, "icon": "info", "color": "#2980B9"},
    }

    insight_cards_html = ""
    for ins in insights:
        style = insight_type_styles.get(ins["유형"], insight_type_styles["info"])
        insight_cards_html += f"""
        <div class="insight-card" style="background:{style["bg"]}; border-left:4px solid {style["border"]};">
            <div class="insight-badge" style="color:{style["color"]}">
                <span class="material-icon">{style["icon"]}</span>
                {ins["유형"].upper()}
            </div>
            <div class="insight-title">{ins["제목"]}</div>
            <div class="insight-desc">{ins["내용"]}</div>
        </div>"""

    # ---- 필수 확인사항 ----
    check_rows_html = ""
    priority_colors = {"긴급": C_DANGER, "필수": C_PRIMARY, "높음": C_ACCENT, "중간": C_INFO}
    for chk in must_checks:
        color = priority_colors.get(chk["중요도"], C_TEXT_SECONDARY)
        check_rows_html += f"""
        <div class="check-item">
            <span class="check-badge" style="background:{color}">{chk["중요도"]}</span>
            <div class="check-content">
                <div class="check-title">{chk["항목"]}</div>
                <div class="check-desc">{chk["설명"]}</div>
            </div>
        </div>"""

    # ---- 제품 테이블 ----
    product_rows = ""
    for i, p in enumerate(products["상품별요약"]):
        revenue_class = "text-success" if p["매출"] > 0 else ("text-danger" if p["매출"] < 0 else "text-muted")
        product_rows += f"""
        <tr>
            <td class="text-center">{i + 1}</td>
            <td class="product-name">{p["상품명"]}</td>
            <td class="text-right">{fmt_number(p["방문자"])}</td>
            <td class="text-right">{fmt_number(p["조회"])}</td>
            <td class="text-right">{fmt_number(p["장바구니"])}</td>
            <td class="text-right">{fmt_number(p["주문"])}</td>
            <td class="text-right">{fmt_number(p["판매량"])}</td>
            <td class="text-right {revenue_class}"><strong>{fmt_money(int(p["매출"]))}</strong></td>
            <td class="text-right">{p["전환율"]}%</td>
        </tr>"""

    # ---- 아이템위너 테이블 ----
    iw_rows = ""
    for iw in products.get("아이템위너", []):
        rate = iw["아이템위너비율"]
        rate_class = "text-success" if rate >= 70 else ("text-warning" if rate >= 40 else "text-danger")
        iw_rows += f"""
        <tr>
            <td class="product-name">{iw["상품명"]}</td>
            <td class="text-right {rate_class}"><strong>{rate:.1f}%</strong></td>
            <td class="text-right">{fmt_money(int(iw["매출"]))}</td>
        </tr>"""

    # ---- 카테고리별 테이블 ----
    category_rows = ""
    for cat in products.get("카테고리별", []):
        category_rows += f"""
        <tr>
            <td>{cat["카테고리"]}</td>
            <td class="text-right">{fmt_money(int(cat["매출"]))}</td>
            <td class="text-right">{fmt_number(cat["주문"])}</td>
            <td class="text-right">{fmt_number(cat["방문자"])}</td>
        </tr>"""

    # ---- 일자별 상세 테이블 ----
    daily_merged = data["교차분석"].get("일별통합", [])
    daily_detail_rows = ""
    if ad_used and daily_merged:
        for d in daily_merged:
            day_kr = WEEKDAY_KR.get(d.get("요일", ""), "")
            daily_detail_rows += f"""
        <tr>
            <td class="text-center">{d["날짜str"]} ({day_kr})</td>
            <td class="text-right">{fmt_money(int(d["광고비"]))}</td>
            <td class="text-right">{fmt_money(int(d["광고매출"]))}</td>
            <td class="text-right">{d["ROAS"]:.1f}%</td>
            <td class="text-right">{fmt_number(int(d["방문자"]))}</td>
            <td class="text-right">{fmt_number(int(d["조회"]))}</td>
            <td class="text-right">{fmt_number(int(d["장바구니"]))}</td>
            <td class="text-right">{fmt_number(int(d["주문"]))}</td>
            <td class="text-right">{d["구매전환율"]:.2f}%</td>
            <td class="text-right">{fmt_money(int(d["매출"]))}</td>
        </tr>"""
        # 합계/평균 행
        dt_cost = sum(d["광고비"] for d in daily_merged)
        dt_adrev = sum(d["광고매출"] for d in daily_merged)
        dt_roas = (dt_adrev / dt_cost * 100) if dt_cost else 0
        dt_visit = sum(d["방문자"] for d in daily_merged)
        dt_view = sum(d["조회"] for d in daily_merged)
        dt_cart = sum(d["장바구니"] for d in daily_merged)
        dt_order = sum(d["주문"] for d in daily_merged)
        dt_cvr = sum(d["구매전환율"] for d in daily_merged) / len(daily_merged)
        dt_rev = sum(d["매출"] for d in daily_merged)
        daily_detail_rows += f"""
        <tr class="total-row">
            <td class="text-center">합계 ({len(daily_merged)}일)</td>
            <td class="text-right">{fmt_money(int(dt_cost))}</td>
            <td class="text-right">{fmt_money(int(dt_adrev))}</td>
            <td class="text-right">{dt_roas:.0f}%</td>
            <td class="text-right">{fmt_number(int(dt_visit))}</td>
            <td class="text-right">{fmt_number(int(dt_view))}</td>
            <td class="text-right">{fmt_number(int(dt_cart))}</td>
            <td class="text-right">{fmt_number(int(dt_order))}</td>
            <td class="text-right">{(sales["총주문"] / sales["총조회"] * 100 if sales.get("총조회") else dt_cvr):.2f}%</td>
            <td class="text-right">{fmt_money(int(dt_rev))}</td>
        </tr>"""
    else:
        # 광고 없이 판매 일별 데이터만 사용
        for d in sales["일별"]:
            day_kr = WEEKDAY_KR.get(d.get("요일", ""), "")
            daily_detail_rows += f"""
        <tr>
            <td class="text-center">{d["날짜str"]} ({day_kr})</td>
            <td class="text-right">{fmt_number(int(d["방문자"]))}</td>
            <td class="text-right">{fmt_number(int(d["조회"]))}</td>
            <td class="text-right">{fmt_number(int(d["장바구니"]))}</td>
            <td class="text-right">{fmt_number(int(d["주문"]))}</td>
            <td class="text-right">{d["구매전환율"]:.2f}%</td>
            <td class="text-right">{fmt_money(int(d["매출"]))}</td>
        </tr>"""
        if sales["일별"]:
            # 합계/평균 행
            st_visit = sum(d["방문자"] for d in sales["일별"])
            st_view = sum(d["조회"] for d in sales["일별"])
            st_cart = sum(d["장바구니"] for d in sales["일별"])
            st_order = sum(d["주문"] for d in sales["일별"])
            st_cvr = sum(d["구매전환율"] for d in sales["일별"]) / len(sales["일별"])
            st_rev = sum(d["매출"] for d in sales["일별"])
            daily_detail_rows += f"""
        <tr class="total-row">
            <td class="text-center">합계 ({len(sales["일별"])}일)</td>
            <td class="text-right">{fmt_number(int(st_visit))}</td>
            <td class="text-right">{fmt_number(int(st_view))}</td>
            <td class="text-right">{fmt_number(int(st_cart))}</td>
            <td class="text-right">{fmt_number(int(st_order))}</td>
            <td class="text-right">{st_cvr:.2f}%</td>
            <td class="text-right">{fmt_money(int(st_rev))}</td>
        </tr>"""

    # ---- 개선사항 카드 ----
    improvement_cards = ""
    priority_badge = {"높음": ("bg-danger", "#E17055"), "중간": ("bg-warning", "#F39C12"), "낮음": ("bg-info", "#74B9FF")}
    for imp in improvements:
        cls, color = priority_badge.get(imp["우선순위"], ("bg-info", C_INFO))
        improvement_cards += f"""
        <div class="improvement-card">
            <div class="improvement-header">
                <span class="improvement-category">{imp["카테고리"]}</span>
                <span class="badge" style="background:{color}">{imp["우선순위"]}</span>
            </div>
            <div class="improvement-status">{imp["현황"]}</div>
            <div class="improvement-action">{imp["개선안"]}</div>
        </div>"""

    # ---- 운영플랜 테이블 ----
    plan_rows = ""
    for plan in plans:
        plan_rows += f"""
        <tr>
            <td><span class="plan-badge">{plan["영역"]}</span></td>
            <td>{plan["목표"]}</td>
            <td>{plan["세부계획"]}</td>
            <td class="text-primary"><strong>{plan["KPI"]}</strong></td>
        </tr>"""

    # ---- 주간별 성과 테이블 ----
    weekly_rows = ""
    if ad_used and ad["주간별"]:
        for w_ad, w_sales in zip(ad["주간별"], sales["주간별"]):
            weekly_rows += f"""
        <tr>
            <td class="text-center"><strong>{w_ad["주차"]}주차</strong>{f' <span style="font-weight:400; font-size:11px; color:#636E72;">({int(w_sales["일수"])}일)</span>' if w_sales.get("일수") else ""}</td>
            <td class="text-right">{fmt_money(int(w_ad["광고비"]))}</td>
            <td class="text-right">{fmt_money(int(w_ad["광고매출"]))}</td>
            <td class="text-right">{w_ad["ROAS"]}%</td>
            <td class="text-right"><strong>{fmt_money(int(w_sales["매출"]))}</strong></td>
            <td class="text-right">{fmt_number(w_sales["주문"])}</td>
            <td class="text-right">{w_sales["전환율"]}%</td>
        </tr>"""
        # 합계/평균 행
        wt_cost = sum(w["광고비"] for w in ad["주간별"])
        wt_adrev = sum(w["광고매출"] for w in ad["주간별"])
        wt_roas = (wt_adrev / wt_cost * 100) if wt_cost else 0
        wt_pairs = list(zip(ad["주간별"], sales["주간별"]))
        wt_rev = sum(w["매출"] for _, w in wt_pairs)
        wt_order = sum(w["주문"] for _, w in wt_pairs)
        wt_cvr = sum(w["전환율"] for _, w in wt_pairs) / len(wt_pairs) if wt_pairs else 0
        weekly_rows += f"""
        <tr class="total-row">
            <td class="text-center">합계</td>
            <td class="text-right">{fmt_money(int(wt_cost))}</td>
            <td class="text-right">{fmt_money(int(wt_adrev))}</td>
            <td class="text-right">{wt_roas:.1f}%</td>
            <td class="text-right">{fmt_money(int(wt_rev))}</td>
            <td class="text-right">{fmt_number(wt_order)}</td>
            <td class="text-right">{(sales["총주문"] / sales["총조회"] * 100 if sales.get("총조회") else 0):.2f}%</td>
        </tr>"""
    else:
        for w_sales in sales["주간별"]:
            weekly_rows += f"""
        <tr>
            <td class="text-center"><strong>{w_sales["주차"]}주차</strong>{f' <span style="font-weight:400; font-size:11px; color:#636E72;">({int(w_sales["일수"])}일)</span>' if w_sales.get("일수") else ""}</td>
            <td class="text-right"><strong>{fmt_money(int(w_sales["매출"]))}</strong></td>
            <td class="text-right">{fmt_number(w_sales["주문"])}</td>
            <td class="text-right">{w_sales["전환율"]}%</td>
        </tr>"""
        if sales["주간별"]:
            # 합계/평균 행
            ws_rev = sum(w["매출"] for w in sales["주간별"])
            ws_order = sum(w["주문"] for w in sales["주간별"])
            ws_cvr = (sales["총주문"] / sales["총조회"] * 100) if sales.get("총조회") else 0
            weekly_rows += f"""
        <tr class="total-row">
            <td class="text-center">합계</td>
            <td class="text-right">{fmt_money(int(ws_rev))}</td>
            <td class="text-right">{fmt_number(ws_order)}</td>
            <td class="text-right">{ws_cvr:.2f}%</td>
        </tr>"""

    # ---- 상관관계 해석 ----
    def interpret_corr(val):
        abs_val = abs(val)
        if abs_val >= 0.7:
            return "강한 양의 상관" if val > 0 else "강한 음의 상관"
        elif abs_val >= 0.4:
            return "보통 양의 상관" if val > 0 else "보통 음의 상관"
        elif abs_val >= 0.2:
            return "약한 양의 상관" if val > 0 else "약한 음의 상관"
        else:
            return "상관관계 없음"

    def corr_color(val):
        if val >= 0.4:
            return C_SUCCESS
        elif val >= 0.2:
            return C_ACCENT
        return C_DANGER

    # ---- 교차 분석 섹션 (광고 데이터 있을 때만) ----
    cross_section_html = ""
    if ad_used:
        ad_vs_chart_div = f'<div class="chart-container">{ad_vs_sales_chart}</div>' if ad_vs_sales_chart else ""
        cross_section_html = f"""
        <!-- ===== 9. 광고-판매 교차 분석 ===== -->
        <div class="section" id="cross">
            <div class="section-title">
                <span class="icon icon-orange">&#x1f50d;</span>
                광고-판매 교차 분석
            </div>

            <div class="kpi-grid kpi-grid-3">
                <div class="kpi-card">
                    <div class="label">광고 매출</div>
                    <div class="value">{fmt_money(cross["광고매출합계"])}</div>
                    <div class="sub">광고를 통한 매출</div>
                </div>
                <div class="kpi-card">
                    <div class="label">셀러인사이트 매출</div>
                    <div class="value">{fmt_money(cross["인사이트매출합계"])}</div>
                    <div class="sub">전체 채널 매출</div>
                </div>
                <div class="kpi-card highlight">
                    <div class="label">순이익 추정 (매출-광고비)</div>
                    <div class="value">{fmt_money(cross["순이익추정"])}</div>
                    <div class="sub">광고비 대비 매출 비율 {cross["광고비대비매출비율"]}%</div>
                </div>
            </div>

            {ad_vs_chart_div}

            <div class="sub-heading">광고비와 성과 지표 간 상관관계</div>
            <div class="corr-grid">
                <div class="corr-card">
                    <div class="corr-label">광고비 &harr; 방문자</div>
                    <div class="corr-value" style="color:{corr_color(cross["광고비_방문자_상관"])}">{cross["광고비_방문자_상관"]}</div>
                    <div class="corr-desc">{interpret_corr(cross["광고비_방문자_상관"])}</div>
                </div>
                <div class="corr-card">
                    <div class="corr-label">광고비 &harr; 주문</div>
                    <div class="corr-value" style="color:{corr_color(cross["광고비_주문_상관"])}">{cross["광고비_주문_상관"]}</div>
                    <div class="corr-desc">{interpret_corr(cross["광고비_주문_상관"])}</div>
                </div>
                <div class="corr-card">
                    <div class="corr-label">광고비 &harr; 매출</div>
                    <div class="corr-value" style="color:{corr_color(cross["광고비_매출_상관"])}">{cross["광고비_매출_상관"]}</div>
                    <div class="corr-desc">{interpret_corr(cross["광고비_매출_상관"])}</div>
                </div>
            </div>
        </div>
        """

    # ---- 취소 현황 테이블 ----
    cancel_rows = ""
    for c in products.get("취소현황", []):
        cancel_rows += f"""
        <tr>
            <td class="product-name">{c["상품명"]}</td>
            <td>{c.get("옵션명", "-")}</td>
            <td class="text-right text-danger">{fmt_money(int(abs(c["총 취소 금액(원)"])))}</td>
            <td class="text-right text-danger">{int(abs(c["총 취소된 상품수"]))}개</td>
        </tr>"""

    # ---- 제품 트렌드 섹션 ----
    trend = data.get("제품트렌드", {})
    trend_section_html = ""
    if trend:
        # 판매량 상위 5
        top5_rows = ""
        for p in trend.get("판매량상위5", []):
            top5_rows += f'<tr><td class="product-name">{p["상품명"]}</td><td class="text-right">{fmt_number(p["판매량"])}</td><td class="text-right">{fmt_money(int(p["매출"]))}</td><td class="text-right">{p["전환율"]}%</td></tr>'

        # 판매량 하위 5
        bottom5_rows = ""
        for p in trend.get("판매량하위5", []):
            bottom5_rows += f'<tr><td class="product-name">{p["상품명"]}</td><td class="text-right">{fmt_number(p["판매량"])}</td><td class="text-right">{fmt_money(int(p["매출"]))}</td><td class="text-right">{p["전환율"]}%</td></tr>'

        # 매출 급등
        rising_rows = ""
        for p in trend.get("매출급등", []):
            rising_rows += (
                f'<tr><td class="product-name">{p["상품명"]}</td>'
                f'<td class="text-right">{fmt_money(p["최근7일매출"])}</td>'
                f'<td class="text-right">{fmt_money(p["이전7일매출"])}</td>'
                f'<td class="text-right text-success"><strong>+{p["변화율"]}%</strong></td></tr>'
            )

        # 매출 급락
        falling_rows = ""
        for p in trend.get("매출급락", []):
            falling_rows += (
                f'<tr><td class="product-name">{p["상품명"]}</td>'
                f'<td class="text-right">{fmt_money(p["최근7일매출"])}</td>'
                f'<td class="text-right">{fmt_money(p["이전7일매출"])}</td>'
                f'<td class="text-right text-danger"><strong>{p["변화율"]}%</strong></td></tr>'
            )

        # 판매 추세 증가
        inc_rows = ""
        for p in trend.get("판매증가추세", []):
            inc_rows += (
                f'<tr><td class="product-name">{p["상품명"]}</td>'
                f'<td class="text-right">{p["최근7일주문"]}건</td>'
                f'<td class="text-right">{p["이전7일주문"]}건</td>'
                f'<td class="text-right text-success"><strong>+{p["변화율"]}%</strong></td></tr>'
            )

        # 판매 추세 감소
        dec_rows = ""
        for p in trend.get("판매감소추세", []):
            dec_rows += (
                f'<tr><td class="product-name">{p["상품명"]}</td>'
                f'<td class="text-right">{p["최근7일주문"]}건</td>'
                f'<td class="text-right">{p["이전7일주문"]}건</td>'
                f'<td class="text-right text-danger"><strong>{p["변화율"]}%</strong></td></tr>'
            )

        # 트렌드 서브 섹션 HTML (Python 3.9 f-string 제약 회피)
        trend_rising_html = ""
        if rising_rows:
            trend_rising_html = (
                f'<p style="font-size:12px; color:{C_TEXT_SECONDARY}; margin:0 0 8px;">아래 급등/급락 표의 매출은 <strong>광고를 집행한 상품 기준 광고 전환매출(14일)</strong>입니다. 타 상품으로 발생한 전환분이 포함될 수 있어, 위 판매량 표(셀러인사이트 기준)와 수치가 다를 수 있습니다.</p>'
                f'<div class="sub-heading" style="color:{C_SUCCESS};">최근 7일 매출 급등 제품</div>'
                f'<div class="table-wrapper"><table>'
                f'<thead><tr><th>상품명</th><th class="text-right">최근 7일</th><th class="text-right">이전 7일(환산)</th><th class="text-right">변화율</th></tr></thead>'
                f'<tbody>{rising_rows}</tbody></table></div>'
            )
        trend_falling_html = ""
        if falling_rows:
            trend_falling_html = (
                f'<div class="sub-heading" style="color:{C_DANGER};">최근 7일 매출 급락 제품</div>'
                f'<div class="table-wrapper"><table>'
                f'<thead><tr><th>상품명</th><th class="text-right">최근 7일</th><th class="text-right">이전 7일(환산)</th><th class="text-right">변화율</th></tr></thead>'
                f'<tbody>{falling_rows}</tbody></table></div>'
            )
        _th = data.get("제품트렌드", {}).get("추세기준", 30)
        trend_inc_html = ""
        if inc_rows:
            trend_inc_html = (
                f'<div class="sub-heading" style="color:{C_SUCCESS};">판매 증가 추세 제품 (주문 +{_th}% 이상)</div>'
                f'<div class="table-wrapper"><table>'
                f'<thead><tr><th>상품명</th><th class="text-right">최근 7일</th><th class="text-right">이전 7일(환산)</th><th class="text-right">변화율</th></tr></thead>'
                f'<tbody>{inc_rows}</tbody></table></div>'
            )
        trend_dec_html = ""
        if dec_rows:
            trend_dec_html = (
                f'<div class="sub-heading" style="color:{C_DANGER};">판매 감소 추세 제품 (주문 -{_th}% 이상)</div>'
                f'<div class="table-wrapper"><table>'
                f'<thead><tr><th>상품명</th><th class="text-right">최근 7일</th><th class="text-right">이전 7일(환산)</th><th class="text-right">변화율</th></tr></thead>'
                f'<tbody>{dec_rows}</tbody></table></div>'
            )

    # ---- ROAS 상태 ----
    roas_status = ("good" if ad["ROAS"] >= 300 else ("warning" if ad["ROAS"] >= 200 else "danger")) if ad_used else ""
    cvr_status = "good" if sales["평균전환율"] >= 2 else ("warning" if sales["평균전환율"] >= 1 else "danger")

    # ---- 월간 예상치 ----
    fc = data.get("예상", {})
    forecast_roas_status = ""
    if fc.get("예상ROAS"):
        forecast_roas_status = "good" if fc["예상ROAS"] >= 300 else ("warning" if fc["예상ROAS"] >= 200 else "danger")

    # 광고 예상치 카드 HTML (Python 3.9 f-string 제약 회피)
    fc_ad_html = ""
    if ad_used:
        fc_ad_cost = fmt_money(fc.get("예상광고비", 0))
        fc_ad_avg = fmt_money(ad["일평균광고비"])
        fc_ad_roas = fc.get("예상ROAS", 0)
        fc_ad_rev = fmt_money(fc.get("예상광고매출", 0))
        fc_ad_html = (
            f'<div class="kpi-card" style="border-left:3px solid {C_ACCENT};">'
            f'<div class="label">예상 광고비</div>'
            f'<div class="value">{fc_ad_cost}</div>'
            f'<div class="sub">일평균 {fc_ad_avg} 유지 시</div>'
            f'</div>'
            f'<div class="kpi-card {forecast_roas_status}" style="border-left:3px solid {C_SUCCESS};">'
            f'<div class="label">예상 ROAS</div>'
            f'<div class="value">{fc_ad_roas}%</div>'
            f'<div class="sub">예상 광고매출 {fc_ad_rev}</div>'
            f'</div>'
        )

    # ---- 목표 달성 분석 섹션 ----
    tgt = data.get("목표")
    target_section_html = ""
    if tgt:
        tgt_money = fmt_money(tgt["목표매출"])
        tgt_current = fmt_money(tgt["현재매출"])
        tgt_remain = fmt_money(tgt["잔여매출"])
        tgt_daily = fmt_money(tgt["목표일매출"])
        tgt_recent_avg = fmt_money(tgt["최근3일평균"])
        tgt_pct = tgt["달성률"]
        # 달성률에 따른 색상
        pct_color = C_SUCCESS if tgt_pct >= 80 else (C_ACCENT if tgt_pct >= 60 else C_DANGER)
        # 프로그레스 바 너비
        bar_width = min(tgt_pct, 100)

        # 최근 3일 행
        recent_rows = ""
        for d in tgt["최근3일매출"]:
            recent_rows += f'<tr><td class="text-center">{d["날짜"]}</td><td class="text-right">{fmt_money(d["매출"])}</td></tr>'

        # 광고 전략 블록
        ad_strategy_html = ""
        ad_strat = tgt.get("광고전략")
        if ad_strat:
            cur_ad = fmt_money(ad_strat["현재일평균광고비"])
            rec_ad = fmt_money(ad_strat["권장일광고비"])
            growth = ad_strat["매출증가필요율"]
            ad_strategy_html = (
                f'<div style="margin-top:16px; padding:16px 20px; background:rgba(108,92,231,0.04); border-radius:10px; border-left:3px solid {C_PRIMARY};">'
                f'<div style="font-size:14px; font-weight:700; color:{C_TEXT}; margin-bottom:10px;">{"광고 노출 증대 & 효율 전략" if tgt["광고전략"]["매출증가필요율"] > 0 else "목표 달성 광고 운영 전략"}</div>'
                f'<div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">'
                f'<div style="font-size:12px; color:{C_TEXT_SECONDARY};">현재 일평균 광고비<br><strong style="font-size:16px; color:{C_TEXT};">{cur_ad}</strong></div>'
                f'<div style="font-size:12px; color:{C_TEXT_SECONDARY};">목표 달성 권장 광고비<br><strong style="font-size:16px; color:{C_PRIMARY};">{rec_ad}</strong></div>'
                f'</div>'
                f'<ul style="margin:12px 0 0; padding-left:18px; font-size:12px; color:{C_TEXT_SECONDARY}; line-height:1.8;">'
                f'<li>{f"일매출 <strong>+{growth:.1f}%</strong> 증가 필요 → 광고 노출량 확대로 트래픽 확보" if growth > 0 else f"목표 일매출이 현재 일평균의 <strong>{100 + growth:.1f}%</strong> 수준 → 현 광고비 유지로 달성 가능"}</li>'
                f'<li>현재 ROAS {ad_strat["현재ROAS"]}% {"유지하며 광고비 증액 → 매출 연동 성장" if growth > 0 else "유지가 우선 → 증액보다 효율 방어"}</li>'
                f'<li>고효율 키워드/캠페인에 예산 집중, 저효율 캠페인 정리</li>'
                f'<li>노출 지면 다각화 (검색 + 카테고리 + 외부채널) 병행</li>'
                f'</ul>'
                f'</div>'
            )

        target_section_html = f'''
            <div style="margin-top:20px; padding:20px 24px; background:{C_CARD}; border-radius:12px; border:1px solid {C_BORDER};">
                <div style="font-size:14px; font-weight:700; color:{C_TEXT}; margin-bottom:14px;">
                    &#x1f3af; 목표 매출 달성 분석
                </div>
                <div style="display:flex; align-items:center; gap:16px; margin-bottom:14px;">
                    <div style="flex:1;">
                        <div style="background:{C_BG}; border-radius:8px; height:24px; overflow:hidden;">
                            <div style="background:linear-gradient(90deg, {C_PRIMARY}, {C_PRIMARY_LIGHT}); height:100%; width:{bar_width}%; border-radius:8px; transition:width 0.5s;"></div>
                        </div>
                    </div>
                    <div style="font-size:20px; font-weight:800; color:{pct_color}; white-space:nowrap;">{tgt_pct}%</div>
                </div>
                <div class="kpi-grid">
                    <div class="kpi-card" style="border-left:3px solid {C_PRIMARY};">
                        <div class="label">목표 매출</div>
                        <div class="value" style="color:{C_PRIMARY};">{tgt_money}</div>
                        <div class="sub">당월 목표</div>
                    </div>
                    <div class="kpi-card" style="border-left:3px solid {C_SUCCESS};">
                        <div class="label">현재 달성</div>
                        <div class="value">{tgt_current}</div>
                        <div class="sub">{data["일수"]}일 기준</div>
                    </div>
                    <div class="kpi-card" style="border-left:3px solid {C_ACCENT};">
                        <div class="label">잔여 필요</div>
                        <div class="value" style="color:{C_ACCENT};">{tgt_remain}</div>
                        <div class="sub">남은 {tgt["잔여일수"]}일</div>
                    </div>
                    <div class="kpi-card" style="border-left:3px solid {C_DANGER};">
                        <div class="label">목표 일매출</div>
                        <div class="value" style="color:{C_DANGER};">{tgt_daily}</div>
                        <div class="sub">최근3일 평균의 {tgt["목표대비최근비율"]}%</div>
                    </div>
                </div>
                <div style="margin-top:14px;">
                    <div style="font-size:12px; font-weight:600; color:{C_TEXT_SECONDARY}; margin-bottom:6px;">최근 3일 매출 추이</div>
                    <table style="width:auto; min-width:200px;">
                        <thead><tr><th>날짜</th><th class="text-right">매출</th></tr></thead>
                        <tbody>{recent_rows}
                            <tr style="font-weight:700; border-top:2px solid {C_BORDER};"><td class="text-center">평균</td><td class="text-right">{tgt_recent_avg}</td></tr>
                        </tbody>
                    </table>
                </div>
                {ad_strategy_html}
            </div>'''

    # ---- 아이템위너 섹션 ----
    avg_iw = products.get("평균아이템위너비율", 0)

    # ---- 광고 운영 분석 & 전략 섹션 (키워드 데이터 기반) ----
    ad_ops = data.get("광고운영", {})
    ad_ops_section_html = ""
    if ad_ops.get("사용"):
        target = ad_ops["목표"]
        roas_total_color = C_SUCCESS if ad_ops["ROAS_전체매출"] >= 300 else (C_ACCENT if ad_ops["ROAS_전체매출"] >= 200 else C_DANGER)

        op_insight_items = ""
        for item in ad_ops.get("인사이트", []):
            op_insight_items += f'<li style="margin-bottom:6px;">{item}</li>'

        direction_items = ""
        for item in ad_ops.get("운영방향", []):
            direction_items += f'<li style="margin-bottom:6px;">{item}</li>'

        checkpoint_items = ""
        for item in ad_ops.get("체크포인트", []):
            checkpoint_items += f"""
            <div style="display:flex; align-items:center; padding:8px 12px; background:#F8F9FA; border-radius:8px; margin-bottom:6px;">
                <span style="color:{C_SUCCESS}; margin-right:8px; font-size:16px;">&#x2610;</span>
                <span>{item}</span>
            </div>"""

        ad_ops_section_html = f"""
        <!-- ===== 광고 운영 분석 & 전략 ===== -->
        <div class="section" id="ad-ops">
            <div class="section-title">
                <span class="icon icon-orange">&#x1f4ca;</span>
                광고 운영 분석 & {data["다음월"]} 전략
            </div>

            <!-- 광고 운영 요약 테이블 -->
            <div class="sub-heading">광고 운영 요약</div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>구분</th>
                            <th class="text-right">주요 내용</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td>총 광고비</td><td class="text-right"><strong>{fmt_money(ad_ops["총광고비"])}</strong></td></tr>
                        <tr><td>광고 전환 매출</td><td class="text-right"><strong>{fmt_money(ad_ops["광고전환매출"])}</strong></td></tr>
                        <tr><td>전체 매출</td><td class="text-right"><strong style="color:{C_PRIMARY}">{fmt_money(ad_ops["전체매출"])}</strong></td></tr>
                        <tr><td>ROAS (전체 매출 기준)</td><td class="text-right"><strong style="color:{roas_total_color}">{ad_ops["ROAS_전체매출"]}%</strong></td></tr>
                        <tr><td>노출수 / 클릭수 <span style="color:{C_TEXT_SECONDARY}; font-size:11px;">(쿠팡 검색광고 리포트 · 전 지면 합산)</span></td><td class="text-right">{ad_ops["노출수"]:,}회 / {ad_ops["클릭수"]:,}회</td></tr>
                        <tr><td>클릭률 (CTR) <span style="color:{C_TEXT_SECONDARY}; font-size:11px;">(쿠팡 검색광고 리포트 기준)</span></td><td class="text-right">{ad_ops["CTR"]}%</td></tr>
                        <tr><td>전환율 (CVR) <span style="color:{C_TEXT_SECONDARY}; font-size:11px;">(검색광고 · 1일 전환 기준)</span></td><td class="text-right">{ad_ops["CVR"]}%</td></tr>
                    </tbody>
                </table>
            </div>

            <!-- 운영 인사이트 -->
            <div class="sub-heading" style="margin-top:24px;">{data["월"]} 운영 인사이트</div>
            <div style="padding:16px 20px; background:#F0F9FF; border-radius:10px; border-left:4px solid {C_PRIMARY};">
                <ul style="margin:0; padding-left:20px; color:{C_TEXT};">
                    {op_insight_items}
                </ul>
            </div>

            <!-- 이번 달 목표 -->
            <div class="sub-heading" style="margin-top:24px;">{data["다음월"]} 목표</div>
            <div class="kpi-grid kpi-grid-3">
                <div class="kpi-card">
                    <div class="label">월 광고비 목표</div>
                    <div class="value">{target["월광고비범위"]}</div>
                </div>
                <div class="kpi-card highlight">
                    <div class="label">월 매출 목표</div>
                    <div class="value">{target["월매출범위"]}</div>
                </div>
                <div class="kpi-card">
                    <div class="label">목표 ROAS (전체 매출 기준)</div>
                    <div class="value">{target["목표ROAS"]}%</div>
                </div>
            </div>

            <!-- 목표 달성 운영 방향 -->
            <div class="sub-heading" style="margin-top:24px;">목표 달성을 위한 광고 운영 방향</div>
            <div style="padding:16px 20px; background:#FEF9E7; border-radius:10px; border-left:4px solid #F39C12;">
                <ul style="margin:0; padding-left:20px; color:{C_TEXT};">
                    {direction_items}
                </ul>
            </div>

            <!-- 실행 체크포인트 -->
            <div class="sub-heading" style="margin-top:24px;">실무 실행 체크포인트</div>
            {checkpoint_items}
        </div>
        """

    # ---- 키워드/지면 분석 섹션 (조건부) ----
    keyword_section_html = ""
    if kw_data:
        # 지면별 테이블
        placement_rows = ""
        for p in kw_data.get("지면별", []):
            placement_rows += f"""
            <tr>
                <td><strong>{p["광고 노출 지면"]}</strong></td>
                <td class="text-right">{int(p["노출수"]):,}</td>
                <td class="text-right">{int(p["클릭수"]):,}</td>
                <td class="text-right">{p["CTR"]}%</td>
                <td class="text-right">{fmt_money(int(p["광고비"]))}</td>
                <td class="text-right">{fmt_money(int(p["CPC"]))}</td>
                <td class="text-right">{fmt_money(int(p["매출"]))}</td>
                <td class="text-right {"text-success" if p["ROAS"] >= 200 else "text-danger"}">{p["ROAS"]}%</td>
            </tr>"""

        # 키워드 Top 매출 테이블
        kw_revenue_rows = ""
        for i, k in enumerate(kw_data.get("키워드_매출순", [])[:15]):
            roas_cls = "text-success" if k["ROAS"] >= 200 else ("text-warning" if k["ROAS"] >= 100 else "text-danger")
            kw_revenue_rows += f"""
            <tr>
                <td class="text-center">{i + 1}</td>
                <td><strong>{k["키워드"]}</strong></td>
                <td class="text-right">{int(k["노출수"]):,}</td>
                <td class="text-right">{int(k["클릭수"]):,}</td>
                <td class="text-right">{k["CTR"]}%</td>
                <td class="text-right">{fmt_money(int(k["광고비"]))}</td>
                <td class="text-right">{int(k["주문수"]):,}</td>
                <td class="text-right"><strong>{fmt_money(int(k["매출"]))}</strong></td>
                <td class="text-right {roas_cls}">{k["ROAS"]}%</td>
            </tr>"""

        # 낭비 키워드 테이블 (제목의 개수와 어긋나지 않도록 리스트를 한 번만 자른다)
        kw_waste_list = kw_data.get("키워드_낭비", [])[:10]
        kw_waste_rows = ""
        for k in kw_waste_list:
            kw_waste_rows += f"""
            <tr>
                <td><strong>{k["키워드"]}</strong></td>
                <td class="text-right">{int(k["노출수"]):,}</td>
                <td class="text-right">{int(k["클릭수"]):,}</td>
                <td class="text-right text-danger"><strong>{fmt_money(int(k["광고비"]))}</strong></td>
                <td class="text-right text-danger">0원</td>
                <td class="text-right text-danger">0%</td>
            </tr>"""

        # 캠페인별 테이블
        campaign_rows = ""
        for c in kw_data.get("캠페인별", []):
            c_roas_cls = "text-success" if c["ROAS"] >= 200 else ("text-warning" if c["ROAS"] >= 100 else "text-danger")
            campaign_rows += f"""
            <tr>
                <td class="product-name">{c["캠페인명"]}</td>
                <td class="text-right">{int(c["노출수"]):,}</td>
                <td class="text-right">{int(c["클릭수"]):,}</td>
                <td class="text-right">{c["CTR"]}%</td>
                <td class="text-right">{fmt_money(int(c["광고비"]))}</td>
                <td class="text-right">{fmt_money(int(c["매출"]))}</td>
                <td class="text-right {c_roas_cls}">{c["ROAS"]}%</td>
            </tr>"""

        waste_amount = fmt_money(kw_data.get("낭비키워드광고비", 0))

        keyword_section_html = f"""
        <!-- ===== 4-2. 키워드 / 지면별 분석 ===== -->
        <div class="section" id="keyword">
            <div class="section-title">
                <span class="icon icon-orange">&#x1f50d;</span>
                광고 키워드 &amp; 지면별 분석
            </div>

            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="label">총 노출수</div>
                    <div class="value">{kw_data["총노출수"]:,}</div>
                </div>
                <div class="kpi-card">
                    <div class="label">총 클릭수</div>
                    <div class="value">{kw_data["총클릭수"]:,}</div>
                </div>
                <div class="kpi-card">
                    <div class="label">평균 CTR</div>
                    <div class="value">{kw_data["평균CTR"]}%</div>
                </div>
                <div class="kpi-card">
                    <div class="label">평균 CPC</div>
                    <div class="value">{fmt_money(kw_data["평균CPC"])}</div>
                </div>
                <div class="kpi-card">
                    <div class="label">총 키워드 수</div>
                    <div class="value">{kw_data["총키워드수"]}개</div>
                    <div class="sub">매출 발생 {kw_data["매출발생키워드수"]}개</div>
                </div>
                <div class="kpi-card {"danger" if kw_data["낭비키워드광고비"] > 0 else ""}">
                    <div class="label">낭비 키워드 광고비</div>
                    <div class="value">{waste_amount}</div>
                    <div class="sub">주문 0건(1일 전환 기준) {kw_data.get("낭비키워드수", 0)}개 합산 · 광고비의 {(kw_data.get("낭비키워드광고비", 0) / kw_data["총광고비"] * 100 if kw_data.get("총광고비") else 0):.1f}%</div>
                </div>
            </div>

            <div class="sub-heading">광고 노출 지면별 성과</div>
            <div class="two-col">
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th>지면</th>
                                <th class="text-right">노출수</th>
                                <th class="text-right">클릭수</th>
                                <th class="text-right">CTR</th>
                                <th class="text-right">광고비</th>
                                <th class="text-right">CPC</th>
                                <th class="text-right">전환매출 <span style="font-weight:400; font-size:11px;">(1일)</span></th>
                                <th class="text-right">ROAS <span style="font-weight:400; font-size:11px;">(1일 기준)</span></th>
                            </tr>
                        </thead>
                        <tbody>{placement_rows}</tbody>
                    </table>
                </div>
                <div class="chart-container">{placement_chart}</div>
            </div>

            <div class="sub-heading">캠페인별 성과</div>
            <div class="chart-container">{campaign_chart}</div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>캠페인명</th>
                            <th class="text-right">노출수</th>
                            <th class="text-right">클릭수</th>
                            <th class="text-right">CTR</th>
                            <th class="text-right">광고비</th>
                            <th class="text-right">전환매출 <span style="font-weight:400; font-size:11px;">(1일)</span></th>
                            <th class="text-right">ROAS <span style="font-weight:400; font-size:11px;">(1일 기준)</span></th>
                        </tr>
                    </thead>
                    <tbody>{campaign_rows}</tbody>
                </table>
            </div>

            <div class="sub-heading">Top 키워드 (매출순)</div>
            <div class="chart-container">{keyword_chart}</div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th class="text-center">#</th>
                            <th>키워드</th>
                            <th class="text-right">노출수</th>
                            <th class="text-right">클릭수</th>
                            <th class="text-right">CTR</th>
                            <th class="text-right">광고비</th>
                            <th class="text-right">주문수 <span style="font-weight:400; font-size:11px;">(1일)</span></th>
                            <th class="text-right">전환매출 <span style="font-weight:400; font-size:11px;">(1일)</span></th>
                            <th class="text-right">ROAS <span style="font-weight:400; font-size:11px;">(1일 기준)</span></th>
                        </tr>
                    </thead>
                    <tbody>{kw_revenue_rows}</tbody>
                </table>
            </div>

            {"" if not kw_waste_rows else f'''
            <div class="sub-heading" style="color:{C_DANGER}">낭비 키워드 (광고비 지출, 매출 0원) <span style="font-weight:400; font-size:12px; color:#636E72;">&mdash; 주문 0건(1일 전환 기준) {kw_data.get("낭비키워드수", 0)}개 중 광고비 상위 {len(kw_waste_list)}개</span></div>
            <p style="font-size:12px; color:{C_TEXT_SECONDARY}; margin-bottom:8px;">
                아래 키워드는 광고비를 소진했으나 전환이 발생하지 않았습니다. 입찰가 조정 또는 제외 키워드 등록을 검토하세요.
            </p>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>키워드</th>
                            <th class="text-right">노출수</th>
                            <th class="text-right">클릭수</th>
                            <th class="text-right">광고비</th>
                            <th class="text-right">전환매출 <span style="font-weight:400; font-size:11px;">(1일)</span></th>
                            <th class="text-right">ROAS <span style="font-weight:400; font-size:11px;">(1일 기준)</span></th>
                        </tr>
                    </thead>
                    <tbody>{kw_waste_rows}</tbody>
                </table>
            </div>
            '''}
        </div>
        """

    # 원본에 빈 칸이 있어 0으로 채웠다면 맨 위에 알린다.
    # 자료가 빠진 것과 그날 실적이 진짜 0인 것을 읽는 사람이 구분할 수 있어야 한다.
    gaps = data.get("결측") or []
    gap_banner = ""
    if gaps:
        gap_items = ""
        for g in gaps:
            when = f' ({", ".join(g["날짜"])})' if g.get("날짜") else ""
            gap_items += f'<li><strong>{g["자료"]}</strong>의 <strong>{g["칸"]}</strong> {g["건수"]}건{when}</li>'
        gap_banner = f"""
        <div class="data-gap">
            <div class="data-gap-title">원본 자료에 빈 칸이 있었습니다</div>
            <ul>{gap_items}</ul>
            <div class="data-gap-note">
                빈 칸은 0으로 계산했습니다. 아래 숫자와 합계에 그대로 반영되어 있으니,
                해당 날짜의 실적이 실제로 0인지 자료가 빠진 것인지 확인하고 보십시오.
            </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>쿠팡 종합 리포트 - {data["월"]}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        html {{
            scroll-behavior: smooth;
        }}

        body {{
            font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, 'Malgun Gothic', sans-serif;
            background: {C_BG};
            color: {C_TEXT};
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }}

        .container {{
            max-width: 1240px;
            margin: 0 auto;
            padding: 24px;
        }}

        /* ===== Header ===== */
        .report-header {{
            background: linear-gradient(135deg, {C_PRIMARY} 0%, #8B5CF6 50%, #A78BFA 100%);
            border-radius: 16px;
            padding: 48px 40px;
            margin-bottom: 28px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(108,92,231,0.25);
            position: relative;
            overflow: hidden;
        }}

        .report-header::before {{
            content: '';
            position: absolute;
            top: -50%;
            right: -20%;
            width: 400px;
            height: 400px;
            background: rgba(255,255,255,0.05);
            border-radius: 50%;
        }}

        .report-header h1 {{
            font-size: 32px;
            font-weight: 800;
            color: #ffffff;
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }}

        .report-header .subtitle {{
            font-size: 16px;
            color: rgba(255,255,255,0.85);
            font-weight: 400;
        }}

        .report-header .period {{
            font-size: 13px;
            color: rgba(255,255,255,0.6);
            margin-top: 8px;
        }}

        /* ===== Navigation ===== */
        .nav-bar {{
            background: {C_CARD};
            border-radius: 12px;
            padding: 12px 20px;
            margin-bottom: 24px;
            display: flex;
            gap: 8px;
            flex-wrap: nowrap;
            overflow-x: auto;
            align-items: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            border: 1px solid {C_BORDER};
            position: sticky;
            top: 0;
            z-index: 100;
            -webkit-overflow-scrolling: touch;
        }}

        .nav-bar a {{
            color: {C_TEXT_SECONDARY};
            text-decoration: none;
            font-size: 13px;
            font-weight: 500;
            padding: 6px 14px;
            border-radius: 8px;
            transition: all 0.2s;
            white-space: nowrap;
            flex-shrink: 0;
        }}

        .nav-bar a:hover {{
            background: {C_BG};
            color: {C_PRIMARY};
        }}

        /* ===== Section ===== */
        .section {{
            background: {C_CARD};
            border-radius: 14px;
            padding: 28px 32px;
            margin-bottom: 20px;
            border: 1px solid {C_BORDER};
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            overflow-x: auto;
            scroll-margin-top: 64px; /* sticky nav에 섹션 제목 가림 방지 */
        }}

        .data-gap {{
            background: #FFF8E1;
            border: 1px solid #F5C400;
            border-left: 5px solid #F5C400;
            border-radius: 10px;
            padding: 18px 22px;
            margin-bottom: 20px;
            word-break: keep-all;
        }}
        .data-gap-title {{
            font-size: 15px;
            font-weight: 700;
            color: #7A5A00;
            margin-bottom: 10px;
        }}
        .data-gap ul {{
            margin: 0 0 10px 18px;
            padding: 0;
            font-size: 14px;
            color: {C_TEXT};
            line-height: 1.8;
        }}
        .data-gap-note {{
            font-size: 13px;
            color: #7A5A00;
            line-height: 1.7;
        }}

        .section-title {{
            font-size: 18px;
            font-weight: 700;
            color: {C_TEXT};
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid {C_BG};
            display: flex;
            align-items: center;
            gap: 10px;
            white-space: nowrap;
        }}

        .section-title .icon {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            border-radius: 8px;
            font-size: 18px;
        }}

        .icon-purple {{ background: rgba(108,92,231,0.1); color: {C_PRIMARY}; }}
        .icon-green {{ background: rgba(0,184,148,0.1); color: {C_SUCCESS}; }}
        .icon-orange {{ background: rgba(249,115,22,0.1); color: {C_ACCENT}; }}
        .icon-blue {{ background: rgba(116,185,255,0.1); color: {C_INFO}; }}
        .icon-red {{ background: rgba(225,112,85,0.1); color: {C_DANGER}; }}

        /* ===== KPI Cards ===== */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
            margin-bottom: 24px;
        }}

        .kpi-card {{
            background: {C_CARD};
            border-radius: 12px;
            padding: 20px;
            border: 1px solid {C_BORDER};
            text-align: center;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .kpi-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}

        .kpi-card .label {{
            font-size: 12px;
            color: {C_TEXT_SECONDARY};
            font-weight: 500;
            margin-bottom: 6px;
            white-space: nowrap;
        }}

        .kpi-card .value {{
            font-size: 24px;
            font-weight: 800;
            color: {C_TEXT};
            line-height: 1.2;
            white-space: nowrap;
        }}

        .kpi-card .sub {{
            font-size: 11px;
            color: {C_TEXT_SECONDARY};
            margin-top: 4px;
            white-space: nowrap;
        }}

        .kpi-card.highlight {{
            border-color: {C_PRIMARY};
            background: linear-gradient(135deg, rgba(108,92,231,0.04), rgba(139,92,246,0.08));
        }}

        .kpi-card.highlight .value {{
            color: {C_PRIMARY};
        }}

        .kpi-card.good {{
            border-color: {C_SUCCESS};
        }}

        .kpi-card.good .value {{
            color: {C_SUCCESS};
        }}

        .kpi-card.warning {{
            border-color: {C_ACCENT};
        }}

        .kpi-card.warning .value {{
            color: {C_ACCENT};
        }}

        .kpi-card.danger {{
            border-color: {C_DANGER};
        }}

        .kpi-card.danger .value {{
            color: {C_DANGER};
        }}

        /* ===== Tables ===== */
        .table-wrapper {{
            overflow-x: auto;
            margin-top: 16px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th {{
            background: {C_BG};
            color: {C_TEXT_SECONDARY};
            font-weight: 600;
            font-size: 12px;
            padding: 10px 14px;
            text-align: left;
            border-bottom: 2px solid {C_BORDER};
            white-space: nowrap;
        }}

        td {{
            padding: 10px 14px;
            font-size: 13px;
            border-bottom: 1px solid {C_BORDER};
            color: {C_TEXT};
            white-space: nowrap;
        }}

        tbody tr:hover {{
            background: rgba(108,92,231,0.03);
        }}

        tbody tr:nth-child(even) {{
            background: rgba(248,249,250,0.5);
        }}

        tbody tr:nth-child(even):hover {{
            background: rgba(108,92,231,0.03);
        }}

        .text-right {{ text-align: right; }}
        .text-center {{ text-align: center; }}
        .text-success {{ color: {C_SUCCESS}; }}
        .text-danger {{ color: {C_DANGER}; }}
        .text-warning {{ color: #F39C12; }}
        .text-muted {{ color: {C_TEXT_SECONDARY}; }}
        .text-primary {{ color: {C_PRIMARY}; }}

        .product-name {{
            font-weight: 500;
            white-space: normal;
            word-break: break-word;
        }}

        /* ===== Insight Cards ===== */
        .insight-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 14px;
        }}

        .insight-card {{
            border-radius: 12px;
            padding: 20px;
        }}

        .insight-badge {{
            font-size: 11px;
            font-weight: 700;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 4px;
        }}

        .material-icon {{
            font-family: 'Material Icons Outlined';
            font-size: 16px;
            vertical-align: middle;
        }}

        .insight-title {{
            font-size: 15px;
            font-weight: 700;
            color: {C_TEXT};
            margin-bottom: 6px;
        }}

        .insight-desc {{
            font-size: 13px;
            color: {C_TEXT_SECONDARY};
            line-height: 1.7;
        }}

        /* ===== Check Items ===== */
        .check-list {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}

        .check-item {{
            display: flex;
            gap: 14px;
            align-items: flex-start;
            background: {C_BG};
            border-radius: 10px;
            padding: 16px 20px;
        }}

        .check-badge {{
            font-size: 11px;
            font-weight: 700;
            color: white;
            padding: 3px 10px;
            border-radius: 6px;
            white-space: nowrap;
            flex-shrink: 0;
            margin-top: 2px;
        }}

        .check-title {{
            font-size: 14px;
            font-weight: 600;
            color: {C_TEXT};
            margin-bottom: 4px;
        }}

        .check-desc {{
            font-size: 12px;
            color: {C_TEXT_SECONDARY};
            line-height: 1.6;
        }}

        /* ===== Improvement Cards ===== */
        .improvements-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 14px;
        }}

        .improvement-card {{
            background: {C_BG};
            border-radius: 12px;
            padding: 20px;
        }}

        .improvement-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}

        .improvement-category {{
            font-size: 15px;
            font-weight: 700;
            color: {C_TEXT};
        }}

        .badge {{
            padding: 3px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            color: white;
            white-space: nowrap;
        }}

        .improvement-status {{
            font-size: 13px;
            color: {C_TEXT_SECONDARY};
            margin-bottom: 8px;
            padding: 8px 12px;
            background: {C_CARD};
            border-radius: 8px;
            border-left: 3px solid {C_ACCENT};
        }}

        .improvement-action {{
            font-size: 13px;
            color: {C_TEXT};
            padding: 8px 12px;
            background: {C_CARD};
            border-radius: 8px;
            border-left: 3px solid {C_SUCCESS};
        }}

        /* ===== Plan Badge ===== */
        .plan-badge {{
            background: {C_PRIMARY};
            color: white;
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            white-space: nowrap;
        }}

        /* ===== Correlation Cards ===== */
        .corr-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 14px;
        }}

        .corr-card {{
            background: {C_BG};
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }}

        .corr-label {{
            font-size: 12px;
            color: {C_TEXT_SECONDARY};
            font-weight: 500;
            margin-bottom: 8px;
            white-space: nowrap;
        }}

        .corr-value {{
            font-size: 32px;
            font-weight: 800;
            white-space: nowrap;
        }}

        .corr-desc {{
            font-size: 11px;
            color: {C_TEXT_SECONDARY};
            margin-top: 4px;
            white-space: nowrap;
        }}

        .kpi-grid-3 {{ grid-template-columns: repeat(3, 1fr); }}
        .kpi-grid-2 {{ grid-template-columns: repeat(2, 1fr); }}

        /* ===== Chart ===== */
        .chart-container {{
            margin: 16px 0;
        }}

        .chart-row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}

        /* ===== Two Column ===== */
        .two-col {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}

        /* ===== Footer ===== */
        .report-footer {{
            text-align: center;
            padding: 24px;
            color: {C_TEXT_SECONDARY};
            font-size: 12px;
        }}

        /* ===== Responsive: Tablet ===== */
        @media (max-width: 768px) {{
            .container {{ padding: 12px; }}
            .section {{ padding: 20px 16px; }}
            .chart-row, .two-col {{ grid-template-columns: 1fr; }}
            .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .improvements-grid, .insight-grid {{ grid-template-columns: 1fr; }}
            .corr-grid {{ grid-template-columns: 1fr; }}
            .nav-bar {{ padding: 8px 12px; gap: 4px; border-radius: 0 0 12px 12px; }}
            .nav-bar a {{ font-size: 12px; padding: 5px 10px; }}
            .report-header {{ padding: 32px 20px; }}
            .report-header h1 {{ font-size: 24px; }}
            .kpi-grid-3 {{ grid-template-columns: repeat(2, 1fr); }}
            .section-title {{ font-size: 16px; white-space: normal; }}
            .sub-heading {{ white-space: normal; }}
        }}

        /* ===== Responsive: Mobile ===== */
        @media (max-width: 480px) {{
            .container {{ padding: 8px; }}
            .section {{ padding: 16px 12px; border-radius: 10px; }}
            .report-header {{ padding: 24px 16px; border-radius: 12px; margin-bottom: 16px; }}
            .report-header h1 {{ font-size: 20px; }}
            .report-header .subtitle {{ font-size: 13px; }}
            .report-header .period {{ font-size: 11px; }}

            /* KPI 카드: 2열, 값 크기 축소 (인라인 스타일 오버라이드) */
            .kpi-grid {{ grid-template-columns: repeat(2, 1fr) !important; gap: 8px; margin-bottom: 16px; }}
            .kpi-grid-3 {{ grid-template-columns: repeat(2, 1fr); }}
            .kpi-grid-2 {{ grid-template-columns: repeat(2, 1fr); }}
            .two-col {{ grid-template-columns: 1fr; }}
            .kpi-card {{ padding: 14px 10px; border-radius: 10px; }}
            .kpi-card .value {{ font-size: 18px; white-space: normal; word-break: break-all; }}
            .kpi-card .label {{ font-size: 11px; }}
            .kpi-card .sub {{ font-size: 10px; white-space: normal; }}

            /* 섹션 타이틀 */
            .section-title {{ font-size: 15px; white-space: normal; gap: 6px; margin-bottom: 14px; }}
            .section-title .icon {{ width: 28px; height: 28px; font-size: 15px; }}
            .sub-heading {{ font-size: 13px; white-space: normal; }}

            /* 인사이트/개선사항 카드 */
            .insight-card {{ padding: 14px; }}
            .insight-title {{ font-size: 13px; }}
            .insight-desc {{ font-size: 12px; }}
            .improvement-card {{ padding: 14px; }}

            /* 체크리스트 세로 배치 */
            .check-item {{ flex-direction: column; gap: 8px; padding: 12px 14px; }}
            .check-badge {{ align-self: flex-start; }}

            /* 상관관계 카드 */
            .corr-grid {{ grid-template-columns: 1fr; gap: 8px; }}
            .corr-value {{ font-size: 24px; }}

            /* 테이블 */
            table {{ font-size: 11px; }}
            th {{ padding: 8px 6px; font-size: 11px; }}
            td {{ padding: 8px 6px; font-size: 11px; }}
            .product-name {{ max-width: 140px; }}

            /* 차트 */
            .chart-container {{ margin: 8px -12px; }}

            /* 스크롤 테이블 */
            .daily-table-wrap, .scroll-table-wrap {{ max-height: 400px; }}

            /* 맨 위로 버튼 */
            .back-to-top {{ right: 12px; bottom: 12px; width: 38px; height: 38px; font-size: 17px; }}
        }}

        /* ===== Print ===== */
        @media print {{
            * {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}

            body {{ background: white; }}
            .nav-bar {{ display: none; }}
            .back-to-top {{ display: none !important; }}
            .report-header {{ box-shadow: none; break-after: avoid; }}
            .report-header::before {{ display: none !important; }}

            .section {{
                box-shadow: none;
                border: 1px solid #ddd;
                break-inside: auto;
                page-break-inside: auto;
                overflow: visible !important;
            }}

            .section-title {{
                break-after: avoid;
                page-break-after: avoid;
            }}

            .sub-heading {{
                break-after: avoid;
                page-break-after: avoid;
            }}

            .kpi-grid {{
                break-inside: avoid;
                page-break-inside: avoid;
            }}

            .kpi-card {{
                break-inside: avoid;
                page-break-inside: avoid;
            }}

            .insight-card {{
                break-inside: avoid;
                page-break-inside: avoid;
            }}

            .check-item {{
                break-inside: avoid;
                page-break-inside: avoid;
            }}

            .improvement-card {{
                break-inside: avoid;
                page-break-inside: avoid;
            }}

            .corr-grid {{
                break-inside: avoid;
                page-break-inside: avoid;
            }}

            .chart-container {{
                break-inside: avoid;
                page-break-inside: avoid;
            }}

            .chart-row {{
                break-inside: avoid;
                page-break-inside: avoid;
            }}

            .table-wrapper {{
                break-inside: avoid;
                page-break-inside: avoid;
                overflow: visible !important;
            }}

            .daily-table-wrap, .scroll-table-wrap {{
                max-height: none !important;
                overflow: visible !important;
            }}

            table {{
                break-inside: auto;
                page-break-inside: auto;
            }}

            tr {{
                break-inside: avoid;
                page-break-inside: avoid;
            }}

            thead {{
                display: table-header-group;
            }}

            .two-col {{
                break-inside: avoid;
                page-break-inside: avoid;
            }}
        }}

        /* ===== Sub heading ===== */
        .sub-heading {{
            font-size: 15px;
            font-weight: 600;
            color: {C_TEXT};
            margin: 24px 0 12px;
            display: flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
        }}

        .sub-heading::before {{
            content: '';
            display: inline-block;
            width: 4px;
            height: 16px;
            background: {C_PRIMARY};
            border-radius: 2px;
        }}

        /* ===== Scroll table (일자별 상세, 제품별 등 긴 테이블) ===== */
        .daily-table-wrap, .scroll-table-wrap {{
            max-height: 500px;
            overflow-y: auto;
            border-radius: 8px;
            border: 1px solid {C_BORDER};
            margin-top: 16px;
        }}

        .daily-table-wrap table thead th, .scroll-table-wrap table thead th {{
            position: sticky;
            top: 0;
            z-index: 10;
            background: {C_BG};
        }}

        /* ===== 합계 행 ===== */
        .total-row td {{
            font-weight: 700;
            background: rgba(108,92,231,0.06);
            border-top: 2px solid {C_PRIMARY};
            color: {C_TEXT};
        }}

        /* ===== 맨 위로 버튼 ===== */
        .back-to-top {{
            position: fixed;
            right: 24px;
            bottom: 24px;
            width: 44px;
            height: 44px;
            background: {C_PRIMARY};
            color: #ffffff;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            text-decoration: none;
            box-shadow: 0 4px 12px rgba(108,92,231,0.35);
            z-index: 200;
            opacity: 0.85;
            transition: opacity 0.2s, transform 0.2s;
        }}

        .back-to-top:hover {{
            opacity: 1;
            transform: translateY(-2px);
        }}
    </style>
</head>
<body>
    <div class="container">

        <!-- ===== Header ===== -->
        <div class="report-header">
            <h1>쿠팡 종합 리포트</h1>
            <div class="subtitle">{data["월"]} 성과 분석 및 {data["다음월"]} 운영 플랜</div>
            <div class="period">분석 기간: {data["기간"]} ({data["일수"]}일)</div>
        </div>
{gap_banner}

        <!-- ===== Navigation ===== -->
        <div class="nav-bar" id="nav">
            <a href="#summary">종합 요약</a>
            <a href="#insights">핵심 인사이트</a>
            <a href="#checks">필수 확인</a>
            {"<a href='#ad-ops'>광고 운영 전략</a>" if ad_ops.get('사용') else ""}
            <a href="#improve">개선사항</a>
            <a href="#plan">운영 플랜</a>
            <span style="color:{C_BORDER}; padding:0 4px;">|</span>
            {"<a href='#ad'>광고 분석</a>" if ad_used else ""}
            {"<a href='#keyword'>키워드/지면</a>" if kw_data else ""}
            <a href="#sales">판매 분석</a>
            <a href="#products">제품 분석</a>
            <a href="#weekly">주간/요일</a>
            {"<a href='#cross'>교차 분석</a>" if ad_used else ""}
            <a href="#daily">일자별 상세</a>
        </div>

        <!-- ===== 1. Executive Summary ===== -->
        <div class="section" id="summary">
            <div class="section-title">
                <span class="icon icon-purple">&#x1f4ca;</span>
                종합 요약 (Executive Summary)
            </div>
            <div class="kpi-grid" style="grid-template-columns: repeat({6 if ad_used else 3}, 1fr);">
                <div class="kpi-card highlight">
                    <div class="label">총 매출</div>
                    <div class="value">{fmt_money(sales["총매출"])}</div>
                    <div class="sub">일평균 {fmt_money(sales["일평균매출"])}</div>
                </div>
                {"" if not ad_used else f'''<div class="kpi-card">
                    <div class="label">총 광고비</div>
                    <div class="value">{fmt_money(ad["총광고비"])}</div>
                    <div class="sub">일평균 {fmt_money(ad["일평균광고비"])}</div>
                </div>
                <div class="kpi-card {roas_status}">
                    <div class="label">ROAS</div>
                    <div class="value">{ad["ROAS"]}%</div>
                    <div class="sub">전체매출 / 광고비 기준</div>
                </div>'''}
                <div class="kpi-card">
                    <div class="label">총 주문</div>
                    <div class="value">{fmt_number(sales["총주문"])}건</div>
                    <div class="sub">일평균 {sales["일평균주문"]}건</div>
                </div>
                <div class="kpi-card">
                    <div class="label">총 방문자</div>
                    <div class="value">{fmt_number(sales["총방문자"])}명</div>
                    <div class="sub">일평균 {fmt_number(sales["일평균방문자"])}명</div>
                </div>
                <div class="kpi-card {cvr_status}">
                    <div class="label">평균 전환율 <span style="font-weight:400; font-size:11px;">(주문/조회)</span></div>
                    <div class="value">{sales["평균전환율"]}%</div>
                    <div class="sub">총 판매량 {fmt_number(sales["총판매량"])}개</div>
                </div>
            </div>

            <!-- 당월 예상 -->
            <div style="margin-top:20px;">
                <div style="font-size:14px; font-weight:700; color:{C_TEXT_SECONDARY}; margin-bottom:10px; padding-left:2px;">
                    &#x1f4c5; {data["월"]} 예상 실적 <span style="font-weight:400; font-size:12px; color:{C_TEXT_SECONDARY};">({fc.get("데이터일수", 0)}일 데이터 기준 → {fc.get("해당월일수", 28)}일 환산)</span>
                </div>
                <div class="kpi-grid">
                    <div class="kpi-card" style="border-left:3px solid {C_PRIMARY};">
                        <div class="label">예상 매출</div>
                        <div class="value">{fmt_money(fc.get("예상매출", 0))}</div>
                        <div class="sub">잔여 {fc.get("잔여일수", 0)}일 추가 예상</div>
                    </div>
                    {fc_ad_html}
                    <div class="kpi-card" style="border-left:3px solid {C_INFO};">
                        <div class="label">예상 주문</div>
                        <div class="value">{fmt_number(fc.get("예상주문", 0))}건</div>
                        <div class="sub">예상 방문자 {fmt_number(fc.get("예상방문자", 0))}명</div>
                    </div>
                </div>
            </div>
            {target_section_html}
        </div>

        <!-- ===== 2. Key Insights ===== -->
        <div class="section" id="insights">
            <div class="section-title">
                <span class="icon icon-purple">&#x1f4a1;</span>
                {data["월"]} 핵심 인사이트
            </div>
            <div class="insight-grid">
                {insight_cards_html}
            </div>
        </div>

        <!-- ===== 3. Must Checks ===== -->
        <div class="section" id="checks">
            <div class="section-title">
                <span class="icon icon-red">&#x2705;</span>
                이번 달 필수 확인사항
            </div>
            <div class="check-list">
                {check_rows_html}
            </div>
        </div>

        {ad_ops_section_html}

        <!-- ===== 개선사항 ===== -->
        <div class="section" id="improve">
            <div class="section-title">
                <span class="icon icon-orange">&#x1f4a1;</span>
                {data["다음월"]} 개선사항
            </div>
            <div class="improvements-grid">
                {improvement_cards}
            </div>
        </div>

        <!-- ===== 운영 플랜 ===== -->
        <div class="section" id="plan">
            <div class="section-title">
                <span class="icon icon-green">&#x1f680;</span>
                {data["다음월"]} 운영 플랜
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>영역</th>
                            <th>목표</th>
                            <th>세부 계획</th>
                            <th>KPI</th>
                        </tr>
                    </thead>
                    <tbody>
                        {plan_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- ===== 상세 분석 구분선 ===== -->
        <div style="text-align:center; margin:32px 0 24px; position:relative;">
            <hr style="border:none; border-top:1px solid {C_BORDER}; margin:0;">
            <span style="background:{C_BG}; padding:0 16px; font-size:13px; font-weight:600; color:{C_TEXT_SECONDARY}; position:relative; top:-10px;">상세 분석 데이터</span>
        </div>

        {"" if not ad_used else f'''
        <!-- ===== 광고 성과 분석 ===== -->
        <div class="section" id="ad">
            <div class="section-title">
                <span class="icon icon-orange">&#x1f4b0;</span>
                {data["월"]} 광고 성과 분석
            </div>

            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="label">총 광고비</div>
                    <div class="value">{fmt_money(ad["총광고비"])}</div>
                    <div class="sub">일평균 {fmt_money(ad["일평균광고비"])}</div>
                </div>
                <div class="kpi-card">
                    <div class="label">총 광고매출 <span style="font-weight:400; font-size:11px;">(14일 전환 기준)</span></div>
                    <div class="value">{fmt_money(ad["총광고매출"])}</div>
                    <div class="sub">일평균 {fmt_money(ad["일평균광고매출"])}</div>
                </div>
                <div class="kpi-card {roas_status}">
                    <div class="label">ROAS</div>
                    <div class="value">{ad["ROAS"]}%</div>
                    <div class="sub">전체매출 / 광고비 기준</div>
                </div>
                <div class="kpi-card">
                    <div class="label">광고비 최대일</div>
                    <div class="value">{ad["광고비최대일"]}</div>
                    <div class="sub">{fmt_money(ad["광고비최대금액"])}</div>
                </div>
                <div class="kpi-card">
                    <div class="label">ROAS 최고일 <span style="font-weight:400; font-size:11px;">(광고매출 14일 기준)</span></div>
                    <div class="value">{ad["ROAS최고일"]}</div>
                    <div class="sub">{ad["ROAS최고값"]}%</div>
                </div>
                <div class="kpi-card">
                    <div class="label">ROAS 최저일 <span style="font-weight:400; font-size:11px;">(광고매출 14일 기준)</span></div>
                    <div class="value">{ad["ROAS최저일"]}</div>
                    <div class="sub">{ad["ROAS최저값"]}%</div>
                </div>
            </div>

            <div class="chart-container">
                {ad_trend_chart}
            </div>
        </div>
        '''}

        {keyword_section_html}

        <!-- ===== 판매 성과 분석 ===== -->
        <div class="section" id="sales">
            <div class="section-title">
                <span class="icon icon-green">&#x1f6d2;</span>
                {data["월"]} 판매 성과 분석
            </div>

            <div class="kpi-grid">
                <div class="kpi-card highlight">
                    <div class="label">총 매출</div>
                    <div class="value">{fmt_money(sales["총매출"])}</div>
                    <div class="sub">일평균 {fmt_money(sales["일평균매출"])}</div>
                </div>
                <div class="kpi-card">
                    <div class="label">매출 최고일</div>
                    <div class="value">{sales["매출최고일"]}</div>
                    <div class="sub">{fmt_money(sales["매출최고금액"])}</div>
                </div>
                <div class="kpi-card">
                    <div class="label">매출 최저일</div>
                    <div class="value">{sales["매출최저일"]}</div>
                    <div class="sub">{fmt_money(sales["매출최저금액"])}</div>
                </div>
                <div class="kpi-card">
                    <div class="label">전환율 최고일</div>
                    <div class="value">{sales["전환율최고일"]}</div>
                    <div class="sub">{sales["전환율최고값"]}%</div>
                </div>
                <div class="kpi-card">
                    <div class="label">조회 &rarr; 장바구니</div>
                    <div class="value">{sales["조회당장바구니율"]}%</div>
                    <div class="sub">장바구니 &rarr; 주문 {sales["장바구니당주문율"]}%</div>
                </div>
                <div class="kpi-card">
                    <div class="label">방문 &rarr; 주문</div>
                    <div class="value">{sales["방문당주문율"]}%</div>
                    <div class="sub">총 판매량 {fmt_number(sales["총판매량"])}개</div>
                </div>
            </div>

            <div class="chart-container">
                {sales_trend_chart}
            </div>

            <div class="chart-row">
                <div class="chart-container">
                    {revenue_trend_chart}
                </div>
                <div class="chart-container">
                    {funnel_chart}
                </div>
            </div>
        </div>

        <!-- ===== 제품별 분석 ===== -->
        <div class="section" id="products">
            <div class="section-title">
                <span class="icon icon-purple">&#x1f4e6;</span>
                제품별 판매 분석
            </div>

            <div class="chart-container">
                {product_chart}
            </div>

            <div class="sub-heading">상품별 매출 상세 <span style="font-weight:400; font-size:12px; color:{C_TEXT_SECONDARY};">(총 {len(products["상품별요약"])}개 상품 · 매출순)</span></div>
            <div class="scroll-table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th class="text-center">#</th>
                            <th>상품명</th>
                            <th class="text-right">방문자</th>
                            <th class="text-right">조회</th>
                            <th class="text-right">장바구니</th>
                            <th class="text-right">주문</th>
                            <th class="text-right">판매량</th>
                            <th class="text-right">매출</th>
                            <th class="text-right">전환율 <span style="font-weight:400; font-size:11px;">(주문/방문자)</span></th>
                        </tr>
                    </thead>
                    <tbody>
                        {product_rows}
                    </tbody>
                </table>
            </div>

            {"" if not iw_rows else f'''
            <div class="sub-heading">아이템위너 분석</div>
            <div class="two-col">
                <div>
                    <div class="kpi-grid kpi-grid-2">
                        <div class="kpi-card {"good" if avg_iw >= 70 else "warning" if avg_iw >= 40 else "danger"}">
                            <div class="label">평균 아이템위너 비율 <span style="font-weight:400; font-size:11px;">(옵션 기준)</span></div>
                            <div class="value">{avg_iw:.1f}%</div>
                            <div class="sub">{"양호" if avg_iw >= 70 else "주의 필요" if avg_iw >= 40 else "개선 시급"}</div>
                        </div>
                        <div class="kpi-card">
                            <div class="label">분석 상품 수</div>
                            <div class="value">{len(products.get("아이템위너", []))}개</div>
                        </div>
                    </div>
                    <div class="table-wrapper">
                        <table>
                            <thead>
                                <tr>
                                    <th>상품명</th>
                                    <th class="text-right">아이템위너 비율</th>
                                    <th class="text-right">매출</th>
                                </tr>
                            </thead>
                            <tbody>
                                {iw_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
                <div class="chart-container">
                    {item_winner_chart}
                </div>
            </div>
            '''}

            {"" if not category_rows else f'''
            <div class="sub-heading">카테고리별 분석</div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>카테고리</th>
                            <th class="text-right">매출</th>
                            <th class="text-right">주문</th>
                            <th class="text-right">방문자</th>
                        </tr>
                    </thead>
                    <tbody>
                        {category_rows}
                    </tbody>
                </table>
            </div>
            '''}

            {"" if not cancel_rows else f'''
            <div class="sub-heading" style="color:{C_DANGER}">취소/반품 현황</div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>상품명</th>
                            <th>옵션명</th>
                            <th class="text-right">취소 금액</th>
                            <th class="text-right">취소 수량</th>
                        </tr>
                    </thead>
                    <tbody>
                        {cancel_rows}
                    </tbody>
                </table>
            </div>
            '''}
        </div>

        <!-- ===== 제품 트렌드 분석 ===== -->
        {"" if not trend else f'''
        <div class="section" id="product-trend">
            <div class="section-title">
                <span class="icon icon-orange">&#x1f4ca;</span>
                제품 트렌드 분석
            </div>

            <div class="two-col">
                <div>
                    <div class="sub-heading">판매량 상위 5개 제품</div>
                    <div class="table-wrapper">
                        <table>
                            <thead><tr><th>상품명</th><th class="text-right">판매량</th><th class="text-right">매출</th><th class="text-right">전환율 <span style="font-weight:400; font-size:11px;">(주문/방문자)</span></th></tr></thead>
                            <tbody>{top5_rows}</tbody>
                        </table>
                    </div>
                </div>
                <div>
                    <div class="sub-heading">판매량 하위 5개 제품</div>
                    <div class="table-wrapper">
                        <table>
                            <thead><tr><th>상품명</th><th class="text-right">판매량</th><th class="text-right">매출</th><th class="text-right">전환율 <span style="font-weight:400; font-size:11px;">(주문/방문자)</span></th></tr></thead>
                            <tbody>{bottom5_rows}</tbody>
                        </table>
                    </div>
                </div>
            </div>

            {trend_rising_html}
            {trend_falling_html}
            {trend_inc_html}
            {trend_dec_html}
        </div>
        '''}

        <!-- ===== 8. 주간별 / 요일별 분석 ===== -->
        <div class="section" id="weekly">
            <div class="section-title">
                <span class="icon icon-blue">&#x1f4c8;</span>
                주간별 {"/ 요일별 " if ad_used else ""}성과 분석
            </div>

            <div class="sub-heading">주간별 성과 요약</div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        {"" if not ad_used else '''<tr>
                            <th class="text-center">주차</th>
                            <th class="text-right">광고비</th>
                            <th class="text-right">광고매출 <span style="font-weight:400; font-size:11px;">(14일)</span></th>
                            <th class="text-right">ROAS (광고매출 14일 기준)</th>
                            <th class="text-right">매출</th>
                            <th class="text-right">주문</th>
                            <th class="text-right">전환율 <span style="font-weight:400; font-size:11px;">(주문/조회)</span></th>
                        </tr>'''}
                        {"" if ad_used else '''<tr>
                            <th class="text-center">주차</th>
                            <th class="text-right">매출</th>
                            <th class="text-right">주문</th>
                            <th class="text-right">전환율 <span style="font-weight:400; font-size:11px;">(주문/조회)</span></th>
                        </tr>'''}
                    </thead>
                    <tbody>
                        {weekly_rows}
                    </tbody>
                </table>
            </div>

            {"" if not ad_used else f'''<div class="chart-container" style="margin-top:24px;">
                {weekday_chart}
            </div>'''}
        </div>

        {cross_section_html}

        <!-- ===== 일자별 상세 분석 (참고 데이터) ===== -->
        <div class="section" id="daily">
            <div class="section-title">
                <span class="icon icon-blue">&#x1f4c5;</span>
                일자별 상세 분석 데이터
            </div>
            <p style="font-size:13px; color:{C_TEXT_SECONDARY}; margin-bottom:12px;">
                {"광고 데이터와 판매 데이터를 일자별로 통합한 상세 테이블입니다." if ad_used else "판매 데이터를 일자별로 정리한 상세 테이블입니다."}
            </p>
            <div class="daily-table-wrap">
                <table>
                    <thead>
                        {"" if not ad_used else '''<tr>
                            <th class="text-center">날짜</th>
                            <th class="text-right">광고비</th>
                            <th class="text-right">광고매출 <span style="font-weight:400; font-size:11px;">(14일)</span></th>
                            <th class="text-right">ROAS (광고매출 14일 기준)</th>
                            <th class="text-right">방문자</th>
                            <th class="text-right">조회</th>
                            <th class="text-right">장바구니</th>
                            <th class="text-right">주문</th>
                            <th class="text-right">전환율 <span style="font-weight:400; font-size:11px;">(주문/조회)</span></th>
                            <th class="text-right">매출</th>
                        </tr>'''}
                        {"" if ad_used else '''<tr>
                            <th class="text-center">날짜</th>
                            <th class="text-right">방문자</th>
                            <th class="text-right">조회</th>
                            <th class="text-right">장바구니</th>
                            <th class="text-right">주문</th>
                            <th class="text-right">전환율 <span style="font-weight:400; font-size:11px;">(주문/조회)</span></th>
                            <th class="text-right">매출</th>
                        </tr>'''}
                    </thead>
                    <tbody>
                        {daily_detail_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- ===== Footer ===== -->
        <div class="report-footer">
            <p style="margin-bottom:4px;">이 리포트는 <strong>쿠팡 리포트 에이전트</strong>에 의해 자동 생성되었습니다.</p>
            <p>생성일: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
        </div>

        <a href="#" class="back-to-top" aria-label="맨 위로">&#8679;</a>
    </div>
</body>
</html>"""

    return html
