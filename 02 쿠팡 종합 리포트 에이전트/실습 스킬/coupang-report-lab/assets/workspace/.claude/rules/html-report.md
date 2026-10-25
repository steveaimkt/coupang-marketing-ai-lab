---
paths:
  - "report_template.py"
---

# HTML 리포트 규칙

## 섹션 구조 (순서 중요)

각 섹션은 `<div class="section" id="...">` 로 감싼다. 실제 생성 순서:

**전략 존 (상단)**, 의사결정용, 사람이 먼저 읽는 영역

| # | id | 제목 |
|---|----|------|
| 1 | `summary` | 종합 요약 (Executive Summary), 당월 예상 실적·목표 달성 분석 포함 |
| 2 | `insights` | {월} 핵심 인사이트 |
| 3 | `checks` | 이번 달 필수 확인사항 |
| 4 | `ad-ops` | 광고 운영 분석 & {다음월} 전략, 다음월 목표 테이블 위치 |
| 5 | `improve` | {다음월} 개선사항 |
| 6 | `plan` | {다음월} 운영 플랜 |

**상세 분석 존 (하단)**, 근거 데이터

| # | id | 제목 |
|---|----|------|
| 7 | `ad` | {월} 광고 성과 분석 |
| 8 | `keyword` | 광고 키워드 & 지면별 분석 |
| 9 | `sales` | {월} 판매 성과 분석 |
| 10 | `products` | 제품별 판매 분석 |
| 11 | `product-trend` | 제품 트렌드 분석 |
| 12 | `weekly` | 주간별 / 요일별 성과 분석 |
| 13 | `cross` | 광고-판매 교차 분석 |
| 14 | `daily` | 일자별 상세 분석 데이터 |

> 워크플로우 Step 3의 **수동 섹션(마케팅 플랜 등)은 `improve`(5번) 앞에 삽입**한다.
> 광고 데이터가 없으면 `ad-ops`·`ad`·`keyword`·`cross` 는 생성되지 않는다.

## PDF 잘림 방지 (print CSS 필수)

- 모든 콘텐츠 영역 `overflow: visible !important`
- `.daily-table-wrap { max-height: none !important }`
- `.report-header::before { display: none !important }`
- `-webkit-print-color-adjust: exact !important`
- `break-inside: avoid`, kpi-card, insight-card, check-item, chart-container, table-wrapper

## Python 3.9 호환

- f-string 안에서 같은 따옴표 재사용 금지 (3.12 기능). 변수로 미리 빌드
- 큰 HTML 블록은 조건부 변수로 분리 후 삽입
