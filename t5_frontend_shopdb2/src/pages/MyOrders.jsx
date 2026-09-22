import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { completeOrder, createReview, getOrders } from "../api/shopApi";
import "./Orders.css";

const money = (v) => Number(v || 0).toLocaleString("ko-KR") + "원";
const statusText = {
  ORDERED: "주문완료",
  PAYMENT_PENDING: "결제대기",
  PAID: "결제완료",
  PREPARING: "상품준비중",
  SHIPPING: "배송중",
  DELIVERED: "배송완료",
  COMPLETED: "구매완료",
  CANCELLED: "취소",
  REFUNDED: "환불",
};

const deliverySteps = [
  { key: "PAID", label: "결제완료" },
  { key: "PREPARING", label: "상품준비중" },
  { key: "SHIPPING", label: "배송중" },
  { key: "DELIVERED", label: "배송완료" },
];

const deliveryRank = {
  PAID: 0,
  PREPARING: 1,
  SHIPPING: 2,
  DELIVERED: 3,
  COMPLETED: 3,
};

function DeliveryTracker({ status }) {
  const current = deliveryRank[status] ?? -1;
  const stopped = ["CANCELLED", "REFUNDED"].includes(status);

  if (stopped) {
    return <div className="delivery-tracker delivery-tracker--stopped">현재 주문 상태: {statusText[status]}</div>;
  }

  return (
    <div className="delivery-tracker">
      <div className="delivery-tracker__title">
        <b>배송조회</b>
        <span>현재 상태: {statusText[status] || status}</span>
      </div>
      <div className="delivery-steps">
        {deliverySteps.map((step, index) => (
          <div className={`delivery-step ${index <= current ? "is-active" : ""}`} key={step.key}>
            <span>{index < current ? "✓" : index + 1}</span>
            <b>{step.label}</b>
          </div>
        ))}
      </div>
      <small>※ 별도 배송 테이블 없이 주문 상태(order_status)를 이용한 쇼핑몰 내부 배송조회입니다.</small>
    </div>
  );
}

function MyOrders() {
  const [orders, setOrders] = useState([]);
  const [error, setError] = useState("");
  const [reviewItem, setReviewItem] = useState(null);
  const [rating, setRating] = useState(5);
  const [reviewTxt, setReviewTxt] = useState("");
  const [processingOrderId, setProcessingOrderId] = useState(null);
  const [trackingOrderId, setTrackingOrderId] = useState(null);

  async function load() {
    try {
      const data = await getOrders();
      setOrders(data.items);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function confirmPurchase(orderId) {
    if (!window.confirm("상품을 정상적으로 받으셨나요? 구매완료로 확정할까요?")) return;
    try {
      setProcessingOrderId(orderId);
      const result = await completeOrder(orderId);
      window.alert(result.message);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setProcessingOrderId(null);
    }
  }

  function openReview(item) {
    setRating(5);
    setReviewTxt("");
    setReviewItem(item);
  }

  async function submitReview(e) {
    e.preventDefault();
    try {
      await createReview({
        order_item_id: reviewItem.order_item_id,
        product_id: reviewItem.product_id,
        rating: Number(rating),
        review_txt: reviewTxt,
      });
      setReviewItem(null);
      setReviewTxt("");
      await load();
      window.alert("리뷰가 등록되었습니다.");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="orders-page">
      <div className="shop-list-page__title">
        <span>MY PAGE</span>
        <h1>주문 내역</h1>
        <p>판매자 또는 관리자가 배송완료로 변경하면 구매한 상품의 리뷰를 바로 작성할 수 있습니다.</p>
      </div>

      {error && <div className="shop-state shop-state--error">{error}</div>}
      {!error && orders.length === 0 && (
        <div className="empty-state"><h2>주문 내역이 없습니다</h2></div>
      )}

      <div className="orders-list">
        {orders.map((order) => {
          const isTrackingOpen = trackingOrderId === order.order_id;

          return (
            <section className="order-card" key={order.order_id}>
              <header>
                <div>
                  <time>{String(order.ordered_at).slice(0, 10)}</time>
                  <b>{order.order_no}</b>
                </div>
                <span>{statusText[order.order_status] || order.order_status}</span>
              </header>

              {order.items.map((item) => {
                const canReview = ["DELIVERED", "COMPLETED"].includes(item.item_status);
                return (
                <div className="order-item" key={item.order_item_id}>
                  <div>
                    <small>주문상품 #{item.order_item_id}</small>
                    <Link to={`/products/${item.product_id}`}><h3>{item.product_name_snapshot}</h3></Link>
                    <p>{item.sku_snapshot} · {item.quantity}개</p>
                  </div>

                  <strong>{money(item.item_amount)}</strong>

                  {item.review_id ? (
                    <span className="review-done">★ {item.rating} 리뷰완료</span>
                  ) : (
                    <div className="order-review-action">
                      <button
                        type="button"
                        className="review-write-button"
                        onClick={() => openReview(item)}
                        disabled={!canReview}
                        title={canReview ? "구매후기 작성" : "배송완료 후 작성할 수 있습니다."}
                      >
                        리뷰 작성
                      </button>
                      {!canReview && <small className="review-waiting">배송완료 후 활성화</small>}
                    </div>
                  )}
                </div>
                );
              })}

              {isTrackingOpen && <DeliveryTracker status={order.order_status} />}

              <footer>
                <span>배송지 {order.shipping_address1 || "-"}</span>
                <strong>총 {money(order.total_amount)}</strong>
                <div className="order-card__actions">
                  <button
                    type="button"
                    className="tracking-button"
                    onClick={() => setTrackingOrderId(isTrackingOpen ? null : order.order_id)}
                  >
                    {isTrackingOpen ? "배송조회 닫기" : "배송조회"}
                  </button>
                  <Link to={`/mypage/orders/${order.order_id}`}>상세보기</Link>
                  {order.order_status === "PAYMENT_PENDING" && (
                    <Link className="pay" to={`/payment/${order.order_id}`}>결제하기</Link>
                  )}
                  {order.order_status === "DELIVERED" && (
                    <button
                      type="button"
                      className="complete-purchase-button"
                      onClick={() => confirmPurchase(order.order_id)}
                      disabled={processingOrderId === order.order_id}
                    >
                      {processingOrderId === order.order_id ? "처리 중..." : "구매완료"}
                    </button>
                  )}
                </div>
              </footer>
            </section>
          );
        })}
      </div>

      {reviewItem && (
        <div className="review-modal" onClick={() => setReviewItem(null)}>
          <form onSubmit={submitReview} onClick={(e) => e.stopPropagation()}>
            <h2>리뷰 작성</h2>
            <p>{reviewItem.product_name_snapshot}</p>
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
              <textarea required value={reviewTxt} onChange={(e) => setReviewTxt(e.target.value)} placeholder="구매한 상품의 후기를 작성해주세요." />
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

export default MyOrders;
