import "./EmptyState.css";

function MyOrders() {
  return (
    <div className="empty-state">
      <h2>주문 내역이 없습니다</h2>
      <p>로그인 및 주문 API 연결 후 이곳에서 주문 상태와 리뷰 작성 버튼을 볼 수 있습니다</p>
    </div>
  );
}

export default MyOrders;