---
paths:
  - "notion_exporter.py"
---

# Notion API 규칙

- Notion API Version: 2022-06-28
- File Upload API 3단계: POST /v1/file_uploads → POST .../send (multipart) → POST .../complete → PATCH children에 file 블록 추가
- file 블록 형식: `"type":"file","file":{"type":"file_upload","file_upload":{"id":"..."}}`
- callout children 수정: GET children → DELETE 기존 bullets → PATCH children (새 paragraph+bullets)
- 페이지 구조: 광고 리포트 에이전트 DB > {브랜드} 광고 리포트 > 날짜별 리포트
