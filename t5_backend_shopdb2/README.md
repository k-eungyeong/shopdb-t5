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
### HeidiSQL에서 최초 1회 실행

첨부한 `꾸원쓰.sql`은 `orders.buyer_user_id`와
`t5_product_reviews.user_id`가 NOT NULL이라 비회원 정보를 저장할 수 없습니다.
HeidiSQL에서 `shopdb2` DB를 선택하고
`heidisql_guest_review_migration.sql`을 전체 실행한 뒤 백엔드를 실행하세요.

서버 실행 후 `http://127.0.0.1:8000/docs`에서 아래 API를 테스트할 수 있습니다.

- `POST /api/reviews`: 리뷰 작성
- `GET /api/products/{product_id}/reviews`: 상품별 리뷰 목록
- `GET /api/products/{product_id}/reviews/summary`: 상품 평점 통계
- `GET /api/users/me/reviews`: 로그인 회원이 작성한 리뷰 목록
- `GET /api/reviews/{review_id}`: 리뷰 상세 조회
- `PATCH /api/reviews/{review_id}`: 작성자 리뷰 수정
- `DELETE /api/reviews/{review_id}`: 작성자 리뷰 삭제

리뷰 API는 회원·비회원 선택적 JWT 방식으로 동작합니다.

- 회원: JWT가 있으면 토큰의 user_id와 주문의 구매자 번호를 비교
- 비회원: JWT 없이 Body의 `order_no`와 `receiver_phone`으로 주문 인증
- 비회원 리뷰의 `user_id`는 NULL로 저장

회원·비회원 모두 `order_item_id`가 실제 주문상품인지, 요청한 `product_id`와
일치하는지, 주문과 주문상품이 배송 완료 상태인지 확인한 후 저장합니다.
비회원은 주문의 구매자 번호가 NULL이고, 기존 `orders.order_no`와
`orders.receiver_phone`이 모두 일치해야 작성·수정·삭제할 수 있습니다.
비회원 저장을 위해 위 마이그레이션 SQL은 최초 1회 반드시 실행해야 합니다.

회원 리뷰 작성 예시:

```json
{
  "order_no": null,
  "receiver_phone": null,
  "order_item_id": 1,
  "product_id": 1,
  "rating": 5,
  "review_txt": "상품이 좋아요."
}
```

비회원 리뷰 작성 예시:

```json
{
  "order_no": "ORD-2025-0001",
  "receiver_phone": "010-5000-5000",
  "order_item_id": 10,
  "product_id": 2,
  "rating": 4,
  "review_txt": "비회원 구매 후기입니다."
}
```
