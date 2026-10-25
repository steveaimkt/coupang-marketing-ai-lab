# 쿠팡 광고 분석 설정

상대 경로는 작업 폴더 기준입니다. 말로 바꾸면 클로드 코드가 이 값을 고칩니다.

```yaml
input_mode: user_provided_file
input_file: 데이터/*/*pa_daily_keyword*.xlsx
file_type: xlsx
csv_encoding: utf-8-sig
csv_delimiter: ','
sheet_name: null
output_directory: 결과물
date_start: null
date_end: null
attribution_days: 14
target_roas_pct: null
star_roas_pct: 300
potential_roas_pct: 100
waste_cost_krw: 10000
minimum_orders_for_star: 1
dashboard_title: 노을뷰티 쿠팡 광고 분석
primary_color: '#2563EB'
visual_style: 밝은 회색 배경, 흰 카드, 파랑과 인디고 포인트, 넉넉한 여백
implementation_mode: static
menu_items:
- id: overview
  label: 대시보드
- id: daily
  label: 일별
- id: placement
  label: 지면
- id: keyword
  label: 키워드
- id: insights
  label: 인사이트
- id: actions
  label: 실행 계획
navigation_desktop: top
navigation_mobile: horizontal
kpi_order:
- revenue
- cost
- roas
- orders
- ctr
- cpc
- cvr
- cpa
overview_layout: split
```
