import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { deleteCart, getCart, updateCart } from "../api/shopApi";
import { money } from "../utils/format";
import ErrorState from "../components/ErrorState";
import EmptyState from "../components/EmptyState";
import { ListSkeleton } from "../components/Skeleton";
import "./ShopList.css";

function Cart() {
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  async function load() {
    try {
      const data = await getCart();
      setItems(data.items);
      // 새로 불러온 장바구니는 기본적으로 전체 선택 상태로 시작합니다.
      setSelected(new Set(data.items.map((item) => item.carts_id)));
      setError("");
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  async function change(item, next) {
    if (next < 1) return;
    try { await updateCart(item.carts_id, next); await load(); } catch (e) { setError(e.message); }
  }
  async function remove(id) {
    try { await deleteCart(id); await load(); } catch (e) { setError(e.message); }
  }

  function toggleItem(id) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }
  function toggleAll() {
    setSelected((prev) => (prev.size === items.length ? new Set() : new Set(items.map((item) => item.carts_id))));
  }

  const selectedItems = useMemo(() => items.filter((item) => selected.has(item.carts_id)), [items, selected]);
  const subtotal = selectedItems.reduce((sum, item) => sum + Number(item.sale_price) * item.quantity, 0);
  const allSelected = items.length > 0 && selected.size === items.length;

  function goCheckout() {
    if (selectedItems.length === 0) { setError("주문할 상품을 한 개 이상 선택해주세요."); return; }
    navigate("/checkout", { state: { cartIds: selectedItems.map((item) => item.carts_id) } });
  }

  return <div className="shop-list-page"><div className="shop-list-page__title"><span>CART</span><h1>장바구니</h1><p>현재 로그인한 회원의 장바구니입니다.</p></div>
    <ErrorState message={error} onRetry={load} />
    {loading ? <ListSkeleton count={3} /> : !error && items.length === 0 ? (
      <EmptyState icon="🛒" title="장바구니가 비어있습니다" description="마음에 드는 상품을 담아보세요." actionTo="/" actionLabel="상품 보러가기" />
    ) : (
      <div className="cart-layout"><div className="shop-items">
        <label className="cart-select-all"><input type="checkbox" checked={allSelected} onChange={toggleAll} /><span>전체선택 ({selected.size}/{items.length})</span></label>
        {items.map((item) => <article className={`shop-item${selected.has(item.carts_id) ? "" : " is-unselected"}`} key={item.carts_id}>
        <input type="checkbox" className="shop-item__check" checked={selected.has(item.carts_id)} onChange={() => toggleItem(item.carts_id)} aria-label={`${item.product_name} 선택`} />
        <Link to={`/products/${item.product_id}`} className="shop-item__image">{item.image ? <img src={item.image} alt={item.product_name} /> : <span>T5</span>}</Link>
        <div className="shop-item__body"><small>{item.carts_id}</small><Link to={`/products/${item.product_id}`}><h3>{item.product_name}</h3></Link><p>{[item.option_value1, item.option_value2].filter(Boolean).join(" / ")}</p><strong>{money(item.sale_price)}</strong><small>구매 가능 재고 {item.available_stock}</small></div>
        <div className="shop-item__qty"><button onClick={() => change(item, item.quantity - 1)}>−</button><b>{item.quantity}</b><button onClick={() => change(item, item.quantity + 1)}>＋</button></div>
        <div className="shop-item__end"><strong>{money(Number(item.sale_price) * item.quantity)}</strong><button className="text-btn" onClick={() => remove(item.carts_id)}>삭제</button></div>
      </article>)}</div>
      <aside className="cart-summary"><h2>결제 예정금액</h2><div><span>선택 상품</span><b>{selected.size}개</b></div><div><span>상품금액</span><b>{money(subtotal)}</b></div><div><span>배송비</span><b>주문 단계에서 계산</b></div><hr/><div className="cart-summary__total"><span>합계</span><strong>{money(subtotal)}</strong></div><button disabled={selectedItems.length === 0} onClick={goCheckout}>주문하기{selectedItems.length > 0 ? ` (${selectedItems.length})` : ""}</button></aside></div>
    )}
  </div>;
}
export default Cart;
