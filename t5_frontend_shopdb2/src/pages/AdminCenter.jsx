import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  createAdminCategory,
  getAdminCategories,
  getAdminDashboard,
  getAdminMembers,
  getAdminPolicies,
  getAdminProducts,
  getAdminRefunds,
  getAdminReviews,
  getAdminSellers,
  updateAdminCategory,
  updateAdminMemberStatus,
  updateAdminProduct,
  updateAdminRefund,
  updateAdminSellerStatus,
  deleteAdminReview,
} from "../api/shopApi";
import { money, statusText as orderStatus } from "../utils/format";
import "./Center.css";

const dateText = (v) => String(v || "").slice(0, 10);

const tabs = [
  ["dashboard", "▦", "대시보드"], ["members", "👥", "회원 관리"], ["sellers", "🏪", "판매자 관리"],
  ["products", "📦", "전체 상품"], ["categories", "🗂", "카테고리"], ["refunds", "↩", "환불 관리"],
  ["reviews", "★", "리뷰 관리"], ["operations", "⚙", "운영 정보"],
];

function AdminCenter() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") || "dashboard";
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [keyword, setKeyword] = useState("");
  const [categoryForm, setCategoryForm] = useState({ category_name:"", parent_category_id:"", display_order:0 });

  async function load() {
    setLoading(true); setError(""); setNotice("");
    try {
      const loaders = { dashboard:getAdminDashboard, members:getAdminMembers, sellers:getAdminSellers, products:getAdminProducts, categories:getAdminCategories, refunds:getAdminRefunds, reviews:getAdminReviews, operations:getAdminPolicies };
      setData(await loaders[tab]());
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [tab]);

  const items = useMemo(() => {
    const list = data?.items || [];
    const q = keyword.trim().toLowerCase();
    if (!q) return list;
    return list.filter((item) => JSON.stringify(item).toLowerCase().includes(q));
  }, [data, keyword]);

  async function action(fn) {
    try { setError(""); const r = await fn(); setNotice(r?.message || "변경되었습니다."); await load(); }
    catch (e) { setError(e.message); }
  }

  async function addCategory(e) {
    e.preventDefault();
    await action(() => createAdminCategory({
      category_name:categoryForm.category_name,
      parent_category_id:categoryForm.parent_category_id ? Number(categoryForm.parent_category_id) : null,
      display_order:Number(categoryForm.display_order || 0),
    }));
    setCategoryForm({ category_name:"", parent_category_id:"", display_order:0 });
  }

  return <div className="center-page">
    <aside className="center-side">
      <h2>ADMIN CENTER</h2><p>쇼핑몰 전체 운영</p>
      {tabs.map(([value, icon, label]) => <button key={value} className={tab===value?"is-active":""} onClick={() => setParams({tab:value})}><span>{icon}</span>{label}</button>)}
      <Link to="/admin/orders"><span>🚚</span>주문·배송 관리</Link>
    </aside>
    <section className="center-main">
      <div className="center-title"><div><span>ADMINISTRATION</span><h1>관리자 센터</h1><p>회원, 판매자, 상품, 주문과 운영 현황을 통합 관리합니다.</p></div><button className="center-button" onClick={load}>↻ 새로고침</button></div>
      <Link className="center-shipping-link" to="/admin/orders"><div><strong>🚚 전체 주문·배송 관리</strong><br/><span>모든 회원의 결제완료·상품준비·배송중·배송완료 주문을 일괄 관리합니다.</span></div><b>바로가기 →</b></Link>
      {notice && <div className="center-notice center-notice--success">✓ {notice}</div>}
      {error && <div className="center-notice center-notice--error">{error}</div>}
      {loading ? <div className="shop-state">관리자 데이터를 불러오는 중입니다...</div> : <>
        {tab === "dashboard" && <Dashboard data={data} />}
        {tab === "members" && <Members items={items} keyword={keyword} setKeyword={setKeyword} onStatus={(id,s)=>action(()=>updateAdminMemberStatus(id,s))} />}
        {tab === "sellers" && <Sellers items={items} keyword={keyword} setKeyword={setKeyword} onStatus={(id,s)=>action(()=>updateAdminSellerStatus(id,s))} />}
        {tab === "products" && <Products items={items} categories={data?.categories} keyword={keyword} setKeyword={setKeyword} onUpdate={(id,p)=>action(()=>updateAdminProduct(id,p))} />}
        {tab === "categories" && <Categories items={items} form={categoryForm} setForm={setCategoryForm} onAdd={addCategory} onUpdate={(id,p)=>action(()=>updateAdminCategory(id,p))} />}
        {tab === "refunds" && <Refunds items={items} keyword={keyword} setKeyword={setKeyword} onUpdate={(id,status,amount)=>action(()=>updateAdminRefund(id,status,amount))} />}
        {tab === "reviews" && <AdminReviews items={items} keyword={keyword} setKeyword={setKeyword} onDelete={(id)=>action(()=>deleteAdminReview(id))} />}
        {tab === "operations" && <Operations data={data} />}
      </>}
    </section>
  </div>;
}

function Dashboard({data}) {
  const s=data?.summary||{};
  const trend=data?.sales_trend||[];
  const maxSales=Math.max(1,...trend.map(i=>Number(i.sales||0)));
  return <>
    <div className="center-grid">
      <div className="center-card"><small>오늘 결제 매출</small><strong>{money(s.today_sales)}</strong></div>
      <div className="center-card"><small>이번 달 매출</small><strong>{money(s.month_sales)}</strong></div>
      <div className="center-card"><small>오늘 주문</small><strong>{s.today_orders||0}건</strong></div>
      <div className="center-card"><small>오늘 신규 회원</small><strong>{s.today_members||0}명</strong></div>
      <div className="center-card"><small>배송중</small><strong>{s.shipping_orders||0}건</strong></div>
      <div className="center-card"><small>배송완료</small><strong>{s.delivered_orders||0}건</strong></div>
      <div className="center-card"><small>환불 처리대기</small><strong>{s.pending_refunds||0}건</strong></div>
      <div className={`center-card ${Number(s.low_stock_variants||0)>0?"center-card--warning":""}`}><small>재고 부족 옵션</small><strong>{s.low_stock_variants||0}개</strong></div>
    </div>

    <div className="center-panel">
      <h2>최근 7일 결제 매출</h2>
      <div className="center-chart" aria-label="최근 7일 매출 그래프">
        {trend.map(row=><div className="center-chart__item" key={row.label}>
          <div className="center-chart__value">{money(row.sales)}</div>
          <div className="center-chart__bar-wrap"><div className="center-chart__bar" style={{height:`${Math.max(4,Math.round(Number(row.sales||0)/maxSales*100))}%`}}/></div>
          <div className="center-chart__label">{row.label}</div>
        </div>)}
      </div>
    </div>

    {(data?.top_products||[]).length>0 && <div className="center-panel">
      <h2>판매량 TOP 10</h2>
      <div className="center-table-wrap"><table className="center-table"><thead><tr><th>순위</th><th>상품</th><th>판매자</th><th>판매수량</th><th>주문상품 매출</th></tr></thead><tbody>
        {data.top_products.map((i,idx)=><tr key={i.product_id}><td><b>{idx+1}</b></td><td>{i.product_name}</td><td>{i.seller_name}</td><td>{i.sold_quantity}개</td><td><b>{money(i.sales_amount)}</b></td></tr>)}
      </tbody></table></div>
    </div>}

    {(data?.low_stock||[]).length>0 && <div className="center-panel">
      <h2>⚠ 재고 부족 상품</h2>
      <p className="center-kicker">현재 가용재고가 안전재고 이하인 옵션입니다.</p>
      <div className="center-table-wrap"><table className="center-table"><thead><tr><th>상품</th><th>판매자</th><th>SKU</th><th>가용재고</th><th>안전재고</th></tr></thead><tbody>
        {data.low_stock.map(i=><tr key={i.variant_id}><td><b>{i.product_name}</b></td><td>{i.seller_name}</td><td>{i.sku_code}</td><td><span className="center-status center-status--red">{i.available_stock}</span></td><td>{i.safety_stock}</td></tr>)}
      </tbody></table></div>
    </div>}

    <div className="center-panel"><h2>최근 주문</h2><div className="center-table-wrap"><table className="center-table"><thead><tr><th>주문번호</th><th>구매자</th><th>상품</th><th>금액</th><th>상태</th></tr></thead><tbody>{(data?.recent_orders||[]).map(o=><tr key={o.order_id}><td><b>{o.order_no}</b><small>{dateText(o.ordered_at)}</small></td><td>{o.buyer_name}</td><td>{o.product_names}</td><td>{money(o.total_amount)}</td><td><span className="center-status">{orderStatus[o.order_status]||o.order_status}</span></td></tr>)}</tbody></table></div></div>
  </>;
}

function Search({keyword,setKeyword,placeholder}) { return <div className="center-toolbar"><input value={keyword} onChange={e=>setKeyword(e.target.value)} placeholder={placeholder}/><span className="center-kicker">검색 결과를 실시간으로 좁힙니다.</span></div>; }
function Members({items,keyword,setKeyword,onStatus}) { return <div className="center-panel"><h2>회원 관리</h2><Search keyword={keyword} setKeyword={setKeyword} placeholder="아이디, 이름, 이메일 검색"/><div className="center-table-wrap"><table className="center-table"><thead><tr><th>회원</th><th>역할</th><th>주문</th><th>구매금액</th><th>가입일</th><th>상태</th><th>변경</th></tr></thead><tbody>{items.map(m=><tr key={m.user_id}><td><b>{m.user_name}</b><small>{m.login_id} · {m.email}</small></td><td>{(m.roles||[]).join(", ")}</td><td>{m.order_count||0}건</td><td>{money(m.purchase_total)}</td><td>{dateText(m.created_at)}</td><td><span className="center-status">{m.user_status}</span></td><td><select value={m.user_status} onChange={e=>onStatus(m.user_id,e.target.value)}><option>ACTIVE</option><option>INACTIVE</option><option>SUSPENDED</option><option>WITHDRAWN</option></select></td></tr>)}</tbody></table></div></div>; }
function Sellers({items,keyword,setKeyword,onStatus}) { return <div className="center-panel"><h2>입점 판매자 관리</h2><Search keyword={keyword} setKeyword={setKeyword} placeholder="업체명, 판매자, 사업자번호 검색"/><div className="center-table-wrap"><table className="center-table"><thead><tr><th>업체</th><th>판매자</th><th>상품수</th><th>판매완료 매출</th><th>상태</th><th>승인/제한</th></tr></thead><tbody>{items.map(s=><tr key={s.seller_id}><td><b>{s.company_name}</b><small>{s.business_number||"사업자번호 없음"}</small></td><td>{s.user_name}<small>{s.login_id} · {s.email}</small></td><td>{s.product_count}</td><td>{money(s.completed_sales)}</td><td><span className="center-status">{s.seller_status}</span></td><td><select value={s.seller_status} onChange={e=>onStatus(s.seller_id,e.target.value)}><option>ACTIVE</option><option>INACTIVE</option><option>SUSPENDED</option><option>PENDING</option></select></td></tr>)}</tbody></table></div></div>; }
function Products({items,keyword,setKeyword,onUpdate}) { return <div className="center-panel"><h2>전체 상품 검수</h2><Search keyword={keyword} setKeyword={setKeyword} placeholder="상품명, 코드, 판매자 검색"/><div className="center-table-wrap"><table className="center-table"><thead><tr><th>상품</th><th>판매자</th><th>카테고리</th><th>가격</th><th>재고</th><th>상태</th></tr></thead><tbody>{items.map(p=><tr key={p.product_id}><td><b>{p.product_name}</b><small>{p.product_code}</small></td><td>{p.seller_name}</td><td>{p.category_name}</td><td>{money(p.sale_price)}<small>정상가 {money(p.regular_price)}</small></td><td>{p.available_stock}</td><td><select value={p.product_status} onChange={e=>onUpdate(p.product_id,{product_status:e.target.value})}><option>READY</option><option>SALE</option><option>SOLD_OUT</option><option>STOPPED</option></select></td></tr>)}</tbody></table></div></div>; }
function Categories({items,form,setForm,onAdd,onUpdate}) { return <><div className="center-panel"><h2>카테고리 추가</h2><form className="center-form" onSubmit={onAdd}><label>카테고리명<input required value={form.category_name} onChange={e=>setForm({...form,category_name:e.target.value})}/></label><label>상위 카테고리<select value={form.parent_category_id} onChange={e=>setForm({...form,parent_category_id:e.target.value})}><option value="">최상위</option>{items.map(c=><option value={c.category_id} key={c.category_id}>{c.category_name}</option>)}</select></label><label>표시 순서<input type="number" value={form.display_order} onChange={e=>setForm({...form,display_order:e.target.value})}/></label><div className="center-form-actions"><button className="center-button center-button--primary">카테고리 등록</button></div></form></div><div className="center-panel"><h2>카테고리 구조</h2><div className="center-table-wrap"><table className="center-table"><thead><tr><th>이름</th><th>상위</th><th>단계</th><th>상품</th><th>순서</th><th>사용</th></tr></thead><tbody>{items.map(c=><tr key={c.category_id}><td><b>{c.category_name}</b></td><td>{c.parent_name||"-"}</td><td>{c.category_level}</td><td>{c.product_count}</td><td><input type="number" defaultValue={c.display_order} onBlur={e=>onUpdate(c.category_id,{display_order:Number(e.target.value)})}/></td><td><select value={c.active_yn} onChange={e=>onUpdate(c.category_id,{active_yn:e.target.value})}><option>Y</option><option>N</option></select></td></tr>)}</tbody></table></div></div></>; }
function Operations({data}) { return <><div className="center-panel"><h2>사이트 운영 정보</h2><div className="center-warning">현재 DB에는 별도 배너/공지/배송비 정책 테이블이 없으므로 테이블을 추가하지 않는 조건에 맞춰 기존 운영정책과 실제 결제수단을 조회합니다.</div><h3>사용 중인 결제수단</h3>{(data?.payment_methods||[]).map(m=><span className="center-status" key={m.payment_method} style={{marginRight:8}}>{m.payment_method} · {m.use_count}건</span>)}</div><div className="center-panel"><h2>회사 정책</h2><div className="center-table-wrap"><table className="center-table"><thead><tr><th>정책</th><th>유형</th><th>버전</th><th>적용기간</th><th>상태</th></tr></thead><tbody>{(data?.policies||[]).map(p=><tr key={p.policy_id}><td><b>{p.policy_name}</b><small>{p.org_name||"전체"}</small></td><td>{p.policy_type}</td><td>{p.policy_version}</td><td>{dateText(p.effective_from)} ~ {p.effective_to?dateText(p.effective_to):"현재"}</td><td>{p.active_yn}</td></tr>)}</tbody></table></div></div></>; }


function Refunds({items,keyword,setKeyword,onUpdate}) {
  return <div className="center-panel"><h2>환불 관리</h2><Search keyword={keyword} setKeyword={setKeyword} placeholder="주문번호, 구매자, 상품, 환불사유 검색"/>
    <div className="center-table-wrap"><table className="center-table"><thead><tr><th>신청</th><th>주문/구매자</th><th>상품</th><th>사유</th><th>금액</th><th>상태</th><th>처리</th></tr></thead><tbody>
      {items.map(r=><tr key={r.refund_request_id}><td>{dateText(r.requested_at)}</td><td><b>{r.order_no}</b><small>{r.buyer_name} · {r.buyer_login_id}</small></td><td>{r.product_names}</td><td>{r.refund_reason}</td><td>{money(r.requested_amount)}</td><td><span className="center-status">{r.refund_status}</span></td><td>{["REJECTED","COMPLETED"].includes(r.refund_status)?<small>처리 종료</small>:<div className="center-actions-inline"><button onClick={()=>onUpdate(r.refund_request_id,"REVIEWING")}>검토중</button><button onClick={()=>onUpdate(r.refund_request_id,"APPROVED",Number(r.requested_amount))}>승인</button><button onClick={()=>window.confirm("환불을 완료 처리하고 재고를 복구할까요?")&&onUpdate(r.refund_request_id,"COMPLETED",Number(r.approved_amount||r.requested_amount))}>완료</button><button className="danger" onClick={()=>window.confirm("환불 요청을 거절할까요?")&&onUpdate(r.refund_request_id,"REJECTED")}>거절</button></div>}</td></tr>)}
    </tbody></table></div></div>;
}

function AdminReviews({items,keyword,setKeyword,onDelete}) {
  return <div className="center-panel"><h2>구매 리뷰 관리</h2><Search keyword={keyword} setKeyword={setKeyword} placeholder="상품, 구매자, 판매자, 리뷰 내용 검색"/>
    <div className="center-table-wrap"><table className="center-table"><thead><tr><th>상품</th><th>구매자</th><th>판매자</th><th>별점</th><th>리뷰</th><th>작성일</th><th>관리</th></tr></thead><tbody>
      {items.map(r=><tr key={r.review_id}><td><b>{r.product_name}</b></td><td>{r.buyer_name}<small>{r.buyer_login_id}</small></td><td>{r.seller_name}</td><td><span className="center-review-stars">{"★".repeat(Number(r.rating||0))}</span></td><td>{r.review_txt}</td><td>{dateText(r.added_at)}</td><td><button className="center-button center-button--danger" onClick={()=>window.confirm("부적절한 리뷰를 삭제할까요?")&&onDelete(r.review_id)}>삭제</button></td></tr>)}
    </tbody></table></div></div>;
}

export default AdminCenter;
