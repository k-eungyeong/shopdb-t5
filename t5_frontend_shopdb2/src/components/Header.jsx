import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { getCategories } from "../api/shopApi";
import "./Header.css";

function Header() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const [keyword, setKeyword] = useState("");
  const [logoutNotice, setLogoutNotice] = useState(false);
  const [categoryOpen, setCategoryOpen] = useState(false);
  const [categories, setCategories] = useState([]);

  useEffect(() => {
    setKeyword(new URLSearchParams(location.search).get("q") || "");
  }, [location.search]);

  // 홈 화면의 상품 필터 버튼과 순서가 어긋나지 않도록, 카테고리 목록을 하드코딩하지 않고
  // Home과 동일한 API(getCategories)에서 그대로 가져와 같은 순서로 보여줍니다.
  useEffect(() => {
    getCategories()
      .then((data) => setCategories(data.items.filter((c) => c.category_level === 2)))
      .catch(() => setCategories([]));
  }, []);

  // 페이지가 바뀌면 열려있던 카테고리 드롭다운을 닫습니다.
  useEffect(() => {
    setCategoryOpen(false);
  }, [location.pathname, location.search]);

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

  // 관리자/판매자 센터 화면에서는 쇼핑몰 홍보 문구가 불필요해서 숨기고, 그만큼 헤더 공간을 검색창/메뉴에 씁니다.
  const isStaffView = isAdmin || isSeller;

  return (
    <header className="site-header">
      {!isStaffView && (
        <div className="site-header__top">
          <span>오늘도 좋은 쇼핑, T5 SHOP</span>
          <span>FastAPI + React + MySQL</span>
        </div>
      )}

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
          <div className="site-header__category-dropdown">
            <button
              type="button"
              className={`site-header__category-toggle ${categoryOpen ? "is-open" : ""}`}
              onClick={() => setCategoryOpen((v) => !v)}
              aria-expanded={categoryOpen}
            >
              카테고리 <span className="caret">▾</span>
            </button>
            {categoryOpen && (
              <div className="site-header__category-menu" role="menu">
                <Link to="/" onClick={() => setCategoryOpen(false)}>전체상품</Link>
                {categories.map((c) => (
                  <Link key={c.category_id} to={`/?category=${c.category_id}`} onClick={() => setCategoryOpen(false)}>
                    {c.category_name}
                  </Link>
                ))}
              </div>
            )}
          </div>
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
