import { Link } from "react-router-dom";
import { money } from "../utils/format";
import "./ProductCard.css";

function ProductCard({ product }) {
  const regular = Number(product.regular_price || 0);
  const sale = Number(product.sale_price || 0);
  const hasDiscount = regular > sale;
  const discountRate = hasDiscount ? Math.round((1 - sale / regular) * 100) : 0;

  return (
    <Link to={`/products/${product.product_id}`} className="product-card">
      <div className="product-card__image">
        {product.image ? <img src={product.image} alt={product.product_name} /> : <div className="product-card__no-image">T5 SHOP</div>}
        {product.is_sold_out ? <span className="product-card__badge product-card__badge--soldout">품절</span> : product.product_status === "SALE" && <span className="product-card__badge">SALE</span>}
      </div>
      <div className="product-card__body">
        <p className="product-card__category">{product.category_name}</p>
        <p className="product-card__name">{product.product_name}</p>
        <p className="product-card__desc">{product.short_description}</p>
        <div className="product-card__price">
          {hasDiscount && <span className="product-card__discount">{discountRate}%</span>}
          <span className="product-card__sale-price">{money(sale)}</span>
        </div>
        {hasDiscount && <p className="product-card__regular-price">{money(regular)}</p>}
        <div className="product-card__meta">
          <span>★ {Number(product.avg_rating || 0).toFixed(1)}</span>
          <span>리뷰 {product.review_count || 0}</span>
          <span>재고 {product.available_stock || 0}</span>
        </div>
      </div>
    </Link>
  );
}

export default ProductCard;
