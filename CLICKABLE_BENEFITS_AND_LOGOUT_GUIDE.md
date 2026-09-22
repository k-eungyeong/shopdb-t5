# 홈 4개 기능 카드 클릭 + 로그아웃 표시 수정

## SQL / Backend
- SQL 테이블: 변경 없음
- FastAPI: 변경 없음

## 변경된 Frontend 파일
1. `t5_frontend_shopdb2/src/pages/Home.jsx`
   - 4개 기능 카드를 `<div>`에서 실제 클릭 가능한 `<button>`으로 변경
   - 빠른 배송 → `/mypage/orders`
   - 실시간 재고 → 상품 영역 이동 + 재고 수량 많은 순 화면 정렬
   - 구매 리뷰 → 상품 영역 이동 + 리뷰 수 많은 순 화면 정렬
   - 찜 & 장바구니 → 찜/장바구니 선택 퀵 메뉴

2. `t5_frontend_shopdb2/src/pages/Home.css`
   - 기능 카드 hover/active/focus 스타일
   - 퀵 메뉴 스타일
   - 재고/리뷰 안내문 스타일

3. `t5_frontend_shopdb2/src/components/Header.jsx`
   - 로그아웃 완료 후 홈으로 이동
   - 3.2초 동안 "로그아웃되었습니다" 토스트 표시

4. `t5_frontend_shopdb2/src/components/Header.css`
   - 로그아웃 토스트 UI와 애니메이션

5. `t5_frontend_shopdb2/src/auth/AuthContext.jsx`
   - 서버 logout API가 실패하더라도 로컬 JWT 토큰과 사용자 상태를 반드시 제거하도록 보완

## 확인 방법
- 홈의 네 기능 카드를 각각 클릭합니다.
- 빠른 배송: 주문내역으로 이동하는지 확인합니다.
- 실시간 재고: 상품영역으로 내려가고 재고 많은 상품 순으로 보이는지 확인합니다.
- 구매 리뷰: 리뷰 많은 상품 순으로 보이는지 확인합니다.
- 찜 & 장바구니: 두 개의 바로가기 버튼이 열리는지 확인합니다.
- 로그인 후 로그아웃: 우측 상단에 로그아웃 완료 알림이 나타나고 헤더가 로그인 버튼으로 바뀌는지 확인합니다.
