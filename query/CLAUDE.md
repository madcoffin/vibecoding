# 진도율 쿼리문 생성기

## 개요
CSV 파일을 업로드하면 각 사용자(이메일)별 상품(상품코드) 수강률을 한 번에 조회할 수 있는 SQL 쿼리를 자동 생성하는 데스크탑 GUI 프로그램.

## 실행 방법
```bash
python3 /Users/coffin/vibecoding/query/query_generator.py
```

## 의존성

| 패키지 | 용도 | 설치 |
|--------|------|------|
| tkinter | GUI 프레임워크 (Python 기본 포함) | `brew install python-tk@3.14` |
| Pillow | 작성자 프로필 이미지 원형 처리 | `brew install pillow` |

## 파일 구조
```
query/
├── query_generator.py   # 메인 프로그램
├── author.jpg           # 작성자 프로필 사진 (author.jpeg / author.png 도 인식)
└── CLAUDE.md
```

## CSV 입력 형식

- **인코딩**: UTF-8 (BOM 포함 가능)
- **필수 헤더**: `이메일`, `상품코드` — 열 위치는 자유, 헤더명으로 자동 탐색
- 동일한 (이메일, 상품코드) 조합은 자동으로 중복 제거됨
- 빈 이메일 또는 빈 상품코드 행은 무시됨

## 생성 쿼리 구조

```sql
WITH combinations AS (
    -- (idx, email, product_code) — idx는 CSV 원본 행 순서
    SELECT idx, email, product_code FROM (VALUES ...) AS t(...)
),
products_mapped AS (
    -- old_product_id → 내부 product_id 변환
    SELECT p.id AS product_id, p.old_product_id
    FROM products p
    WHERE p.old_product_id IN (...)
)
SELECT m.email, pm.old_product_id AS product_code, mc.progress
FROM members m
JOIN combinations c     ON m.email = c.email
JOIN products_mapped pm ON pm.old_product_id = c.product_code
JOIN my_contents mc     ON mc.member_id = m.id AND mc.product_id = pm.product_id
ORDER BY c.idx;  -- CSV 원본 순서 유지
```

### 참조 테이블
| 테이블 | 역할 |
|--------|------|
| `products` | `old_product_id`(상품코드) → 내부 `id` 매핑 |
| `members` | 이메일로 회원 조회 |
| `my_contents` | 회원별 상품 수강 진도율(`progress`) |

## UI 구성 요소

| 섹션 | 설명 |
|------|------|
| 타이틀 + 작성자 | 프로그램명, 설명, 우상단 원형 프로필 사진 + madcoffin |
| FILE | CSV 파일 선택 (`열기` 버튼) |
| 통계 | 조합 수 / 고유 이메일 / 고유 상품코드 / 데이터 행 |
| PREVIEW | 파싱된 데이터 최대 10행 미리보기 |
| SQL | 생성된 쿼리 표시 영역, `복사` / `저장` 버튼 |

## 주요 함수 및 클래스

### `parse_csv(filepath) → list[dict]`
- 헤더에서 `이메일`, `상품코드` 열 위치를 동적으로 탐색
- 반환값: `[{'email': str, 'code': str}, ...]` (중복 제거, 순서 유지)

### `build_query(pairs) → str`
- `pairs` 리스트를 받아 완성된 SQL 문자열 반환
- `idx`를 VALUES에 포함시켜 `ORDER BY c.idx`로 CSV 원본 순서 보장
- SQL 인젝션 방지를 위해 `sql_str()`로 단일 인용부호 이스케이프

### `class FlatBtn(tk.Label)`
- macOS에서 `tk.Button`의 색상이 무시되는 문제를 Label 기반으로 우회
- `dark=True`: 검정 배경 + 흰 글씨 / `dark=False`: 흰 배경 + 검정 글씨
- `flash(text, ms)`: 일시적으로 텍스트·색상 변경 후 원복 (복사됨 ✓ 피드백)

### `load_author_photo(size) → PhotoImage | None`
- `author.jpg / author.jpeg / author.png` 순으로 탐색
- PIL로 원형 마스크 적용 후 `ImageTk.PhotoImage` 반환
- 파일 없거나 PIL 오류 시 `None` 반환 → 이니셜 원(Canvas)으로 자동 대체

## 디자인 원칙
- 흰 배경(`#ffffff`), 검정 텍스트(`#111111`) 고대비 미니멀 스타일
- 1px 라인(`#e0e0e0`)으로 섹션 구분, 색상 카드 없음
- The Minimalists (theminimalists.com) 톤앤매너 참고

<!-- AUTO-GENERATED START -->
_Last auto-updated: 2026-04-17 16:41:47_

## `query_generator.py` — Code Structure

### Dependencies
- `tkinter`
- `tkinter (filedialog, messagebox, scrolledtext, ttk)`
- `csv`
- `os`

### Constants
- `BG` = `'#ffffff'`
- `TEXT` = `'#111111'`
- `MUTED` = `'#888888'`
- `BORDER` = `'#e0e0e0'`
- `SQL_BG` = `'#f4f4f4'`
- `F_BODY` = `('Helvetica Neue', 11)`
- `F_SM` = `('Helvetica Neue', 9)`
- `F_XS` = `('Helvetica Neue', 8)`
- `F_BOLD` = `('Helvetica Neue', 10, 'bold')`
- `F_TITLE` = `('Helvetica Neue', 20, 'bold')`
- `F_SUB` = `('Helvetica Neue', 10)`
- `F_NUM` = `('Helvetica Neue', 24, 'bold')`
- `F_MON` = `('Menlo', 10)`
- `PAD` = `40`

### Classes
- **`FlatBtn`**(tk.Label)
  - `flash()`
- **`App`**(tk.Tk)
  - `_style_tree()`
  - `_build_ui()`
  - `_open_file()`
  - `_copy_query()`
  - `_save_file()`

### Functions
- `parse_csv(filepath)`
- `sql_str(s)`
- `build_query(pairs)`
- `load_author_photo(size)`
- `divider(parent)`

<!-- AUTO-GENERATED END -->
