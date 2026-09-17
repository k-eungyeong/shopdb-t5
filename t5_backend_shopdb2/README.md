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

## 리뷰 API
서버 실행 후 `http://127.0.0.1:8000/docs`에서 아래 API를 테스트할 수 있습니다.

- `POST /api/reviews`: 리뷰 작성
- `GET /api/products/{product_id}/reviews`: 상품별 리뷰 목록
- `GET /api/products/{product_id}/reviews/summary`: 상품 평점 통계
- `GET /api/users/me/reviews`: 로그인 사용자 작성 리뷰 목록
- `GET /api/reviews/{review_id}`: 리뷰 상세 조회
- `PATCH /api/reviews/{review_id}`: 작성자 리뷰 수정
- `DELETE /api/reviews/{review_id}`: 로그인 작성자 리뷰 삭제

리뷰 작성·내 리뷰 조회·수정·삭제 API는 `Authorization: Bearer JWT토큰`이
필요합니다. `user_id`는 요청으로 받지 않고 검증된 JWT의 `sub` 값에서 가져옵니다.

로그인 API를 추가하기 전 테스트용 토큰은 프로젝트 폴더에서 아래처럼 만들 수 있습니다.

```powershell
uv run python -c "from auth.security import create_access_token; print(create_access_token(4, 'buyer'))"
```

출력된 토큰을 Swagger의 `Authorize` 버튼에 입력한 뒤 보호된 API를 테스트합니다.
실제 로그인 기능을 만들 때는 비밀번호 확인에 성공한 후
`create_access_token(user_id, role)`을 호출하여 같은 형식의 토큰을 반환하면 됩니다.
