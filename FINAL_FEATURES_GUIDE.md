# T5 SHOP 최종 기능 확장 안내

이 버전은 기존 MySQL **테이블 구조를 추가/삭제/변경하지 않고** 현재 존재하는 테이블과 컬럼만 사용해 기능을 확장한 버전입니다.

## 이번 버전에 추가된 핵심 기능

### 관리자 센터
- 오늘 매출 / 이번 달 매출 / 오늘 주문 / 신규 회원 / 배송 현황 / 환불 대기 / 재고 부족 요약
- 최근 7일 결제 매출 막대 그래프
- 판매량 TOP 10 상품
- 재고 부족 옵션 목록
- 회원별 주문 수 / 구매금액 통계
- 기존 회원/판매자/상품/카테고리 관리 유지
- 환불 요청 조회 및 검토중/승인/거절/완료 처리
- 환불 완료 시 기존 `inventories`, `payments`, `payment_transactions`, `orders`, `order_items`를 이용해 재고/주문/결제 상태 반영
- 전체 구매리뷰 조회 및 관리자 삭제
- 배송완료 상태를 잘못 처리한 경우 **관리자만 `DELIVERED -> SHIPPING` 한 단계 정정** 가능
- 단, 구매완료(COMPLETED)는 정정 불가

### 판매자 센터
- 오늘 판매완료 매출 / 이번 달 매출 / 주문 상태 / 재고 부족 요약
- 최근 7일 판매완료 매출 그래프
- 재고 부족 옵션 경고
- 상품/옵션/재고 관리
- 판매자 본인 상품의 주문만 배송 상태 처리
- 주문번호, 구매자, 상품명, 배송지 검색
- 상품별 판매매출 TOP 10
- 정산 대상 매출 조회
- 고객 문의 답변
- 구매리뷰 조회

### 구매자 쇼핑몰
- 상품 정렬: 최신순 / 판매량순 / 평점순 / 리뷰많은순 / 가격낮은순 / 가격높은순 / 재고많은순
- 가격 범위 검색
- 페이지네이션(기본 12개)
- 품절 상품 카드 표시
- 품절 옵션은 선택/장바구니 담기 제한
- 주문 생성 시 재고 재확인
- 배송상태 조회
- 배송완료 후 리뷰 작성
- 내 리뷰 목록 / 수정 / 삭제
- 배송완료 또는 구매완료 주문의 환불 신청
- 주문상세에서 환불 처리상태 확인

## 배송 상태 정정 규칙

일반 흐름:

`PAID -> PREPARING -> SHIPPING -> DELIVERED -> COMPLETED`

관리자 실수 정정은 `DELIVERED -> SHIPPING`만 허용합니다.
`COMPLETED`는 리뷰/정산의 기준이 될 수 있으므로 되돌리지 않습니다.

## 환불 처리 흐름

구매자:

`배송완료/구매완료 -> 환불 신청(REQUESTED)`

관리자:

`REQUESTED -> REVIEWING -> APPROVED -> COMPLETED`

또는 `REJECTED` 처리 가능.

환불 완료 시 기존 테이블을 사용해 주문 상태, 주문상품 상태, 결제 상태와 재고를 함께 반영합니다.

## 실행

### Backend
```bash
cd t5_backend_shopdb2
uv sync
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Swagger:
`http://127.0.0.1:8000/docs`

### Frontend
```bash
cd t5_frontend_shopdb2
npm install
npm run dev -- --port 5174
```

Frontend:
`http://localhost:5174/`

## 검사 결과
- Backend 전체 Python `compileall` 통과
- Frontend 전체 JS/JSX Babel parser 문법검사 통과
- ESLint는 기존 프로젝트의 React effect 관련 엄격 규칙을 제외하고 오류 없음 확인
- 이 작업 환경은 Windows에서 설치된 Vite/Rolldown 네이티브 패키지와 Linux 환경이 달라 최종 `vite build`는 네이티브 바인딩 단계에서 실행할 수 없었음
- Windows에서 `npm install`을 새로 실행하면 해당 플랫폼용 의존성이 설치됨

## DB 관련 원칙
이번 작업에서 `CREATE TABLE`, `ALTER TABLE`, 컬럼 추가/삭제/자료형 변경을 하지 않았습니다.
