import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { deleteWishlist, getWishlist } from "../api/shopApi";
import { money } from "../utils/format";
import ErrorState from "../components/ErrorState";
import EmptyState from "../components/EmptyState";
import { ProductGridSkeleton } from "../components/Skeleton";
import "./ShopList.css";

function Wishlist() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  async function load() { try { const d = await getWishlist(); setItems(d.items); setError(""); } catch(e) { setError(e.message); } finally { setLoading(false); } }
  useEffect(() => { load(); }, []);
  async function remove(id) { try { await deleteWishlist(id); await load(); } catch(e) { setError(e.message); } }

  return <div className="shop-list-page"><div className="shop-list-page__title"><span>WISHLIST</span><h1>찜한 상품</h1><p>현재 로그인한 회원의 관심 상품입니다.</p></div>
    <ErrorState message={error} onRetry={load} />
    {loading ? <ProductGridSkeleton count={4} /> : !error && items.length === 0 ? (
      <EmptyState icon="♡" title="찜한 상품이 없습니다" description="마음에 드는 상품을 찜해두면 여기서 모아볼 수 있어요." actionTo="/" actionLabel="상품 보러가기" />
    ) : <div className="wishlist-grid">{items.map((item) => <article className="wishlist-card" key={item.wishlist_id}><Link to={`/products/${item.product_id}`} className="wishlist-card__image">{item.image ? <img src={item.image} alt={item.product_name}/> : <span>T5 SHOP</span>}</Link><div><small>{item.product_code}</small><Link to={`/products/${item.product_id}`}><h3>{item.product_name}</h3></Link><p>{item.short_description}</p><strong>{money(item.sale_price)}</strong><button onClick={() => remove(item.wishlist_id)}>♡ 삭제</button></div></article>)}</div>}
  </div>;
}
export default Wishlist;
