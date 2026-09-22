import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { deleteCart, getCart, updateCart } from "../api/shopApi";
import "./ShopList.css";

const money = (v) => Number(v || 0).toLocaleString("ko-KR") + "원";

function Cart() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function load() {
    try { const data = await getCart(); setItems(data.items); setError(""); }
    catch (e) { setError(e.message); }
  }
  useEffect(() => { load(); }, []);

  async function change(item, next) {
    if (next < 1) return;
    try { await updateCart(item.carts_id, next); await load(); } catch (e) { setError(e.message); }
  }
  async function remove(id) { try { await deleteCart(id); await load(); } catch (e) { setError(e.message); } }

  const subtotal = items.reduce((sum, item) => sum + Number(item.sale_price) * item.quantity, 0);

  return <div className="shop-list-page"><div className="shop-list-page__title"><span>CART</span><h1>장바구니</h1><p>현재 로그인한 회원의 장바구니입니다.</p></div>
    {error && <div className="shop-state shop-state--error">{error}</div>}
    {!error && items.length === 0 ? <div className="empty-state"><h2>장바구니가 비어있습니다</h2><Link to="/">상품 보러가기</Link></div> : (
      <div className="cart-layout"><div className="shop-items">{items.map((item) => <article className="shop-item" key={item.carts_id}>
        <Link to={`/products/${item.product_id}`} className="shop-item__image">{item.image ? <img src={item.image} alt={item.product_name} /> : <span>T5</span>}</Link>
        <div className="shop-item__body"><small>{item.carts_id}</small><Link to={`/products/${item.product_id}`}><h3>{item.product_name}</h3></Link><p>{[item.option_value1, item.option_value2].filter(Boolean).join(" / ")}</p><strong>{money(item.sale_price)}</strong><small>구매 가능 재고 {item.available_stock}</small></div>
        <div className="shop-item__qty"><button onClick={() => change(item, item.quantity - 1)}>−</button><b>{item.quantity}</b><button onClick={() => change(item, item.quantity + 1)}>＋</button></div>
        <div className="shop-item__end"><strong>{money(Number(item.sale_price) * item.quantity)}</strong><button className="text-btn" onClick={() => remove(item.carts_id)}>삭제</button></div>
      </article>)}</div>
      <aside className="cart-summary"><h2>결제 예정금액</h2><div><span>상품금액</span><b>{money(subtotal)}</b></div><div><span>배송비</span><b>주문 단계에서 계산</b></div><hr/><div className="cart-summary__total"><span>합계</span><strong>{money(subtotal)}</strong></div><button onClick={() => navigate("/checkout")}>주문하기</button></aside></div>
    )}
  </div>;
}
export default Cart;
