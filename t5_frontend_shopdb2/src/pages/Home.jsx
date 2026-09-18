import ProductCard from "../components/ProductCard";
import { mockProducts } from "../data/mockProducts";
import "./Home.css";

function Home() {
  return (
    <div className="home">
      <section className="home__banner">
        <h1>T5 SHOP에 오신 걸 환영합니다</h1>
        <p>AI 기기부터 패션까지, 필요한 모든 것</p>
      </section>

      <section className="home__products">
        <h2 className="home__section-title">전체 상품</h2>
        <div className="home__grid">
          {mockProducts.map((product) => (
            <ProductCard key={product.product_id} product={product} />
          ))}
        </div>
      </section>
    </div>
  );
}

export default Home;