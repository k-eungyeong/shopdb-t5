# 구매후기 작성 버튼 2개 화면 적용 안내

## 핵심 규칙

SQL 테이블 구조는 수정하지 않았습니다.

리뷰는 다음 조건을 모두 만족할 때만 작성할 수 있습니다.

1. 로그인한 회원 본인의 주문상품이어야 합니다.
2. 해당 상품을 실제 주문한 내역이 있어야 합니다.
3. 주문 상태가 `COMPLETED`(구매완료)여야 합니다.
4. 같은 `order_item_id`에는 리뷰를 한 번만 작성할 수 있습니다.

## 화면 1: 주문 내역

- 모든 미작성 주문상품에 `리뷰 작성` 버튼이 보입니다.
- 구매완료 전에는 버튼이 비활성화됩니다.
- 주문 상태가 `COMPLETED`가 되면 버튼이 활성화됩니다.
- 리뷰 등록 후에는 `리뷰완료`로 표시됩니다.

## 화면 2: 상품 상세 > 구매후기

- `구매후기` 영역에 `내 구매후기` 박스와 `리뷰 작성` 버튼을 추가했습니다.
- FastAPI의 `GET /reviews/eligibility/{product_id}`가 현재 로그인 회원의 실제 주문내역을 확인합니다.
- 리뷰를 쓸 수 있는 구매완료 주문상품이 있으면 버튼이 활성화됩니다.
- 구매했지만 아직 구매완료 전이면 버튼은 비활성화되고 안내 문구가 표시됩니다.
- 구매하지 않았다면 실제 구매 회원만 작성할 수 있다는 안내가 표시됩니다.
- 리뷰 등록 직후 상품 상세의 리뷰 목록과 평균 평점이 다시 로드됩니다.

## 추가된 API

`GET /reviews/eligibility/{product_id}`

응답 예시:

```json
{
  "can_review": true,
  "message": "구매완료한 상품입니다. 리뷰를 작성할 수 있습니다.",
  "order_item": {
    "order_item_id": 20,
    "order_id": 18,
    "product_id": 4,
    "order_no": "ORD-...",
    "order_status": "COMPLETED"
  }
}
```

실제 리뷰 등록은 기존 `POST /reviews`를 그대로 사용합니다. 백엔드는 다시 한 번 주문 소유자, 상품 일치 여부, `COMPLETED` 상태, 중복 리뷰 여부를 검사합니다.

## 변경 파일

- `t5_backend_shopdb2/routers/reviews.py`
- `t5_frontend_shopdb2/src/api/shopApi.js`
- `t5_frontend_shopdb2/src/pages/MyOrders.jsx`
- `t5_frontend_shopdb2/src/pages/Orders.css`
- `t5_frontend_shopdb2/src/pages/ProductDetail.jsx`
- `t5_frontend_shopdb2/src/pages/ProductDetail.css`

## 테스트 순서

1. 로그인합니다.
2. 주문내역에서 주문상태가 `DELIVERED`인 주문은 `구매완료`를 누릅니다.
3. 상태가 `COMPLETED`로 바뀌면 주문내역의 `리뷰 작성` 버튼이 활성화되는지 확인합니다.
4. 같은 상품의 상세 페이지로 이동합니다.
5. `구매후기` 영역에서도 `리뷰 작성` 버튼이 활성화되는지 확인합니다.
6. 한 화면에서 리뷰를 작성합니다.
7. 다른 화면으로 이동했을 때 이미 리뷰를 작성한 주문상품에는 다시 작성할 수 없는지 확인합니다.

> 개발 환경에서는 DB 데이터의 `orders.order_status`가 `PAID`이면 아직 구매완료가 아니므로 리뷰 버튼이 비활성화됩니다. `DELIVERED` 상태에서 사용자가 구매완료를 누른 뒤 `COMPLETED`가 되어야 활성화됩니다.
