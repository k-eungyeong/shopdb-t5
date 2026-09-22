import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  cancelOrder,
  completeOrder,
  createReview,
  getOrderDetail,
  requestRefund,
} from "../api/shopApi";
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
const deliveryRank = { PAID: 0, PREPARING: 1, SHIPPING: 2, DELIVERED: 3, COMPLETED: 3 };

function DeliveryTracker({ status, updatedAt }) {
  const current = deliveryRank[status] ?? -1;
  const stopped = ["CANCELLED", "REFUNDED"].includes(status);

  return (
    <section className="order-shipping-box">
      <div className="delivery-tracker__title">
        <div>
          <h3>배송조회</h3>
          <p>현재 주문 상태를 이용해 배송 진행 상황을 표시합니다.</p>
        </div>
        <strong>{statusText[status] || status}</strong>
      </div>

      {stopped ? (
        <div className="delivery-tracker delivery-tracker--stopped">현재 주문 상태: {statusText[status]}</div>
      ) : (
        <div className="delivery-steps">
          {deliverySteps.map((step, index) => (
            <div className={`delivery-step ${index <= current ? "is-active" : ""}`} key={step.key}>
              <span>{index < current ? "✓" : index + 1}</span>
              <b>{step.label}</b>
            </div>
          ))}
        </div>
      )}

      <small>
        최근 상태 변경: {updatedAt ? String(updatedAt).slice(0, 19).replace("T", " ") : "-"}
        {" · "}상세 택배 이동 이력은 별도 배송 테이블/택배사 API 없이 저장되지 않습니다.
      </small>
    </section>
  );
}

function OrderDetail() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const [order, setOrder] = useState(null);
  const [error, setError] = useState("");
  const [reviewItem, setReviewItem] = useState(null);
  const [rating, setRating] = useState(5);
  const [reviewTxt, setReviewTxt] = useState("");
  const [processing, setProcessing] = useState(false);
  const [refundOpen, setRefundOpen] = useState(false);
  const [refundReason, setRefundReason] = useState("");

  async function load() {
    try {
      setOrder(await getOrderDetail(orderId));
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, [orderId]);

  async function cancel() {
    if (!window.confirm("이 주문을 취소할까요? 결제완료 주문은 개발용 결제 취소와 재고 복구도 함께 처리됩니다.")) return;
    try {
      const result = await cancelOrder(Number(orderId));
      window.alert(result.message);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function confirmPurchase() {
    if (!window.confirm("상품을 정상적으로 받으셨나요? 구매완료로 확정할까요?")) return;
    try {
      setProcessing(true);
      const result = await completeOrder(Number(orderId));
      window.alert(result.message);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setProcessing(false);
    }
  }

  async function submitRefund(e) {
    e.preventDefault();
    if (!window.confirm("이 주문 전체에 대해 환불을 신청할까요?")) return;
    try {
      setProcessing(true);
      const result = await requestRefund(Number(orderId), refundReason);
      window.alert(result.message);
      setRefundOpen(false); setRefundReason(""); await load();
    } catch (err) { setError(err.message); } finally { setProcessing(false); }
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

  if (error && !order) {
    return <div className="orders-page"><div className="shop-state shop-state--error">{error}</div></div>;
  }
  if (!order) return <div className="shop-state">주문 상세를 불러오는 중입니다...</div>;

  const canCancel = ["ORDERED", "PAYMENT_PENDING", "PAID"].includes(order.order_status);
  return (
    <div className="orders-page">
      <div className="shop-list-page__title">
        <span>ORDER DETAIL</span>
        <h1>주문 상세</h1>
        <p>{order.order_no}</p>
      </div>

      {error && <div className="shop-state shop-state--error">{error}</div>}

      <section className="order-detail-card">
        <div className="order-detail-card__head">
          <div>
            <small>{String(order.ordered_at).slice(0, 19).replace("T", " ")}</small>
            <h2>{order.order_no}</h2>
          </div>
          <strong>{statusText[order.order_status] || order.order_status}</strong>
        </div>

        <DeliveryTracker status={order.order_status} updatedAt={order.updated_at} />

        <h3>주문 상품</h3>
        {order.items.map((item) => {
          const canReview = ["DELIVERED", "COMPLETED"].includes(item.item_status);
          return (
          <div className="order-detail-item" key={item.order_item_id}>
            <div>
              <Link to={`/products/${item.product_id}`}><b>{item.product_name_snapshot}</b></Link>
              <span>{item.sku_snapshot} · {item.quantity}개 · {item.item_status}</span>
            </div>
            <strong>{money(item.item_amount)}</strong>
            <div className="order-detail-item__review">
              {item.review_id ? (
                <span className="review-done">★ {item.rating} 리뷰완료</span>
              ) : canReview ? (
                <button type="button" className="review-write-button" onClick={() => openReview(item)}>
                  리뷰 작성
                </button>
              ) : (
                <small className="review-waiting">배송완료 후 리뷰 가능</small>
              )}
            </div>
          </div>
          );
        })}

        <div className="order-detail-address">
          <h3>배송 정보</h3>
          <p>{order.receiver_name} · {order.receiver_phone}</p>
          <p>[{order.zipcode}] {order.shipping_address1} {order.shipping_address2}</p>
        </div>

        <div className="order-detail-payment">
          <h3>금액 / 결제</h3>
          <div><span>상품금액</span><b>{money(order.product_amount)}</b></div>
          <div><span>배송비</span><b>{money(order.shipping_amount)}</b></div>
          <div><span>할인</span><b>-{money(order.discount_amount)}</b></div>
          <div className="total"><span>총 금액</span><strong>{money(order.total_amount)}</strong></div>
          {order.payment && <p>결제방법: {order.payment.payment_method} · 결제상태: {order.payment.payment_status}</p>}
        </div>

        {order.refund && <div className="order-refund-status"><b>환불 신청 상태</b><span>{order.refund.refund_status}</span><p>{order.refund.refund_reason}</p></div>}

        <div className="order-detail-actions">
          <button type="button" onClick={() => navigate(-1)}>목록으로</button>
          {order.order_status === "PAYMENT_PENDING" && <Link to={`/payment/${order.order_id}`}>결제하기</Link>}
          {order.order_status === "DELIVERED" && (
            <button type="button" className="complete" onClick={confirmPurchase} disabled={processing}>
              {processing ? "처리 중..." : "구매완료"}
            </button>
          )}
          {canCancel && <button className="danger" onClick={cancel}>주문 취소</button>}
          {["DELIVERED","COMPLETED"].includes(order.order_status) && !order.refund?.refund_status?.match(/REQUESTED|REVIEWING|APPROVED|COMPLETED/) && <button className="danger" onClick={()=>setRefundOpen(true)}>환불 신청</button>}
        </div>
      </section>

      {refundOpen && (
        <div className="review-modal" onClick={()=>setRefundOpen(false)}>
          <form onSubmit={submitRefund} onClick={e=>e.stopPropagation()}>
            <h2>환불 신청</h2><p>{order.order_no}</p>
            <label>환불 사유<textarea required minLength="2" value={refundReason} onChange={e=>setRefundReason(e.target.value)} placeholder="환불 사유를 입력해주세요."/></label>
            <div><button type="button" onClick={()=>setRefundOpen(false)}>취소</button><button type="submit" disabled={processing}>환불 신청</button></div>
          </form>
        </div>
      )}

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

export default OrderDetail;
