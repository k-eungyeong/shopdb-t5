import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createOrder, getAddresses, getCart } from "../api/shopApi";
import "./Checkout.css";

const money = (v) => Number(v || 0).toLocaleString("ko-KR") + "원";

function Checkout() {
  const [items, setItems] = useState([]);
  const [addresses, setAddresses] = useState([]);
  const [addressId, setAddressId] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    async function load() {
      try {
        const [cart, addressData] = await Promise.all([getCart(), getAddresses()]);
        setItems(cart.items);
        setAddresses(addressData.items);
        const first = addressData.items.find((a)=>a.default_yn==="Y") || addressData.items[0];
        if (first) setAddressId(String(first.address_id));
      } catch (err) { setError(err.message); }
    }
    load();
  }, []);

  const subtotal = useMemo(() => items.reduce((sum,i)=>sum+Number(i.sale_price)*i.quantity,0),[items]);
  const shipping = subtotal >= 50000 ? 0 : 3000;

  async function submitOrder() {
    if (!addressId) return setError("배송지를 먼저 등록하거나 선택해주세요.");
    setSubmitting(true); setError("");
    try {
      const result = await createOrder(Number(addressId));
      navigate(`/payment/${result.order_id}`);
    } catch (err) { setError(err.message); }
    finally { setSubmitting(false); }
  }

  if (!items.length && !error) return <div className="checkout"><div className="empty-state"><h2>주문할 상품이 없습니다.</h2><Link to="/cart">장바구니로 돌아가기</Link></div></div>;

  return <div className="checkout"><div className="shop-list-page__title"><span>CHECKOUT</span><h1>주문서</h1><p>배송지와 주문 금액을 확인한 후 주문서를 생성합니다.</p></div>
    {error && <div className="shop-state shop-state--error">{error}</div>}
    <div className="checkout__grid"><main>
      <section className="checkout__section"><div className="checkout__head"><h2>배송지</h2><Link to="/mypage">배송지 관리</Link></div>
        {addresses.length===0 ? <p>등록된 배송지가 없습니다. <Link to="/mypage">마이페이지에서 등록해주세요.</Link></p> : <div className="checkout__addresses">{addresses.map((a)=><label key={a.address_id} className={String(a.address_id)===addressId?"active":""}><input type="radio" name="address" value={a.address_id} checked={String(a.address_id)===addressId} onChange={(e)=>setAddressId(e.target.value)} /><span><b>{a.address_name || "배송지"} {a.default_yn==="Y" && "· 기본"}</b><strong>{a.receiver_name} · {a.receiver_phone}</strong><small>[{a.zipcode}] {a.address1} {a.address2}</small></span></label>)}</div>}
      </section>
      <section className="checkout__section"><h2>주문 상품</h2>{items.map((i)=><div className="checkout__item" key={i.carts_id}><div><b>{i.product_name}</b><span>{[i.option_value1,i.option_value2].filter(Boolean).join(" / ")} · {i.quantity}개</span></div><strong>{money(Number(i.sale_price)*i.quantity)}</strong></div>)}</section>
    </main>
    <aside className="checkout__summary"><h2>최종 결제금액</h2><div><span>상품금액</span><b>{money(subtotal)}</b></div><div><span>배송비</span><b>{money(shipping)}</b></div><hr/><div className="checkout__total"><span>총 금액</span><strong>{money(subtotal+shipping)}</strong></div><button disabled={submitting || !addressId} onClick={submitOrder}>{submitting?"주문 생성 중...":"주문서 생성"}</button><small>주문서를 만든 뒤 개발용 결제 화면으로 이동합니다.</small></aside>
    </div>
  </div>;
}
export default Checkout;
