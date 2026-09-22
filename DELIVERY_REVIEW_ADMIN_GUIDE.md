# 배송조회 + 관리자 배송상태 + 배송완료 리뷰 기능

## 핵심 결론

새 DB 테이블을 추가하지 않습니다.
기존 `orders.order_status` 값을 이용해 다음 흐름을 구현합니다.

`PAID(결제완료) → PREPARING(상품준비중) → SHIPPING(배송중) → DELIVERED(배송완료) → COMPLETED(구매완료)`

관리자가 `DELIVERED`로 변경하는 순간 구매자는 리뷰를 작성할 수 있습니다.
고객의 `구매완료(COMPLETED)` 버튼은 수령 확정 용도로 그대로 유지되지만, 리뷰 작성의 필수 조건은 아닙니다.

## 새 테이블 없이 가능한 배송조회 범위

가능:
- 결제완료
- 상품준비중
- 배송중
- 배송완료
- 현재 상태 표시
- 관리자의 배송상태 변경
- 배송완료 후 리뷰 작성

불가능/제한:
- 택배사 송장번호 저장
- 집하/허브/지역터미널 같은 상세 이동 이력
- 단계별 정확한 시각(집하 14:20, 허브 도착 18:10 등) 저장

이런 상세 택배 추적까지 필요하면 나중에 배송 테이블이나 택배사 API 연동이 필요합니다.
현재 학습 프로젝트에서는 기존 `orders.order_status`만 사용하는 방식이 가장 단순합니다.

## 변경 파일

### Backend
- `t5_backend_shopdb2/main.py`
- `t5_backend_shopdb2/routers/admin_orders.py` (신규)
- `t5_backend_shopdb2/routers/reviews.py`

### Frontend
- `t5_frontend_shopdb2/src/api/shopApi.js`
- `t5_frontend_shopdb2/src/App.jsx`
- `t5_frontend_shopdb2/src/components/Header.jsx`
- `t5_frontend_shopdb2/src/pages/AdminOrders.jsx` (신규)
- `t5_frontend_shopdb2/src/pages/AdminOrders.css` (신규)
- `t5_frontend_shopdb2/src/pages/MyOrders.jsx`
- `t5_frontend_shopdb2/src/pages/OrderDetail.jsx`
- `t5_frontend_shopdb2/src/pages/Orders.css`
- `t5_frontend_shopdb2/src/pages/ProductDetail.jsx`

## 관리자 사용 방법

ADMIN 권한 계정으로 로그인하면 헤더에 `배송관리` 메뉴가 나타납니다.

주소: `/admin/orders`

관리자는 결제가 끝난 주문에서 다음 상태를 선택할 수 있습니다.

- 상품준비중
- 배송중
- 배송완료

상태를 이전 단계로 되돌리는 것은 백엔드에서도 막습니다.

API:
- `GET /admin/orders`
- `PATCH /admin/orders/{order_id}/shipping-status`

관리자 여부는 프론트 화면만 믿지 않고 FastAPI가 `user_roles + roles`로 다시 확인합니다.

## 리뷰 작성 규칙

리뷰는 다음 조건을 모두 만족해야 합니다.

1. 로그인한 본인의 주문상품이어야 함
2. 주문한 product_id와 리뷰 product_id가 같아야 함
3. 주문 상태가 `DELIVERED` 또는 `COMPLETED`
4. 같은 order_item_id에 기존 리뷰가 없어야 함

따라서 관리자가 주문을 배송완료로 변경하면 주문내역과 상품 상세의 `리뷰 작성` 버튼이 활성화됩니다.

## 구매자 배송조회

주문내역의 `배송조회` 버튼을 누르면 현재 상태를 다음 단계로 보여줍니다.

결제완료 → 상품준비중 → 배송중 → 배송완료

주문 상세 페이지에서는 배송 진행 상황을 항상 확인할 수 있습니다.

## 중요한 테스트 순서

1. 구매자 계정으로 상품 주문 및 개발용 결제를 완료합니다.
2. 주문 상태가 `PAID`인지 확인합니다.
3. ADMIN 계정으로 로그인합니다.
4. `배송관리`에서 주문을 `PREPARING`으로 변경합니다.
5. 다시 `SHIPPING`으로 변경합니다.
6. `DELIVERED`로 변경합니다.
7. 구매자 계정으로 로그인합니다.
8. 주문내역에서 배송조회가 `배송완료`까지 표시되는지 확인합니다.
9. 주문내역의 `리뷰 작성` 버튼이 활성화되는지 확인합니다.
10. 상품 상세의 구매후기 영역에서도 `리뷰 작성` 버튼이 활성화되는지 확인합니다.

## 관리자 계정 참고

기존 SQL 샘플의 `admin01` 비밀번호 값이 실제 PBKDF2 해시가 아닌 샘플 값이라면 현재 로그인 코드에서 로그인되지 않을 수 있습니다.
이 경우 기존 비밀번호 재설정 기능을 이용해 admin01 계정의 비밀번호를 새로 설정하면 됩니다.
테이블 구조를 변경할 필요는 없습니다.
