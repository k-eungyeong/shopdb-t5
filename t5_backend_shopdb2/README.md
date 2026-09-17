# t5_backend_shopdb2 실행 가이드

## 최초 설정 (한 번만)
1. 본인 컴퓨터의 shopdb2 DB에 t5_carts / t5_wishlist_items / t5_product_reviews 테이블과 트리거 3개가 이미 있는지 확인
2. 가상환경 생성: `python -m venv venv`
3. 가상환경 활성화: `venv\Scripts\activate`
4. 패키지 설치: `pip install -r requirements.txt`
5. `.env.example`을 참고해서 `.env` 에 본인 DB 비밀번호 입력

## 실행
1. uvicorn main:app --reload
브라우저에서 `http://127.0.0.1:8000/db-test` 접속해서 정상 응답 나오면 성공.
→ 정상 응답 예시: {"t5_carts_row_count":5}

## 작업 규칙
- 본인 담당 기능은 `routers/본인기능.py` 파일로 새로 만들어서 작업
- `main.py`는 라우터 등록(import + include_router) 2줄만 추가