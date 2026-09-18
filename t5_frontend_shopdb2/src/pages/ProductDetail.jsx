import { useParams, Link } from "react-router-dom";
import { mockProducts } from "../data/mockProducts";
import "./ProductDetail.css";

function formatPrice(price) {
  return price.toLocaleString("ko-KR") + "원";
}

function ProductDetail() {
  const { id } = useParams();
  const product = mockProducts.find((p) => String(p.product_id) === id);

  if (!product) {
    return (
      <div className="product-detail__not-found">
        <p>상품을 찾을 수 없습니다.</p>
        <Link to="/">홈으로 돌아가기</Link>
      </div>
    );
  }

  return (
    <div className="product-detail">
      <div className="product-detail__image">
        {product.image ? (
          <img src={product.image} alt={product.product_name} />
        ) : (
          <div className="product-detail__no-image">이미지 준비 중</div>
        )}
      </div>

      <div className="product-detail__info">
        <h1>{product.product_name}</h1>
        <p className="product-detail__desc">{product.short_description}</p>
        <p className="product-detail__price">{formatPrice(product.sale_price)}</p>

        <div className="product-detail__actions">
          <button type="button" className="btn btn--outline">찜하기</button>
          <button type="button" className="btn btn--primary">장바구니 담기</button>
        </div>
      </div>
    </div>
  );
}

export default ProductDetail;