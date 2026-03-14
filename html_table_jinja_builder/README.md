# html_table_jinja_builder

PowerPoint/Excel에서 복붙한 HTML 표를 입력받아 다음 산출물을 만드는 1단계 도구입니다.

- `template.html.j2`: 원본 표 구조/스타일을 최대 유지한 Jinja2 템플릿
- `data_contract.json`: 셀 메타데이터 + placeholder 매핑 계약
- `mock_data.json`: 독립 렌더링 가능한 샘플 데이터
- `rendered_preview.html`: 템플릿 렌더링 결과

## 설치

Python 3.11 기준

```bash
pip install beautifulsoup4 lxml jinja2
```

## 실행

```bash
python build_template.py --input input/sample_table.html --output-dir output
python render_demo.py --template output/template.html.j2 --data output/mock_data.json --out output/rendered_preview.html
```

## 후보 셀 판별 규칙(1단계)

아래 패턴을 우선 치환 후보(`is_candidate=true`)로 판별합니다.

- 숫자/천단위 숫자/소수점/음수
- `%` 값
- 기간성 값(`26.1Q`, `2Q`, `25.W32` 등)
- 본문 영역에서 반복 데이터처럼 보이는 짧은 값

다음 항목은 기본 유지합니다.

- `th` 헤더 셀
- 대표 헤더 키워드(`DRAM`, `FLASH`, `합계` 등)

> 후보 여부는 `data_contract.json`에 함께 기록되므로 사람이 사후 수정 가능합니다.

## 한계사항

- 후보 판별은 규칙 기반이며 문맥을 완전히 이해하지는 못합니다.
- 복합 텍스트가 많은 셀에서는 첫 번째 주요 텍스트 노드를 기준으로 치환합니다.
- 다중 테이블 문서는 지원하지만, 현재는 단순 순서 기반으로 처리합니다.

## 다음 단계(확장 포인트)

- LLM 연동 후보 정제(비즈니스 문맥 기반)
- SQL shape 자동 추천기
- Oracle 실행기/적재 파이프라인 연결

