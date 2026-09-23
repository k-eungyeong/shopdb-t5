import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { createOrder, getAddresses, getCart } from "../api/shopApi";
import { money } from "../utils/format";
import ErrorState from "../components/ErrorState";
import EmptyState from "../components/EmptyState";
import "./Checkout.css";

function Checkout() {
  const [items, setItems] = useState([]);
  const [addresses, setAddresses] = useState([]);
  const [addressId, setAddressId] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  // 장바구니 화면에서 선택한 상품만 넘어온 경우 그 목록으로 제한합니다.
  // 없으면(주소창으로 바로 진입 등) 기존처럼 장바구니 전체를 보여줍니다.
  const cartIds = location.state?.cartIds || null;

  // 재시도 버튼에서도 다시 쓸 수 있도록 로딩 함수를 useEffect 밖으로 뺐습니다.
  async function load() {
    try {
      setError("");
      const [cart, addressData] = await Promise.all([getCart(), getAddresses()]);
      const filtered = cartIds ? cart.items.filter((i) => cartIds.includes(i.carts_id)) : cart.items;
      setItems(filtered);
      setAddresses(addressData.items);
      const first = addressData.items.find((a)=>a.default_yn==="Y") || addressData.items[0];
      if (first) setAddressId(String(first.address_id));
    } catch (err) { setError(err.message); }
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const subtotal = useMemo(() => items.reduce((sum,i)=>sum+Number(i.sale_price)*i.quantity,0),[items]);
  const shipping = subtotal >= 50000 ? 0 : 3000;

  async function submitOrder() {
    if (!addressId) return setError("배송지를 먼저 등록하거나 선택해주세요.");
    setSubmitting(true); setError("");
    try {
      const result = await createOrder(Number(addressId), items.map((i) => i.carts_id));
      navigate(`/payment/${result.order_id}`);
    } catch (err) { setError(err.message); }
    finally { setSubmitting(false); }
  }

  if (!items.length && !error) return <div className="checkout"><EmptyState icon="🧾" title="주문할 상품이 없습니다" description="장바구니에서 주문할 상품을 먼저 선택해주세요." actionTo="/cart" actionLabel="장바구니로 돌아가기" /></div>;
  if (error && !items.length) return <div className="checkout"><ErrorState message={error} onRetry={load} /></div>;

  return <div className="checkout"><div className="shop-list-page__title"><span>CHECKOUT</span><h1>주문서</h1><p>배송지와 주문 금액을 확인한 후 주문서를 생성합니다.</p></div>
    <ErrorState message={error} onRetry={load} />
    <div className="checkout__grid"><main>
      <section className="checkout__section"><div className="checkout__head"><h2>배송지</h2><Link to="/mypage">배송지 관리</Link></div>
        {addresses.length===0 ? <p>등록된 배송지가 없습니다. <Link to="/mypage">마이페이지에서 등록해주세요.</Link></p> : <div className="checkout__addresses">{addresses.map((a)=><label key={a.address_id} className={String(a.address_id)===addressId?"active":""}><input type="radio" name="address" value={a.address_id} checked={String(a.address_id)===addressId} onChange={(e)=>setAddressId(e.target.value)} /><span><b>{a.address_name || "배송지"} {a.default_yn==="Y" && "· 기본"}</b><strong>{a.receiver_name} · {a.receiver_phone}</strong><small>[{a.zipcode}] {a.address1} {a.address2}</small></span></label>)}</div>}
      </section>
      <section className="checkout__section"><h2>주문 상품 ({items.length}개)</h2>{items.map((i)=><div className="checkout__item" key={i.carts_id}><div><b>{i.product_name}</b><span>{[i.option_value1,i.option_value2].filter(Boolean).join(" / ")} · {i.quantity}개</span></div><strong>{money(Number(i.sale_price)*i.quantity)}</strong></div>)}</section>
    </main>
    <aside className="checkout__summary"><h2>최종 결제금액</h2><div><span>상품금액</span><b>{money(subtotal)}</b></div><div><span>배송비</span><b>{money(shipping)}</b></div><hr/><div className="checkout__total"><span>총 금액</span><strong>{money(subtotal+shipping)}</strong></div><button disabled={submitting || !addressId} onClick={submitOrder}>{submitting?"주문 생성 중...":"주문서 생성"}</button><small>주문서를 만든 뒤 개발용 결제 화면으로 이동합니다.</small></aside>
    </div>
  </div>;
}
export default Checkout;
