"""
쿠팡 종합 리포트 - Notion 연동 모듈
분석 데이터를 Notion 페이지에 자동 업로드합니다.
"""

import io
import json
import unicodedata
import zipfile
import requests
from pathlib import Path
from notion_client import Client
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def _rich_text(text: str, bold: bool = False, color: str = "default") -> dict:
    """Notion rich_text 객체 생성"""
    rt = {
        "type": "text",
        "text": {"content": text},
        "annotations": {
            "bold": bold,
            "italic": False,
            "strikethrough": False,
            "underline": False,
            "code": False,
            "color": color,
        },
    }
    return rt


def _heading(text: str, level: int = 2) -> dict:
    """Notion heading 블록"""
    block_type = f"heading_{level}"
    return {
        "object": "block",
        "type": block_type,
        block_type: {
            "rich_text": [_rich_text(text)],
            "color": "default",
        },
    }


def _paragraph(text: str, bold: bool = False, color: str = "default") -> dict:
    """Notion paragraph 블록"""
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [_rich_text(text, bold=bold, color=color)],
        },
    }


def _bulleted(text: str, bold_prefix: str = "", color: str = "default") -> dict:
    """Notion bulleted list 블록"""
    rich = []
    if bold_prefix:
        rich.append(_rich_text(bold_prefix, bold=True, color=color))
        rich.append(_rich_text(text))
    else:
        rich.append(_rich_text(text, color=color))

    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": rich},
    }


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def _callout(text: str, emoji: str = "💡", color: str = "blue_background") -> dict:
    """Notion callout 블록"""
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [_rich_text(text)],
            "icon": {"type": "emoji", "emoji": emoji},
            "color": color,
        },
    }


def _table_row(cells: list) -> dict:
    """Notion table row"""
    return {
        "type": "table_row",
        "table_row": {
            "cells": [[_rich_text(str(c))] for c in cells],
        },
    }


def _fmt_money(value: int) -> str:
    """금액 포맷"""
    if abs(value) >= 10000:
        man = value / 10000
        if man == int(man):
            return f"{int(man):,}만원"
        return f"{man:,.1f}만원"
    return f"{value:,}원"


# ============================================================
#  Plotly PNG → Notion File Upload 차트 이미지 생성
# ============================================================

CHART_COLORS = ["#4A90D9", "#E17055", "#00B894", "#F39C12", "#6C5CE7", "#74B9FF", "#FD79A8", "#55E6C1"]

# Notion API key는 export_to_notion에서 설정
_notion_api_key = None


def _ascii_filename(filename: str, fallback_stem: str = "coupang_report") -> str:
    """Notion은 파일명의 비ASCII 문자를 '_'로 치환하므로 미리 읽을 수 있는 ASCII 이름으로 변환"""
    p = Path(filename)
    ascii_stem = "".join(c if c.isascii() and (c.isalnum() or c in "-_") else "_" for c in p.stem)
    ascii_stem = "_".join(part for part in ascii_stem.split("_") if part)
    # 한글 브랜드명 등이 모두 걸러져 날짜만 남는 경우 식별 가능하도록 접두사를 붙인다
    if not any(c.isalpha() for c in ascii_stem):
        ascii_stem = f"{fallback_stem}_{ascii_stem}" if ascii_stem else fallback_stem
    return ascii_stem + p.suffix


def _upload_file_to_notion(file_bytes: bytes, filename: str, content_type: str = "image/png") -> str:
    """파일 바이트를 Notion File Upload API로 업로드하고 file_upload ID 반환"""
    if not _notion_api_key:
        return ""
    headers = {
        "Authorization": f"Bearer {_notion_api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    # Step 1: Create upload
    r1 = requests.post("https://api.notion.com/v1/file_uploads", headers=headers, json={
        "name": filename, "content_type": content_type,
    })
    if r1.status_code != 200:
        return ""
    upload = r1.json()
    upload_id = upload["id"]
    upload_url = upload["upload_url"]

    # Step 2: Send file
    r2 = requests.post(upload_url, headers={
        "Authorization": f"Bearer {_notion_api_key}",
        "Notion-Version": "2022-06-28",
    }, files={"file": (filename, file_bytes, content_type)})
    if r2.status_code != 200:
        return ""

    return upload_id


def _create_chart_upload(fig, filename: str) -> str:
    """Plotly figure를 PNG로 변환 후 Notion에 업로드, file_upload ID 반환"""
    try:
        png_bytes = fig.to_image(format="png", width=800, height=400, scale=2)
        return _upload_file_to_notion(png_bytes, filename, "image/png")
    except Exception as e:
        print(f"  [경고] 차트 이미지 생성 실패 ({filename}): {e}")
        return ""


def _image_block_from_upload(upload_id: str) -> dict:
    """Notion file_upload 기반 image block"""
    return {
        "object": "block",
        "type": "image",
        "image": {
            "type": "file_upload",
            "file_upload": {"id": upload_id},
        },
    }


def _generate_charts(data: dict) -> dict:
    """분석 데이터에서 Plotly 차트 → Notion file_upload ID 생성"""
    uploads = {}
    sales = data["판매"]
    products = data["제품"]
    ad = data["광고"]
    ad_used = ad.get("사용", False)

    daily = sales.get("일별", [])
    if not daily:
        return uploads

    labels = [d["날짜str"] for d in daily]

    # 1. 매출·주문 트렌드
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=labels, y=[round(int(d["매출"]) / 10000, 1) for d in daily],
        name="매출(만원)", fill="tozeroy",
        line=dict(color="#4A90D9"), fillcolor="rgba(74,144,217,0.1)",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=labels, y=[int(d["주문"]) for d in daily],
        name="주문(건)", line=dict(color="#E17055"),
    ), secondary_y=True)
    fig.update_layout(title="일별 매출·주문 트렌드", template="plotly_white",
                      legend=dict(orientation="h", y=1.12), margin=dict(l=50, r=50, t=60, b=40))
    fig.update_yaxes(title_text="매출(만원)", secondary_y=False)
    fig.update_yaxes(title_text="주문(건)", secondary_y=True)
    uploads["sales_trend"] = _create_chart_upload(fig, "sales_trend.png")

    # 2. 방문자·전환율 트렌드
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    fig2.add_trace(go.Scatter(
        x=labels, y=[int(d["방문자"]) for d in daily],
        name="방문자", line=dict(color="#00B894"),
    ), secondary_y=False)
    fig2.add_trace(go.Scatter(
        x=labels, y=[round(d["구매전환율"], 2) for d in daily],
        name="전환율(%)", line=dict(color="#F39C12"),
    ), secondary_y=True)
    fig2.update_layout(title="일별 방문자·전환율 트렌드", template="plotly_white",
                       legend=dict(orientation="h", y=1.12), margin=dict(l=50, r=50, t=60, b=40))
    fig2.update_yaxes(title_text="방문자", secondary_y=False)
    fig2.update_yaxes(title_text="전환율(%)", secondary_y=True)
    uploads["visitors"] = _create_chart_upload(fig2, "visitors_trend.png")

    # 3. 제품별 매출 TOP 8
    top_products = products.get("상품별요약", [])[:8]
    if top_products:
        tp_rev = list(reversed(top_products))
        fig3 = go.Figure(go.Bar(
            y=[p["상품명"] for p in tp_rev],
            x=[round(int(p["매출"]) / 10000, 1) for p in tp_rev],
            orientation="h",
            marker_color=list(reversed(CHART_COLORS[:len(top_products)])),
        ))
        fig3.update_layout(title="제품별 매출 TOP 8", template="plotly_white",
                           showlegend=False, margin=dict(l=200, r=30, t=60, b=40))
        fig3.update_xaxes(title_text="매출(만원)")
        uploads["product"] = _create_chart_upload(fig3, "product_top8.png")

    # 4. 광고 트렌드 (광고 데이터 있을 때만)
    if ad_used and ad.get("일별"):
        ad_daily = ad["일별"]
        ad_labels = [d["날짜str"] for d in ad_daily]
        fig4 = make_subplots(specs=[[{"secondary_y": True}]])
        fig4.add_trace(go.Scatter(
            x=ad_labels, y=[round(int(d["광고비"]) / 10000, 1) for d in ad_daily],
            name="광고비(만원)", line=dict(color="#E17055"),
        ), secondary_y=False)
        fig4.add_trace(go.Scatter(
            x=ad_labels, y=[round(int(d["광고매출"]) / 10000, 1) for d in ad_daily],
            name="광고매출(만원)", line=dict(color="#4A90D9"),
        ), secondary_y=False)
        fig4.add_trace(go.Scatter(
            x=ad_labels, y=[round(float(d["ROAS"]), 1) for d in ad_daily],
            name="ROAS(%)", line=dict(color="#00B894"),
        ), secondary_y=True)
        fig4.update_layout(title="일별 광고 성과 트렌드", template="plotly_white",
                           legend=dict(orientation="h", y=1.12), margin=dict(l=50, r=50, t=60, b=40))
        fig4.update_yaxes(title_text="금액(만원)", secondary_y=False)
        fig4.update_yaxes(title_text="ROAS(%)", secondary_y=True)
        uploads["ad_trend"] = _create_chart_upload(fig4, "ad_trend.png")

    return uploads


def build_notion_blocks(data: dict) -> list:
    """분석 데이터로 Notion 블록 리스트 생성"""
    blocks = []
    ad = data["광고"]
    ad_used = ad.get("사용", False)
    sales = data["판매"]
    products = data["제품"]
    cross = data["교차분석"]
    insights = data.get("인사이트", [])
    must_checks = data.get("필수확인", [])
    improvements = data.get("개선사항", [])
    plans = data.get("운영플랜", [])

    # 차트 이미지 생성
    chart_urls = _generate_charts(data)

    # ===== 헤더 =====
    blocks.append(_callout(
        f'{data["월"]} 성과 분석 및 {data["다음월"]} 운영 플랜  |  분석 기간: {data["기간"]} ({data["일수"]}일)',
        emoji="📊",
        color="blue_background",
    ))
    blocks.append(_paragraph(""))

    # ===== 1. Executive Summary (최상단) =====
    blocks.append(_heading("Executive Summary", level=2))

    summary_table_children = [
        _table_row(["지표", "값", "비고"]),
        _table_row(["총 매출", _fmt_money(sales["총매출"]), f"일평균 {_fmt_money(sales['일평균매출'])}"]),
    ]
    if ad_used:
        summary_table_children.append(_table_row(["총 광고비", _fmt_money(ad["총광고비"]), f"일평균 {_fmt_money(ad['일평균광고비'])}"]))
        summary_table_children.append(_table_row(["ROAS (전체매출 기준)", f'{ad["ROAS"]}%', f"광고 전환매출(14일) {_fmt_money(ad['총광고매출'])}"]))
    summary_table_children += [
        _table_row(["총 주문", f'{sales["총주문"]}건', f"일평균 {sales['일평균주문']}건"]),
        _table_row(["총 방문자", f'{sales["총방문자"]:,}명', f"일평균 {sales['일평균방문자']:,}명"]),
        _table_row(["평균 전환율 (주문/조회)", f'{sales["평균전환율"]}%', f"총 판매량 {sales['총판매량']}개"]),
    ]
    if ad_used:
        summary_table_children.append(_table_row(["순이익 추정", _fmt_money(cross["순이익추정"]), "매출 - 광고비"]))
    blocks.append({
        "object": "block",
        "type": "table",
        "table": {
            "table_width": 3,
            "has_column_header": True,
            "has_row_header": False,
            "children": summary_table_children,
        },
    })
    blocks.append(_paragraph(""))

    # ===== 당월 예상 실적 =====
    fc = data.get("예상", {})
    if fc:
        fc_days = fc.get("데이터일수", 0)
        fc_total = fc.get("해당월일수", 28)
        blocks.append(_heading(f"당월 예상 실적 ({fc_days}일 데이터 → {fc_total}일 환산)", level=3))
        fc_table_children = [
            _table_row(["지표", "예상 값", "비고"]),
            _table_row(["예상 매출", _fmt_money(fc.get("예상매출", 0)), f"일평균 {_fmt_money(sales['일평균매출'])} × {fc_total}일"]),
        ]
        if ad_used:
            fc_table_children.append(_table_row(["예상 광고비", _fmt_money(fc.get("예상광고비", 0)), f"일평균 {_fmt_money(ad['일평균광고비'])} 유지 시"]))
            fc_table_children.append(_table_row(["예상 ROAS", f'{fc.get("예상ROAS", 0)}%', f"예상 광고매출 {_fmt_money(fc.get('예상광고매출', 0))}"]))
        fc_table_children += [
            _table_row(["예상 주문", f'{fc.get("예상주문", 0):,}건', f"잔여 {fc.get('잔여일수', 0)}일 추가 예상"]),
            _table_row(["예상 방문자", f'{fc.get("예상방문자", 0):,}명', ""]),
        ]
        blocks.append({
            "object": "block",
            "type": "table",
            "table": {
                "table_width": 3,
                "has_column_header": True,
                "has_row_header": False,
                "children": fc_table_children,
            },
        })
        blocks.append(_paragraph(""))

    # 차트: 매출·주문 트렌드
    if chart_urls.get("sales_trend"):
        blocks.append(_heading("매출·주문 트렌드", level=3))
        blocks.append(_image_block_from_upload(chart_urls["sales_trend"]))
        blocks.append(_paragraph(""))

    # ===== 2. 핵심 인사이트 =====
    blocks.append(_heading("핵심 인사이트", level=2))
    insight_emoji = {"positive": "✅", "warning": "⚠️", "danger": "🚨", "info": "ℹ️"}
    insight_color = {"positive": "green", "warning": "orange", "danger": "red", "info": "blue"}
    for ins in insights:
        emoji = insight_emoji.get(ins["유형"], "ℹ️")
        color = insight_color.get(ins["유형"], "default")
        blocks.append(_callout(
            f'{ins["제목"]}\n{ins["내용"]}',
            emoji=emoji,
            color=f"{color}_background",
        ))
    blocks.append(_paragraph(""))

    # ===== 3. 필수 확인사항 =====
    blocks.append(_heading("이번 달 필수 확인사항", level=2))
    check_emoji = {"긴급": "🔴", "필수": "🟠", "높음": "🟡", "중간": "🟢"}
    for chk in must_checks:
        emoji = check_emoji.get(chk["중요도"], "⚪")
        blocks.append(_bulleted(
            f' {chk["항목"]}  ·  {chk["설명"]}',
            bold_prefix=f'{emoji} [{chk["중요도"]}]',
        ))
    blocks.append(_paragraph(""))

    # ===== 4. 광고 운영 분석 & 전략 (키워드 데이터 기반) =====
    ad_ops = data.get("광고운영", {})
    if ad_ops.get("사용"):
        blocks.append(_divider())
        blocks.append(_heading(f'광고 운영 분석 & {data["다음월"]} 전략', level=2))

        # 광고 운영 요약 테이블
        blocks.append(_heading("광고 운영 요약", level=3))
        ops_table = [
            _table_row(["구분", "주요 내용"]),
            _table_row(["총 광고비", _fmt_money(ad_ops["총광고비"])]),
            _table_row(["광고 전환 매출 (14일 전환 기준)", _fmt_money(ad_ops["광고전환매출"])]),
            _table_row(["전체 매출", _fmt_money(ad_ops["전체매출"])]),
            _table_row(["ROAS (전체 매출 기준)", f'{ad_ops["ROAS_전체매출"]}%']),
            _table_row(["노출수 / 클릭수 (쿠팡 검색광고 리포트 · 전 지면 합산)", f'{ad_ops["노출수"]:,}회 / {ad_ops["클릭수"]:,}회']),
            _table_row(["클릭률 (CTR, 검색광고 기준)", f'{ad_ops["CTR"]}%']),
            _table_row(["전환율 (CVR, 검색광고 · 1일 전환 기준)", f'{ad_ops["CVR"]}%']),
        ]
        blocks.append({
            "object": "block",
            "type": "table",
            "table": {
                "table_width": 2,
                "has_column_header": True,
                "has_row_header": False,
                "children": ops_table,
            },
        })
        blocks.append(_paragraph(""))

        # 운영 인사이트
        blocks.append(_heading(f'{data["월"]} 운영 인사이트', level=3))
        for item in ad_ops.get("인사이트", []):
            blocks.append(_bulleted(item))
        blocks.append(_paragraph(""))

        # 다음월 목표
        target = ad_ops["목표"]
        blocks.append(_heading(f'{data["다음월"]} 목표', level=3))
        target_table = [
            _table_row(["항목", "목표"]),
            _table_row(["월 광고비 목표", target["월광고비범위"]]),
            _table_row(["월 매출 목표", target["월매출범위"]]),
            _table_row(["목표 ROAS (전체 매출 기준)", f'{target["목표ROAS"]}%']),
        ]
        blocks.append({
            "object": "block",
            "type": "table",
            "table": {
                "table_width": 2,
                "has_column_header": True,
                "has_row_header": False,
                "children": target_table,
            },
        })
        blocks.append(_paragraph(""))

        # 운영 방향
        blocks.append(_heading("목표 달성을 위한 광고 운영 방향", level=3))
        for item in ad_ops.get("운영방향", []):
            blocks.append(_bulleted(item))
        blocks.append(_paragraph(""))

        # 실행 체크포인트
        blocks.append(_heading("실무 실행 체크포인트", level=3))
        for item in ad_ops.get("체크포인트", []):
            blocks.append(_callout(item, emoji="☑️", color="gray_background"))
        blocks.append(_paragraph(""))

    # ===== 5. 개선사항 =====
    blocks.append(_divider())
    blocks.append(_heading(f'{data["다음월"]} 개선사항', level=2))
    priority_emoji = {"높음": "🔴", "중간": "🟡", "낮음": "🟢"}
    for imp in improvements:
        emoji = priority_emoji.get(imp["우선순위"], "⚪")
        blocks.append(_callout(
            f'[{imp["카테고리"]}] {imp["현황"]}\n→ 개선안: {imp["개선안"]}',
            emoji=emoji,
            color="yellow_background" if imp["우선순위"] == "높음" else "default",
        ))
    blocks.append(_paragraph(""))

    # ===== 6. 운영 플랜 =====
    blocks.append(_heading(f'{data["다음월"]} 운영 플랜', level=2))
    plan_children = [_table_row(["영역", "목표", "세부 계획", "KPI"])]
    for plan in plans:
        plan_children.append(_table_row([
            plan["영역"],
            plan["목표"],
            plan["세부계획"],
            plan["KPI"],
        ]))
    blocks.append({
        "object": "block",
        "type": "table",
        "table": {
            "table_width": 4,
            "has_column_header": True,
            "has_row_header": False,
            "children": plan_children,
        },
    })
    blocks.append(_paragraph(""))

    # ===== 상세 분석 데이터 =====
    blocks.append(_divider())
    blocks.append(_callout("아래는 상세 분석 데이터입니다.", emoji="📋", color="gray_background"))
    blocks.append(_paragraph(""))

    # ===== 7. 광고 성과 분석 (광고 데이터 있을 때만) =====
    if ad_used:
        blocks.append(_heading(f'{data["월"]} 광고 성과 분석', level=2))
        blocks.append(_bulleted(f'총 광고비: {_fmt_money(ad["총광고비"])}  |  총 광고매출(14일 전환 기준): {_fmt_money(ad["총광고매출"])}  |  ROAS(전체매출 기준): {ad["ROAS"]}%'))
        blocks.append(_bulleted(f'광고비 최대일: {ad["광고비최대일"]} ({_fmt_money(ad["광고비최대금액"])})  |  최소일: {ad["광고비최소일"]} ({_fmt_money(ad["광고비최소금액"])})'))
        blocks.append(_bulleted(f'ROAS 최고일: {ad["ROAS최고일"]} ({ad["ROAS최고값"]}%)  |  최저일: {ad["ROAS최저일"]} ({ad["ROAS최저값"]}%)'))
        # 차트: 광고 트렌드
        if chart_urls.get("ad_trend"):
            blocks.append(_image_block_from_upload(chart_urls["ad_trend"]))
        blocks.append(_paragraph(""))

    # ===== 7-2. 광고 키워드 & 지면별 분석 (키워드 데이터 있을 때만) =====
    kw = data.get("키워드")
    if kw:
        blocks.append(_heading("광고 키워드 & 지면별 분석", level=2))
        blocks.append(_bulleted(
            f'총 노출수 {kw["총노출수"]:,}회  |  총 클릭수 {kw["총클릭수"]:,}회  |  평균 CTR {kw["평균CTR"]}%  |  평균 CPC {_fmt_money(kw["평균CPC"])}'
        ))
        blocks.append(_bulleted(f'총 키워드 {kw["총키워드수"]}개 중 매출 발생 {kw["매출발생키워드수"]}개'))

        # 지면별 성과 테이블
        placements = kw.get("지면별", [])
        if placements:
            placement_children = [_table_row(["지면", "노출수", "클릭수", "CTR", "광고비", "전환매출(1일)", "ROAS(1일)"])]
            for p in placements:
                placement_children.append(_table_row([
                    p["광고 노출 지면"],
                    f'{int(p["노출수"]):,}',
                    f'{int(p["클릭수"]):,}',
                    f'{p["CTR"]}%',
                    _fmt_money(int(p["광고비"])),
                    _fmt_money(int(p["매출"])),
                    f'{p["ROAS"]}%',
                ]))
            blocks.append({
                "object": "block",
                "type": "table",
                "table": {
                    "table_width": 7,
                    "has_column_header": True,
                    "has_row_header": False,
                    "children": placement_children,
                },
            })

        # Top 키워드 (매출순)
        top_keywords = kw.get("키워드_매출순", [])[:5]
        if top_keywords:
            blocks.append(_heading("Top 키워드 (매출순)", level=3))
            kw_children = [_table_row(["키워드", "클릭수", "광고비", "전환매출(1일)", "ROAS(1일)"])]
            for k in top_keywords:
                kw_children.append(_table_row([
                    k["키워드"],
                    f'{int(k["클릭수"]):,}',
                    _fmt_money(int(k["광고비"])),
                    _fmt_money(int(k["매출"])),
                    f'{k["ROAS"]}%',
                ]))
            blocks.append({
                "object": "block",
                "type": "table",
                "table": {
                    "table_width": 5,
                    "has_column_header": True,
                    "has_row_header": False,
                    "children": kw_children,
                },
            })

        # 낭비 키워드 경고
        if kw.get("낭비키워드광고비", 0) > 0:
            waste_count = kw.get("낭비키워드수", len(kw.get("키워드_낭비", [])))
            blocks.append(_callout(
                f'주문 0건(1일 전환 기준) 키워드 {waste_count}개에서 광고비 {_fmt_money(kw["낭비키워드광고비"])} 소진했습니다. 입찰가 조정 또는 제외 키워드 등록을 검토하세요.',
                emoji="🚨",
                color="red_background",
            ))
        blocks.append(_paragraph(""))

    # ===== 8. 판매 성과 분석 =====
    blocks.append(_heading(f'{data["월"]} 판매 성과 분석', level=2))
    blocks.append(_bulleted(f'매출 최고일: {sales["매출최고일"]} ({_fmt_money(sales["매출최고금액"])})  |  최저일: {sales["매출최저일"]} ({_fmt_money(sales["매출최저금액"])})'))
    blocks.append(_bulleted(f'전환율 최고일: {sales["전환율최고일"]} ({sales["전환율최고값"]}%)'))
    blocks.append(_bulleted(f'퍼널: 조회→장바구니 {sales["조회당장바구니율"]}%  |  장바구니→주문 {sales["장바구니당주문율"]}%'))
    # 차트: 방문자·전환율 트렌드
    if chart_urls.get("visitors"):
        blocks.append(_image_block_from_upload(chart_urls["visitors"]))
    blocks.append(_paragraph(""))

    # ===== 9. 제품별 분석 =====
    blocks.append(_heading("제품별 판매 분석", level=2))
    product_children = [_table_row(["상품명", "방문자", "주문", "판매량", "매출", "전환율"])]
    for p in products["상품별요약"][:15]:
        name = p["상품명"][:40] + ("..." if len(p["상품명"]) > 40 else "")
        product_children.append(_table_row([
            name,
            str(int(p["방문자"])),
            str(int(p["주문"])),
            str(int(p["판매량"])),
            _fmt_money(int(p["매출"])),
            f'{p["전환율"]}%',
        ]))
    blocks.append({
        "object": "block",
        "type": "table",
        "table": {
            "table_width": 6,
            "has_column_header": True,
            "has_row_header": False,
            "children": product_children,
        },
    })
    # 차트: 제품별 매출 TOP
    if chart_urls.get("product"):
        blocks.append(_image_block_from_upload(chart_urls["product"]))
    blocks.append(_paragraph(""))

    # ===== 10. 주간별 성과 =====
    blocks.append(_heading("주간별 성과", level=2))
    if ad_used and ad["주간별"]:
        weekly_children = [_table_row(["주차", "광고비", "광고매출(14일)", "ROAS(광고매출 14일)", "매출", "주문", "전환율(주문/조회)"])]
        for w_ad, w_sales in zip(ad["주간별"], sales["주간별"]):
            weekly_children.append(_table_row([
                f'{w_ad["주차"]}주차',
                _fmt_money(int(w_ad["광고비"])),
                _fmt_money(int(w_ad["광고매출"])),
                f'{w_ad["ROAS"]}%',
                _fmt_money(int(w_sales["매출"])),
                str(int(w_sales["주문"])),
                f'{w_sales["전환율"]}%',
            ]))
        # 합계/평균 행
        wt_pairs = list(zip(ad["주간별"], sales["주간별"]))
        wt_cost = sum(w["광고비"] for w, _ in wt_pairs)
        wt_adrev = sum(w["광고매출"] for w, _ in wt_pairs)
        wt_roas = (wt_adrev / wt_cost * 100) if wt_cost else 0
        wt_rev = sum(w["매출"] for _, w in wt_pairs)
        wt_order = sum(w["주문"] for _, w in wt_pairs)
        # 주차별 전환율의 단순 평균이 아니라 총주문/총조회로 계산한다 (일수 가중)
        wt_cvr = (sales["총주문"] / sales["총조회"] * 100) if sales.get("총조회") else 0
        weekly_children.append(_table_row([
            "합계",
            _fmt_money(int(wt_cost)),
            _fmt_money(int(wt_adrev)),
            f'{wt_roas:.0f}%',
            _fmt_money(int(wt_rev)),
            str(int(wt_order)),
            f'{wt_cvr:.2f}%',
        ]))
        weekly_width = 7
    else:
        weekly_children = [_table_row(["주차", "매출", "주문", "전환율"])]
        for w_sales in sales["주간별"]:
            weekly_children.append(_table_row([
                f'{w_sales["주차"]}주차',
                _fmt_money(int(w_sales["매출"])),
                str(int(w_sales["주문"])),
                f'{w_sales["전환율"]}%',
            ]))
        if sales["주간별"]:
            ws_rev = sum(w["매출"] for w in sales["주간별"])
            ws_order = sum(w["주문"] for w in sales["주간별"])
            ws_cvr = (sales["총주문"] / sales["총조회"] * 100 if sales.get("총조회") else 0)
            weekly_children.append(_table_row([
                "합계",
                _fmt_money(int(ws_rev)),
                str(int(ws_order)),
                f'{ws_cvr:.2f}%',
            ]))
        weekly_width = 4
    blocks.append({
        "object": "block",
        "type": "table",
        "table": {
            "table_width": weekly_width,
            "has_column_header": True,
            "has_row_header": False,
            "children": weekly_children,
        },
    })
    blocks.append(_paragraph(""))

    # ===== 11. 교차 분석 (광고 데이터 있을 때만) =====
    if ad_used:
        blocks.append(_heading("광고-판매 교차 분석", level=2))
        blocks.append(_bulleted(f'광고비↔방문자 상관계수: {cross["광고비_방문자_상관"]}'))
        blocks.append(_bulleted(f'광고비↔주문 상관계수: {cross["광고비_주문_상관"]}'))
        blocks.append(_bulleted(f'광고비↔매출 상관계수: {cross["광고비_매출_상관"]}'))
        blocks.append(_paragraph(""))

    return blocks


def _find_or_create_brand_page(notion, root_page_id: str, brand_name: str) -> str:
    """브랜드 페이지를 찾거나 없으면 생성. 반환: 브랜드 페이지 ID"""
    norm_brand = unicodedata.normalize('NFC', brand_name).strip()

    # 루트 페이지의 children에서 브랜드 페이지 검색
    try:
        children = notion.blocks.children.list(block_id=root_page_id, page_size=100)
        for block in children.get("results", []):
            if block["type"] == "child_page":
                child_title = unicodedata.normalize('NFC', block["child_page"]["title"]).strip()
                if child_title == norm_brand:
                    return block["id"]
    except Exception as e:
        print(f"  [경고] 브랜드 페이지 검색 중 오류: {e}")

    # 없으면 새로 생성
    new_brand_page = notion.pages.create(
        parent={"page_id": root_page_id},
        properties={
            "title": [{"text": {"content": brand_name}}],
        },
    )
    print(f"  브랜드 페이지 생성: {brand_name}")
    return new_brand_page["id"]


def export_to_notion(data: dict, config: dict, title: str = None, brand_name: str = None, html_path: str = None) -> str:
    """분석 데이터를 Notion 페이지에 업로드

    brand_name이 주어지면 루트 > 브랜드 페이지 > 리포트 구조로 생성.
    없으면 루트 바로 아래에 생성 (기존 동작).
    """
    api_key = config["notion"]["api_key"]
    root_page_id = config["notion"]["database_id"]

    if not api_key or not root_page_id:
        raise ValueError("Notion API Key 또는 페이지 ID가 설정되지 않았습니다. .env 의 NOTION_API_KEY / NOTION_PAGE_ID 를 확인하세요.")

    # 차트 이미지 업로드용 API key 설정
    global _notion_api_key
    _notion_api_key = api_key

    notion = Client(auth=api_key)

    # 브랜드 페이지 결정
    if brand_name:
        parent_page_id = _find_or_create_brand_page(notion, root_page_id, brand_name)
    else:
        parent_page_id = root_page_id

    # 새 하위 페이지 제목
    page_title = title or f'쿠팡 종합 리포트 - {data["월"]}'

    # [중복 방지] 동일한 제목의 기존 페이지가 있는지 검색
    parent_page_id_normalized = parent_page_id.replace('-', '')
    existing_page_id = None
    try:
        results = notion.search(query=page_title, filter={"property": "object", "value": "page"}).get("results", [])
        for res in results:
            if res.get("archived", False):
                continue

            res_title = ""
            props = res.get("properties", {})
            for key in ("title", "Name", "이름"):
                if key in props:
                    title_list = props[key].get("title", [])
                    if title_list:
                        res_title = title_list[0].get("plain_text", "")
                        break

            norm_res_title = unicodedata.normalize('NFC', res_title).strip()
            norm_page_title = unicodedata.normalize('NFC', page_title).strip()

            if norm_res_title == norm_page_title:
                parent = res.get("parent", {})
                api_parent_id = parent.get("page_id", parent.get("database_id", "")).replace('-', '')
                if api_parent_id == parent_page_id_normalized:
                    existing_page_id = res["id"]
                    break
    except Exception as e:
        print(f"  [경고] 기존 페이지 검색 중 오류: {e}")

    if existing_page_id:
        try:
            notion.pages.update(page_id=existing_page_id, archived=True)
            print(f"  [안내] 기존 동일 제목의 리포트를 아카이브하고 최신 데이터로 대체합니다.")
        except Exception as e:
            print(f"  [경고] 기존 페이지 아카이브 실패: {e}")

    blocks = build_notion_blocks(data)

    new_page = notion.pages.create(
        parent={"page_id": parent_page_id},
        properties={
            "title": [{"text": {"content": page_title}}],
        },
    )

    page_id = new_page["id"]

    # 블록을 100개씩 나눠서 추가
    for i in range(0, len(blocks), 100):
        chunk = blocks[i : i + 100]
        notion.blocks.children.append(block_id=page_id, children=chunk)

    page_url = new_page.get("url", f"https://notion.so/{page_id.replace('-', '')}")

    # HTML 파일 다운로드 블록 추가 (상단 callout 뒤)
    if html_path and Path(html_path).exists():
        try:
            # Notion은 파일명의 비ASCII 문자를 '_'로 치환하므로 미리 ASCII 이름을 만든다
            html_filename = _ascii_filename(Path(html_path).name)
            html_bytes = Path(html_path).read_bytes()
            upload_id = _upload_file_to_notion(html_bytes, html_filename, "text/html")

            # Notion 업로드 엔드포인트(Cloudflare)가 HTML 원문을 403으로 차단하는 경우가 있어
            # 실패 시 ZIP으로 압축해 재시도한다.
            if not upload_id:
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr(html_filename, html_bytes)
                html_filename = html_filename.rsplit(".", 1)[0] + ".zip"
                upload_id = _upload_file_to_notion(
                    zip_buf.getvalue(), html_filename, "application/zip"
                )
                if upload_id:
                    print("  [알림] HTML 직접 업로드가 차단되어 ZIP으로 첨부했습니다.")

            if not upload_id:
                print("  [경고] HTML 다운로드 파일 업로드 실패 (Notion 업로드 거부)")

            if upload_id:
                # 첫 callout 찾기
                children_resp = notion.blocks.children.list(block_id=page_id, page_size=5)
                first_callout_id = None
                for b in children_resp.get("results", []):
                    if b["type"] == "callout":
                        first_callout_id = b["id"]
                        break

                download_blocks = [
                    {
                        "object": "block",
                        "type": "callout",
                        "callout": {
                            "rich_text": [{"type": "text", "text": {"content": (
                                "HTML 리포트 다운로드 (아래 파일 클릭 → 압축 해제 후 브라우저로 열기)"
                                if html_filename.endswith(".zip")
                                else "HTML 리포트 다운로드 (아래 파일 클릭)"
                            )}}],
                            "icon": {"type": "emoji", "emoji": "📥"},
                            "color": "purple_background",
                        },
                    },
                    {
                        "object": "block",
                        "type": "file",
                        "file": {
                            "type": "file_upload",
                            "file_upload": {"id": upload_id},
                        },
                    },
                    _paragraph(""),
                ]

                if first_callout_id:
                    notion.blocks.children.append(block_id=page_id, children=download_blocks, after=first_callout_id)
                else:
                    notion.blocks.children.append(block_id=page_id, children=download_blocks)
                print(f"  HTML 다운로드 링크 추가: {html_filename}")
        except Exception as e:
            print(f"  [경고] HTML 다운로드 링크 추가 실패: {e}")

    return page_url
