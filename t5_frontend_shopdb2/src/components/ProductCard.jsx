import { Link } from "react-router-dom";
import "./ProductCard.css";

function formatPrice(price) {
  return price.toLocaleString("ko-KR") + "원";
}

function ProductCard({ product }) {
  const hasDiscount = product.sale_price < product.regular_price;
  const discountRate = hasDiscount
    ? Math.round((1 - product.sale_price / product.regular_price) * 100)
    : 0;

  return (
    <Link to={`/products/${product.product_id}`} className="product-card">
      <div className="product-card__image">
        {product.image ? (
          <img src={product.image} alt={product.product_name} />
        ) : (
          <div className="product-card__no-image">이미지 준비 중</div>
        )}
      </div>
      <div className="product-card__body">
        <p className="product-card__name">{product.product_name}</p>
        <p className="product-card__desc">{product.short_description}</p>
        <div className="product-card__price">
          {hasDiscount && <span className="product-card__discount">{discountRate}%</span>}
          <span className="product-card__sale-price">{formatPrice(product.sale_price)}</span>
        </div>
        {hasDiscount && (
          <p className="product-card__regular-price">{formatPrice(product.regular_price)}</p>
        )}
      </div>
    </Link>
  );
}

export default ProductCard;