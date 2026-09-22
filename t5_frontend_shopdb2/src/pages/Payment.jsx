import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { approveDevPayment, getPaymentOrder } from "../api/shopApi";
import "./Payment.css";

const money = (v) => Number(v || 0).toLocaleString("ko-KR") + "원";

function Payment() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const [order, setOrder] = useState(null);
  const [method, setMethod] = useState("CARD");
  const [error, setError] = useState("");
  const [paying, setPaying] = useState(false);

  useEffect(()=>{ getPaymentOrder(orderId).then(setOrder).catch((e)=>setError(e.message)); },[orderId]);

  async function pay() {
    setPaying(true); setError("");
    try {
      const result = await approveDevPayment(Number(orderId), method);
      alert(`${result.message}\n승인금액: ${money(result.approved_amount)}`);
      navigate("/mypage/orders", { replace:true });
    } catch(err) { setError(err.message); }
    finally { setPaying(false); }
  }

  if (error && !order) return <div className="payment"><div className="shop-state shop-state--error">{error}</div></div>;
  if (!order) return <div className="shop-state">주문 정보를 불러오는 중입니다...</div>;

  return <div className="payment"><div className="shop-list-page__title"><span>PAYMENT</span><h1>결제</h1><p>학습용 개발 결제로 DB 흐름을 확인합니다.</p></div>
    {error && <div className="shop-state shop-state--error">{error}</div>}
    <div className="payment__notice"><b>개발용 결제</b><p>실제 카드번호나 계좌정보를 입력하지 않습니다. 버튼을 누르면 FastAPI가 <code>payments</code>와 <code>payment_transactions</code>에 승인 기록을 만들고 재고를 차감합니다.</p></div>
    <div className="payment__grid"><main className="payment__box"><h2>{order.order_no}</h2>{order.items.map((i)=><div className="payment__item" key={i.order_item_id}><span><b>{i.product_name_snapshot}</b><small>{i.sku_snapshot} · {i.quantity}개</small></span><strong>{money(i.item_amount)}</strong></div>)}<div className="payment__address"><h3>배송지</h3><p>{order.receiver_name} · {order.receiver_phone}</p><p>[{order.zipcode}] {order.shipping_address1} {order.shipping_address2}</p></div></main>
      <aside className="payment__box"><h2>결제 방법</h2><label><input type="radio" checked={method==="CARD"} onChange={()=>setMethod("CARD")}/> 카드(시뮬레이션)</label><label><input type="radio" checked={method==="TRANSFER"} onChange={()=>setMethod("TRANSFER")}/> 계좌이체(시뮬레이션)</label><label><input type="radio" checked={method==="EASY_PAY"} onChange={()=>setMethod("EASY_PAY")}/> 간편결제(시뮬레이션)</label><hr/><div className="payment__amount"><span>총 결제금액</span><strong>{money(order.total_amount)}</strong></div>{order.order_status==="PAYMENT_PENDING" ? <button onClick={pay} disabled={paying}>{paying?"결제 처리 중...":"개발용 결제 승인"}</button> : <p className="payment__done">현재 주문 상태: {order.order_status}</p>}<Link to="/mypage/orders">주문내역으로 돌아가기</Link></aside>
    </div>
  </div>;
}
export default Payment;
