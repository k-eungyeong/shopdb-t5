import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import "./Header.css";

function Header() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const [keyword, setKeyword] = useState("");
  const [logoutNotice, setLogoutNotice] = useState(false);

  useEffect(() => {
    setKeyword(new URLSearchParams(location.search).get("q") || "");
  }, [location.search]);

  useEffect(() => {
    if (!logoutNotice) return undefined;
    const timer = window.setTimeout(() => setLogoutNotice(false), 3200);
    return () => window.clearTimeout(timer);
  }, [logoutNotice]);

  function handleSearch(e) {
    e.preventDefault();
    const q = keyword.trim();
    navigate(q ? `/?q=${encodeURIComponent(q)}` : "/");
  }

  async function handleLogout() {
    await logout();
    setLogoutNotice(true);
    navigate("/", { replace: true });
  }

  const isAdmin = user?.roles?.includes("ADMIN");
  const isSeller = user?.roles?.includes("SELLER");

  return (
    <header className="site-header">
      <div className="site-header__top">
        <span>오늘도 좋은 쇼핑, T5 SHOP</span>
        <span>FastAPI + React + MySQL</span>
      </div>

      <div className="site-header__inner">
        <Link to="/" className="site-header__logo"><span>T5</span> SHOP</Link>

        <form className="site-header__search" onSubmit={handleSearch}>
          <input
            type="text"
            placeholder="상품명을 검색해보세요"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
          />
          <button type="submit" aria-label="검색">⌕</button>
        </form>

        <nav className="site-header__nav">
          {/* 역할에 따라 관리센터 바로가기를 쇼핑 메뉴보다 앞에 표시합니다. */}
          {isAdmin && (
            <Link to="/admin" className="site-header__role-center">
              <b>⚙</b><span>관리자센터</span>
            </Link>
          )}
          {!isAdmin && isSeller && (
            <Link to="/seller" className="site-header__role-center">
              <b>🏪</b><span>판매자센터</span>
            </Link>
          )}

          <Link to="/wishlist"><b>♡</b><span>찜</span></Link>
          <Link to="/cart"><b>🛒</b><span>장바구니</span></Link>
          <Link to="/mypage/orders"><b>◉</b><span>주문내역</span></Link>

          {user ? (
            <div className="site-header__member">
              <Link to="/mypage" className="site-header__userlink">{user.user_name}님</Link>
              <button type="button" onClick={handleLogout}>로그아웃</button>
            </div>
          ) : (
            <Link to="/login" className="site-header__login">로그인</Link>
          )}
        </nav>
      </div>

      <div className="site-header__category-bar">
        <div>
          <Link to="/">전체상품</Link>
          <Link to="/?category=3">노트북</Link>
          <Link to="/?category=4">스마트폰</Link>
          <Link to="/?category=5">상의</Link>
          <Link to="/?category=6">신발</Link>
        </div>
      </div>

      {logoutNotice && (
        <div className="site-header__logout-toast" role="status" aria-live="polite">
          <span>✓</span>
          <div>
            <strong>로그아웃되었습니다.</strong>
            <small>안전하게 로그아웃했어요. 다음에 또 만나요!</small>
          </div>
          <button type="button" aria-label="알림 닫기" onClick={() => setLogoutNotice(false)}>×</button>
        </div>
      )}
    </header>
  );
}

export default Header;
