import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import ProductCard from "../components/ProductCard";
import { getCategories, getProducts } from "../api/shopApi";
import "./Home.css";

function Home() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const keyword = searchParams.get("q") || "";
  const categoryId = searchParams.get("category") || "";
  const view = searchParams.get("view") || "";
  const sort = searchParams.get("sort") || (view === "stock" ? "stock" : view === "reviews" ? "reviews" : "latest");
  const page = Number(searchParams.get("page") || 1);
  const minPrice = searchParams.get("minPrice") || "";
  const maxPrice = searchParams.get("maxPrice") || "";
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [meta, setMeta] = useState({ total:0, total_pages:1 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [quickMenuOpen, setQuickMenuOpen] = useState(false);
  const [priceForm, setPriceForm] = useState({ min:minPrice, max:maxPrice });

  useEffect(() => {
    async function load() {
      setLoading(true); setError("");
      try {
        const [productData, categoryData] = await Promise.all([
          getProducts({ keyword, categoryId, sort, page, pageSize:12, minPrice, maxPrice }),
          getCategories(),
        ]);
        setProducts(productData.items);
        setMeta(productData);
        setCategories(categoryData.items.filter((c) => c.category_level === 2));
      } catch (err) { setError(err.message); }
      finally { setLoading(false); }
    }
    load();
  }, [keyword, categoryId, sort, page, minPrice, maxPrice]);

  const sectionTitle = keyword ? `“${keyword}” 검색 결과` : view === "stock" ? "실시간 재고 확인" : view === "reviews" ? "구매 리뷰 많은 상품" : "추천 상품";

  function updateParams(values, resetPage=true) {
    const next = new URLSearchParams(searchParams);
    Object.entries(values).forEach(([key,value]) => {
      if (value === "" || value == null) next.delete(key); else next.set(key,String(value));
    });
    if (resetPage) next.set("page","1");
    setSearchParams(next);
  }
  function selectCategory(id){ updateParams({category:id}); }
  function scrollToProducts(){ window.setTimeout(()=>document.getElementById("products")?.scrollIntoView({behavior:"smooth",block:"start"}),50); }
  function openProductView(nextView){
    const nextSort=nextView==="stock"?"stock":"reviews";
    updateParams({view:nextView,sort:nextSort}); setQuickMenuOpen(false); scrollToProducts();
  }
  function openOrders(){ setQuickMenuOpen(false); navigate("/mypage/orders"); }
  function applyPrice(e){ e.preventDefault(); updateParams({minPrice:priceForm.min,maxPrice:priceForm.max}); }

  return <div className="home">
    <section className="home__banner"><div className="home__banner-copy"><span className="home__eyebrow">T5 SMART SHOPPING</span><h1>필요한 상품을<br/><strong>더 빠르고 똑똑하게.</strong></h1><p>실제 MySQL 상품·재고·리뷰 데이터를 FastAPI로 연결한 쇼핑몰입니다.</p><button onClick={()=>document.getElementById("products")?.scrollIntoView({behavior:"smooth"})}>상품 둘러보기 →</button></div><div className="home__hero-card"><span>NEW</span><div>AI · DIGITAL<br/>LIFESTYLE</div><small>2026 COLLECTION</small></div></section>

    <section className="home__benefit-area" aria-label="쇼핑 주요 기능"><div className="home__benefits">
      <button type="button" className="home__benefit-card" onClick={openOrders}><b>🚚</b><span><strong>빠른 배송</strong><small>주문 상태를 한눈에</small></span><em>›</em></button>
      <button type="button" className={`home__benefit-card ${view==="stock"?"is-active":""}`} onClick={()=>openProductView("stock")}><b>✓</b><span><strong>실시간 재고</strong><small>DB 재고 수량 연동</small></span><em>›</em></button>
      <button type="button" className={`home__benefit-card ${view==="reviews"?"is-active":""}`} onClick={()=>openProductView("reviews")}><b>★</b><span><strong>구매 리뷰</strong><small>리뷰 많은 상품 보기</small></span><em>›</em></button>
      <button type="button" className={`home__benefit-card ${quickMenuOpen?"is-active":""}`} onClick={()=>setQuickMenuOpen(v=>!v)}><b>♡</b><span><strong>찜 & 장바구니</strong><small>원하는 상품을 저장</small></span><em>{quickMenuOpen?"×":"›"}</em></button>
    </div>{quickMenuOpen&&<div className="home__quick-menu"><div><strong>어디로 이동할까요?</strong><small>저장한 상품 또는 장바구니를 바로 확인할 수 있습니다.</small></div><button onClick={()=>navigate("/wishlist")}>♡ 찜 목록 보기</button><button onClick={()=>navigate("/cart")}>🛒 장바구니 보기</button></div>}</section>

    <section className="home__products" id="products">
      <div className="home__section-head"><div><span>SHOP</span><h2>{sectionTitle}</h2></div><p>총 {meta.total||0}개의 상품</p></div>
      <div className="home__shop-tools">
        <div className="home__filters"><button className={!categoryId?"active":""} onClick={()=>selectCategory("")}>전체</button>{categories.map(c=><button key={c.category_id} className={String(c.category_id)===categoryId?"active":""} onClick={()=>selectCategory(c.category_id)}>{c.category_name}</button>)}</div>
        <div className="home__sort"><label>정렬 <select value={sort} onChange={e=>updateParams({sort:e.target.value,view:""})}><option value="latest">최신순</option><option value="sales">판매량순</option><option value="rating">평점순</option><option value="reviews">리뷰많은순</option><option value="price_low">가격낮은순</option><option value="price_high">가격높은순</option><option value="stock">재고많은순</option></select></label></div>
      </div>
      <form className="home__price-filter" onSubmit={applyPrice}><span>가격</span><input type="number" min="0" placeholder="최소 금액" value={priceForm.min} onChange={e=>setPriceForm({...priceForm,min:e.target.value})}/><span>~</span><input type="number" min="0" placeholder="최대 금액" value={priceForm.max} onChange={e=>setPriceForm({...priceForm,max:e.target.value})}/><button>적용</button>{(minPrice||maxPrice)&&<button type="button" onClick={()=>{setPriceForm({min:"",max:""});updateParams({minPrice:"",maxPrice:""})}}>초기화</button>}</form>
      {loading&&<div className="shop-state">상품을 불러오는 중입니다...</div>}
      {error&&<div className="shop-state shop-state--error">{error}<br/><small>FastAPI 서버가 127.0.0.1:8000에서 실행 중인지 확인해주세요.</small></div>}
      {!loading&&!error&&products.length===0&&<div className="shop-state">조건에 맞는 상품이 없습니다.</div>}
      {!loading&&!error&&products.length>0&&<div className="home__grid">{products.map(product=><ProductCard key={product.product_id} product={product}/>)}</div>}
      {!loading&&!error&&Number(meta.total_pages||1)>1&&<div className="home__pagination"><button disabled={page<=1} onClick={()=>updateParams({page:page-1},false)}>‹ 이전</button><span>{page} / {meta.total_pages}</span><button disabled={page>=meta.total_pages} onClick={()=>updateParams({page:page+1},false)}>다음 ›</button></div>}
    </section>
  </div>;
}
export default Home;
