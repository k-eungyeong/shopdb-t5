import { Link } from "react-router-dom";
import "./Header.css";

function Header() {
  return (
    <header className="site-header">
      <div className="site-header__inner">
        <Link to="/" className="site-header__logo">T5 SHOP</Link>

        <div className="site-header__search">
          <input type="text" placeholder="상품을 검색해보세요" />
          <button type="button" aria-label="검색">🔍</button>
        </div>

        <nav className="site-header__nav">
          <Link to="/wishlist">찜</Link>
          <Link to="/cart">장바구니</Link>
          <Link to="/mypage/orders">마이페이지</Link>
          <Link to="/login" className="site-header__login">로그인</Link>
        </nav>
      </div>
    </header>
  );
}

export default Header;