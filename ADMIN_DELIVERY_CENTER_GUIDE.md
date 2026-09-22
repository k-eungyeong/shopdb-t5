# 관리자 배송관리 화면 보강

## 이번 수정의 핵심

기존 SQL 테이블은 추가/변경하지 않았습니다.
배송 상태는 기존 `orders.order_status`와 `order_items.item_status`를 사용합니다.

관리자 로그인 시 우측 상단 **찜 메뉴의 왼쪽에 `🚚 배송관리`** 메뉴가 나타납니다.
관리자 배송관리 주소는 `/admin/orders` 입니다.

## 기존에 메뉴가 안 보이던 원인

로그인 직후 프론트에서 로그인 API의 간단한 `user` 객체를 그대로 사용했는데,
그 객체에는 `roles`가 포함되어 있지 않았습니다.
그래서 ADMIN 계정이어도 새로고침 전까지 `user.roles`를 확인할 수 없어 배송관리 메뉴가 숨겨질 수 있었습니다.

`AuthContext.jsx`를 수정하여 로그인/회원가입 직후 토큰을 저장하고 `/auth/me`를 다시 호출합니다.
따라서 로그인 직후부터 `ADMIN`, `BUYER`, `SELLER` 권한을 정확히 사용할 수 있습니다.

## 관리자 배송관리 기능

- 다른 회원의 결제완료 이후 배송 대상 주문 일괄 조회
- 결제완료 / 상품준비중 / 배송중 / 배송완료 건수 표시
- 상태별 필터
- 주문번호 / 구매자 / 상품명 / 주소 검색
- 현재 배송중 주문 강조 표시
- 주문별 배송상태 변경
- 여러 주문 체크 후 일괄 배송상태 변경
- 배송완료/구매완료 주문은 조회 가능하되 배송상태 재변경은 제한
- 관리자 본인의 주문은 관리자 배송관리 대상에서 제외

배송 상태 진행 방향:

`PAID(결제완료) → PREPARING(상품준비중) → SHIPPING(배송중) → DELIVERED(배송완료)`

관리자가 `DELIVERED`로 변경하면 기존 리뷰 API 규칙에 따라 구매자는 해당 구매 상품의 리뷰를 작성할 수 있습니다.

## 변경 파일

### Backend
- `t5_backend_shopdb2/routers/admin_orders.py`

### Frontend
- `t5_frontend_shopdb2/src/auth/AuthContext.jsx`
- `t5_frontend_shopdb2/src/components/Header.jsx`
- `t5_frontend_shopdb2/src/components/Header.css`
- `t5_frontend_shopdb2/src/pages/AdminOrders.jsx`
- `t5_frontend_shopdb2/src/pages/AdminOrders.css`
- `t5_frontend_shopdb2/src/api/shopApi.js`

## 새 관리자 API

- `GET /admin/orders`
- `PATCH /admin/orders/{order_id}/shipping-status`
- `PATCH /admin/orders/bulk-shipping-status`

모든 관리자 API는 FastAPI에서 다시 `ADMIN` 역할을 확인합니다.
프론트 화면을 직접 열더라도 일반 회원은 관리자 API를 사용할 수 없습니다.

## 테스트 순서

1. FastAPI 재시작
2. React 개발 서버 재시작
3. 관리자 계정 로그인
4. 우측 상단에서 `🚚 배송관리` 확인
5. `/admin/orders` 접속
6. `배송중` 카드 클릭하여 현재 배송중 주문만 확인
7. 개별 주문 상태 변경 테스트
8. 여러 주문 체크 후 일괄 변경 테스트
9. `배송완료`로 변경된 상품을 구매자 계정으로 확인
10. 주문내역 또는 상품상세에서 리뷰 작성 버튼 활성화 확인
