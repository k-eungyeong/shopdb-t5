# 구매완료 후 리뷰 작성 기능

## 변경된 동작

기존: 배송완료(DELIVERED) → 바로 리뷰 작성 가능

변경: 배송완료(DELIVERED) → [구매완료] 버튼 → 구매완료(COMPLETED) → [리뷰 작성] 버튼

## 변경 파일

- t5_backend_shopdb2/routers/orders.py
  - POST /orders/{order_id}/complete 추가
  - 배송완료 주문만 구매완료 처리
- t5_backend_shopdb2/routers/reviews.py
  - 리뷰 작성 가능 상태를 COMPLETED로 제한
- t5_frontend_shopdb2/src/api/shopApi.js
  - completeOrder() 추가
- t5_frontend_shopdb2/src/pages/MyOrders.jsx
  - 배송완료 주문에 구매완료 버튼 표시
  - 구매완료 후 상품별 리뷰 작성 버튼 표시
- t5_frontend_shopdb2/src/pages/OrderDetail.jsx
  - 주문상세에서도 구매완료 및 리뷰작성 가능
- t5_frontend_shopdb2/src/pages/Orders.css
  - 구매완료/리뷰 버튼 스타일 추가

## DB 변경 여부

SQL 테이블 생성/수정 없음. 기존 orders.order_status와 order_items.item_status를 사용합니다.
