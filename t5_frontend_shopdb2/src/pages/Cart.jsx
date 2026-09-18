import { Link } from "react-router-dom";
import "./EmptyState.css";

function Cart() {
  return (
    <div className="empty-state">
      <h2>장바구니가 비어있습니다</h2>
      <p>담긴 상품이 여기에 표시될 예정입니다 (t5_carts API 연결 예정)</p>
      <Link to="/">쇼핑 계속하기</Link>
    </div>
  );
}

export default Cart;