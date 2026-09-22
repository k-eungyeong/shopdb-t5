# T5 SHOP 역할별 관리자/판매자 센터

## 핵심 원칙
- 기존 MySQL 테이블 구조를 변경하지 않았습니다.
- React -> FastAPI -> MySQL 구조를 유지합니다.
- ADMIN / SELLER / BUYER 역할은 기존 `roles`, `user_roles`를 사용합니다.
- 판매자 상품 소유권은 기존 `products.seller_user_id`를 사용합니다.
- 판매자별 배송 상태는 기존 `order_items.item_status`를 사용합니다.

## 로그인 후 기본 이동
- ADMIN: `/admin`
- SELLER: `/seller`
- BUYER: `/`

판매자가 BUYER 역할을 함께 가지고 있어도 SELLER가 있으면 판매자센터로 이동합니다.

## 관리자 센터
`/admin`
- 대시보드: 오늘 결제매출, 신규회원, 판매자/상품/배송 지표
- 회원 관리: 회원목록, ACTIVE/INACTIVE/SUSPENDED/WITHDRAWN 상태 변경
- 판매자 관리: 입점 판매자 목록, ACTIVE/INACTIVE/SUSPENDED/PENDING 상태 변경
- 전체 상품: 판매자별 상품/재고 조회, 판매상태 검수
- 카테고리: 기존 카테고리 조회/추가/활성 여부/표시순서 관리
- 운영 정보: 기존 회사정책과 실제 결제수단 사용현황 조회
- 전체 주문·배송: `/admin/orders`에서 전체 회원 주문 배송상태 관리 및 일괄 변경

## 판매자 센터
`/seller`
- 대시보드: 내 상품, 주문, 배송, 판매완료 매출, 리뷰, 미답변문의
- 상품·재고: 상품 등록/수정/삭제(soft delete), 옵션 추가, 옵션별 재고 수정
- 주문·배송: 자기 상품이 포함된 주문만 조회, 상품준비중 -> 배송중 -> 배송완료 처리
- 정산: 배송완료/구매완료된 자기 상품의 매출 합계와 정산 계좌 조회
- 고객문의: 판매자 조직에 들어온 `buyer_inquiries` 조회 및 답변
- 구매리뷰: 자기 상품에 작성된 리뷰 조회

## 여러 판매자가 한 주문에 섞인 경우
`orders.order_status`만 판매자가 직접 바꾸면 다른 판매자의 상품까지 함께 배송완료가 되는 문제가 생길 수 있습니다.
따라서 판매자 센터는 자기 상품의 `order_items.item_status`만 변경합니다.
전체 주문 상태는 모든 주문상품의 상태를 보고 자동 재계산합니다.

예:
- 판매자 A 상품 = DELIVERED
- 판매자 B 상품 = SHIPPING
- 전체 주문 = SHIPPING

모든 상품이 DELIVERED가 되면 전체 주문도 DELIVERED가 됩니다.

## 리뷰 작성 조건
리뷰는 주문 전체 상태가 아니라 해당 `order_items.item_status`가 `DELIVERED` 또는 `COMPLETED`인지 검사합니다.
따라서 여러 판매자 주문이어도 실제 배송완료된 상품부터 리뷰를 작성할 수 있습니다.

## 현재 DB 구조상 제한
새 테이블을 추가하지 않는 조건 때문에 아래는 완전한 상용 기능이 아니라 기존 테이블 범위의 구현입니다.
- 실제 택배사 송장 추적: 송장번호/택배사 저장 테이블 또는 외부 택배 API가 필요함
- 판매자 수수료 정산/출금: 수수료율/정산 지급 이력 테이블이 없어 `order_items.item_amount` 기준의 정산 대상 매출을 표시함
- 공지/이벤트 배너 편집: 전용 테이블이 없어 관리자센터에서는 기존 `company_policies`와 결제수단 현황만 표시함

## 실행
### Backend
```bash
cd t5_backend_shopdb2
uv sync
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
Swagger: http://127.0.0.1:8000/docs

### Frontend
```bash
cd t5_frontend_shopdb2
npm install
npm run dev -- --port 5174
```
Frontend: http://localhost:5174/

## 테스트 순서
1. 관리자 계정 로그인 -> `/admin` 이동 확인
2. 관리자센터에서 회원/판매자/상품/카테고리 화면 조회
3. `/admin/orders`에서 전체 배송상태 변경
4. 판매자 계정 로그인 -> `/seller` 이동 확인
5. 판매자센터에서 자기 상품만 표시되는지 확인
6. 상품 등록/재고 수정 확인
7. 판매자의 주문·배송에서 `상품준비중 -> 배송중 -> 배송완료` 순서로 변경
8. 구매자 계정으로 로그인하여 주문내역 배송상태 확인
9. 배송완료된 주문상품에서 리뷰 작성 버튼 활성화 확인
