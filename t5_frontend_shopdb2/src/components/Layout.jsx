import { Outlet } from "react-router-dom";
import Header from "./Header";
import Footer from "./Footer";

// 모든 페이지 공통 틀(헤더 + 본문 + 푸터). <Outlet />에 라우트별 페이지가 들어감
function Layout() {
  return (
    <>
      <Header />
      <main className="page-main">
        <Outlet />
      </main>
      <Footer />
    </>
  );
}

export default Layout;