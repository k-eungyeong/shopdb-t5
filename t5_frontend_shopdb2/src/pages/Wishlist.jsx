import { Link } from "react-router-dom";
import "./EmptyState.css";

function Wishlist() {
  return (
    <div className="empty-state">
      <h2>찜한 상품이 없습니다</h2>
      <p>찜한 상품이 여기에 표시될 예정입니다 (t5_wishlist_items API 연결 예정)</p>
      <Link to="/">쇼핑 계속하기</Link>
    </div>
  );
}

export default Wishlist;