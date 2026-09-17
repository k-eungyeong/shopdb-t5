# t5_backend_shopdb2 실행 가이드

## 최초 설정 (한 번만)
1. 본인 컴퓨터의 shopdb2 DB에 t5_carts / t5_wishlist_items / t5_product_reviews 테이블과 트리거 3개가 이미 있는지 확인
2. uv 설치 확인: `uv --version`
3. 가상환경 생성 + 패키지 설치(한 번에 처리): `uv sync`
4. `.env.example`을 복사해서 `.env` 생성 후 본인 DB 비밀번호 입력

## 실행
1. 'uv run uvicorn main:app --reload'
브라우저에서 `http://127.0.0.1:8000/db-test` 접속해서 정상 응답 나오면 성공.
-> 정상응답 {"t5_carts_row_count":5}

(참고: `uv run`은 가상환경을 따로 activate 하지 않아도 자동으로 `.venv`를 사용해서 실행해줍니다. `.venv\Scripts\activate`로 직접 활성화한 뒤 `uvicorn main:app --reload`로 실행해도 동일하게 동작합니다.)

## 새 패키지가 필요할 때
- uv add 패키지명
`pyproject.toml`과 `uv.lock`에 자동으로 반영되니, 커밋해서 팀원과 공유하면 됩니다.

## 작업 규칙
- 본인 담당 기능은 `routers/본인기능.py` 파일로 새로 만들어서 작업
- `main.py`는 라우터 등록(import + include_router) 2줄만 추가
