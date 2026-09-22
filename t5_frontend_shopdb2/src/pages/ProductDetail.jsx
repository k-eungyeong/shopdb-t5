import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  addToCart,
  addWishlist,
  checkWishlist,
  createReview,
  deleteWishlist,
  getProduct,
  getReviewEligibility,
} from "../api/shopApi";
import { useAuth } from "../auth/AuthContext";
import "./ProductDetail.css";

const money = (value) => Number(value || 0).toLocaleString("ko-KR") + "원";

function ProductDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [product, setProduct] = useState(null);
  const [variantId, setVariantId] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [wishlist, setWishlist] = useState(null);
  const [reviewEligibility, setReviewEligibility] = useState(null);
  const [reviewItem, setReviewItem] = useState(null);
  const [rating, setRating] = useState(5);
  const [reviewTxt, setReviewTxt] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  // 상품, 찜 상태, 리뷰 작성 가능 여부를 한 번에 다시 읽는 함수입니다.
  // 리뷰 등록 뒤에도 이 함수를 사용하면 화면의 리뷰 목록과 버튼 상태가 즉시 갱신됩니다.
  async function loadPage({ keepVariant = false } = {}) {
    const data = await getProduct(id);
    setProduct(data);

    if (!keepVariant) {
      const firstAvailable = data.variants?.find((v) => Number(v.available_stock || 0) > 0) || data.variants?.[0];
      setVariantId(firstAvailable?.variant_id ? String(firstAvailable.variant_id) : "");
    }

    if (user) {
      const [wish, eligibility] = await Promise.all([
        checkWishlist(id),
        getReviewEligibility(id),
      ]);
      setWishlist(wish.is_wishlisted ? wish.wishlist : null);
      setReviewEligibility(eligibility);
    } else {
      setWishlist(null);
      setReviewEligibility(null);
    }
  }

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        setError("");
        await loadPage();
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
    // id 또는 로그인 회원이 바뀌면 현재 사용자의 구매/리뷰 가능 여부를 다시 검사합니다.
  }, [id, user]);

  const selectedVariant = useMemo(
    () => product?.variants?.find((v) => String(v.variant_id) === variantId),
    [product, variantId],
  );
  const finalPrice = Number(product?.sale_price || 0) + Number(selectedVariant?.additional_price || 0);

  function requireLogin() {
    if (!user) {
      navigate(`/login?next=${encodeURIComponent(`/products/${id}`)}`);
      return false;
    }
    return true;
  }

  async function handleCart() {
    if (!requireLogin()) return;
    if (!selectedVariant) return setMessage("구매 옵션을 선택해주세요.");
    if (Number(selectedVariant.available_stock || 0) <= 0) return setMessage("선택한 옵션은 품절되었습니다.");
    if (quantity > Number(selectedVariant.available_stock || 0)) return setMessage(`현재 재고는 ${selectedVariant.available_stock}개입니다.`);
    try {
      await addToCart({ productId: product.product_id, variantId: selectedVariant.variant_id, quantity });
      setMessage("장바구니에 담았습니다.");
    } catch (err) {
      setMessage(err.message);
    }
  }

  async function handleWishlist() {
    if (!requireLogin()) return;
    try {
      if (wishlist) {
        await deleteWishlist(wishlist.wishlist_id);
        setWishlist(null);
        setMessage("찜 목록에서 삭제했습니다.");
      } else {
        const data = await addWishlist(product.product_id);
        setWishlist(data.wishlist);
        setMessage("찜 목록에 추가했습니다.");
      }
    } catch (err) {
      setMessage(err.message);
    }
  }

  function openReview() {
    if (!requireLogin()) return;

    // 서버가 실제 구매내역을 확인해 준 order_item_id를 사용합니다.
    // 프론트에서 임의의 주문상품 번호를 만들어 보내지 않습니다.
    if (!reviewEligibility?.can_review || !reviewEligibility.order_item) {
      setMessage(reviewEligibility?.message || "배송완료된 구매 상품만 리뷰를 작성할 수 있습니다.");
      return;
    }

    setRating(5);
    setReviewTxt("");
    setReviewItem(reviewEligibility.order_item);
  }

  async function submitReview(e) {
    e.preventDefault();
    try {
      await createReview({
        order_item_id: reviewItem.order_item_id,
        product_id: Number(id),
        rating: Number(rating),
        review_txt: reviewTxt,
      });

      setReviewItem(null);
      setReviewTxt("");
      setMessage("리뷰가 등록되었습니다.");

      // 방금 작성한 리뷰가 구매후기 목록에 바로 보이도록 상품과 자격을 다시 조회합니다.
      await loadPage({ keepVariant: true });
    } catch (err) {
      setMessage(err.message);
    }
  }

  if (loading) return <div className="shop-state">상품 정보를 불러오는 중입니다...</div>;
  if (error || !product) {
    return (
      <div className="product-detail__not-found">
        <p>{error || "상품을 찾을 수 없습니다."}</p>
        <Link to="/">홈으로 돌아가기</Link>
      </div>
    );
  }

  return (
    <div className="product-page">
      <div className="product-page__breadcrumb">
        <Link to="/">홈</Link><span>›</span><span>{product.category_name}</span><span>›</span><b>{product.product_name}</b>
      </div>

      <section className="product-detail">
        <div className="product-detail__image">
          {product.image ? (
            <img src={product.image} alt={product.product_name} />
          ) : (
            <div className="product-detail__no-image">T5 SHOP</div>
          )}
        </div>

        <div className="product-detail__info">
          <span className="product-detail__category">{product.category_name} · {product.product_code}</span>
          <h1>{product.product_name}</h1>
          <p className="product-detail__desc">{product.short_description}</p>
          <div className="product-detail__rating">
            ★ {Number(product.avg_rating || 0).toFixed(1)} <span>리뷰 {product.review_count}개</span>
          </div>

          <div className="product-detail__pricebox">
            <del>{money(product.regular_price)}</del>
            <strong>{money(finalPrice)}</strong>
          </div>

          <label className="product-detail__label">옵션 선택</label>
          <select value={variantId} onChange={(e) => setVariantId(e.target.value)}>
            {product.variants.map((v) => (
              <option key={v.variant_id} value={v.variant_id} disabled={Number(v.available_stock) <= 0}>
                {[
                  v.option_name1 && `${v.option_name1}: ${v.option_value1}`,
                  v.option_name2 && `${v.option_name2}: ${v.option_value2}`,
                ].filter(Boolean).join(" / ") || v.sku_code}
                {Number(v.additional_price) > 0 ? ` (+${money(v.additional_price)})` : ""} · 재고 {v.available_stock}
              </option>
            ))}
          </select>

          <div className="product-detail__quantity">
            <span>수량</span>
            <div>
              <button onClick={() => setQuantity((q) => Math.max(1, q - 1))}>−</button>
              <b>{quantity}</b>
              <button onClick={() => setQuantity((q) => q + 1)}>＋</button>
            </div>
          </div>

          <div className="product-detail__total">
            <span>총 상품금액</span>
            <strong>{money(finalPrice * quantity)}</strong>
          </div>

          {message && <p className="product-detail__message">{message}</p>}

          <div className="product-detail__actions">
            <button type="button" className="btn btn--outline" onClick={handleWishlist}>
              {wishlist ? "♥ 찜 해제" : "♡ 찜하기"}
            </button>
            <button type="button" className="btn btn--primary" onClick={handleCart} disabled={!selectedVariant || Number(selectedVariant.available_stock || 0) <= 0}>
              {!selectedVariant || Number(selectedVariant.available_stock || 0) <= 0 ? "품절" : "장바구니 담기"}
            </button>
          </div>
        </div>
      </section>

      <section className="product-detail__description">
        <h2>상품 상세정보</h2>
        <p>{product.description}</p>
      </section>

      <section className="product-reviews">
        <div className="product-reviews__head">
          <div>
            <h2>구매후기</h2>
            <p>실제 구매한 상품이 배송완료되면 구매후기를 작성할 수 있습니다.</p>
          </div>
          <strong>★ {Number(product.avg_rating || 0).toFixed(1)}</strong>
        </div>

        <div className="product-review-write-box">
          <div>
            <b>내 구매후기</b>
            {!user ? (
              <p>로그인하면 이 상품의 구매 여부를 확인해 리뷰 작성 버튼을 활성화합니다.</p>
            ) : (
              <p>{reviewEligibility?.message || "구매내역을 확인하고 있습니다."}</p>
            )}
          </div>

          {!user ? (
            <button type="button" onClick={() => navigate(`/login?next=${encodeURIComponent(`/products/${id}`)}`)}>
              로그인 후 확인
            </button>
          ) : (
            <button
              type="button"
              className="product-review-write-button"
              onClick={openReview}
              disabled={!reviewEligibility?.can_review}
            >
              리뷰 작성
            </button>
          )}
        </div>

        {product.reviews.length === 0 ? (
          <p className="product-reviews__empty">아직 작성된 리뷰가 없습니다.</p>
        ) : (
          product.reviews.map((review) => (
            <article key={review.review_id}>
              <div>
                <b>{"★".repeat(review.rating)}{"☆".repeat(5 - review.rating)}</b>
                <span>{review.user_name}</span>
                <time>{String(review.added_at).slice(0, 10)}</time>
              </div>
              <p>{review.review_txt}</p>
            </article>
          ))
        )}
      </section>

      {reviewItem && (
        <div className="product-review-modal" onClick={() => setReviewItem(null)}>
          <form onSubmit={submitReview} onClick={(e) => e.stopPropagation()}>
            <h2>리뷰 작성</h2>
            <p>{reviewItem.product_name_snapshot}</p>
            <small>주문번호 {reviewItem.order_no}</small>

            <label>
              별점
              <select value={rating} onChange={(e) => setRating(e.target.value)}>
                <option value="5">★★★★★ 5점</option>
                <option value="4">★★★★☆ 4점</option>
                <option value="3">★★★☆☆ 3점</option>
                <option value="2">★★☆☆☆ 2점</option>
                <option value="1">★☆☆☆☆ 1점</option>
              </select>
            </label>

            <label>
              후기
              <textarea
                required
                minLength={2}
                value={reviewTxt}
                onChange={(e) => setReviewTxt(e.target.value)}
                placeholder="구매한 상품의 후기를 작성해주세요."
              />
            </label>

            <div>
              <button type="button" onClick={() => setReviewItem(null)}>취소</button>
              <button type="submit">리뷰 등록</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

export default ProductDetail;
