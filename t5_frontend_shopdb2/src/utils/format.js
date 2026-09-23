// 여러 페이지(장바구니/주문/관리자/판매자 화면 등)에서 반복되던 포맷팅 함수를 한 곳으로 모았습니다.
// 값을 바꿀 일이 생기면 이 파일 하나만 고치면 전체 화면에 반영됩니다.

// 금액을 "12,000원" 형태의 한국어 통화 문자열로 바꿉니다.
export function money(value) {
  return `${Number(value || 0).toLocaleString("ko-KR")}원`;
}

// 주문(orders.order_status) / 주문상품(order_items.item_status) 상태 코드를 한글 라벨로 바꿉니다.
export const statusText = {
  ORDERED: "주문완료",
  PAYMENT_PENDING: "결제대기",
  PAID: "결제완료",
  PREPARING: "상품준비중",
  SHIPPING: "배송중",
  DELIVERED: "배송완료",
  COMPLETED: "구매완료",
  CANCELLED: "취소",
  REFUNDED: "환불",
};
