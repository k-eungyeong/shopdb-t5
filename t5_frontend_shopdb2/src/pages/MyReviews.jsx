import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { deleteMyReview, getMyReviews, updateMyReview } from "../api/shopApi";
import EmptyState from "../components/EmptyState";
import "./MyPage.css";

function MyReviews(){
  const [items,setItems]=useState([]); const [error,setError]=useState(""); const [message,setMessage]=useState("");
  const [editing,setEditing]=useState(null); const [rating,setRating]=useState(5); const [text,setText]=useState("");
  async function load(){try{const d=await getMyReviews();setItems(d.items||[]);setError("");}catch(e){setError(e.message)}}
  useEffect(()=>{load()},[]);
  function start(item){setEditing(item);setRating(Number(item.rating));setText(item.review_txt)}
  async function save(e){e.preventDefault();try{const r=await updateMyReview(editing.review_id,{rating:Number(rating),review_txt:text});setMessage(r.message);setEditing(null);await load()}catch(err){setError(err.message)}}
  async function remove(item){if(!confirm("이 리뷰를 삭제할까요?"))return;try{const r=await deleteMyReview(item.review_id);setMessage(r.message);await load()}catch(err){setError(err.message)}}
  return <div className="mypage"><div className="shop-list-page__title"><span>MY REVIEWS</span><h1>내 리뷰 관리</h1><p>내가 작성한 구매후기를 수정하거나 삭제할 수 있습니다.</p></div>
    <div className="mypage__quick"><Link to="/mypage">마이페이지</Link><Link to="/mypage/orders">주문 내역</Link></div>
    {message&&<div className="mypage__message">{message}</div>}{error&&<div className="shop-state shop-state--error">{error}</div>}
    <section className="mypage__section"><h2>작성한 리뷰 {items.length}개</h2>{items.length===0?<EmptyState icon="★" title="작성한 리뷰가 없습니다" description="배송완료된 상품을 구매하면 리뷰를 작성할 수 있어요." actionTo="/mypage/orders" actionLabel="주문 내역 보기" />:items.map(item=><article className="myreview-card" key={item.review_id}><div><Link to={`/products/${item.product_id}`}><b>{item.product_name}</b></Link><small>{item.order_no} · {String(item.added_at).slice(0,10)}</small><div className="center-review-stars">{"★".repeat(Number(item.rating))}{"☆".repeat(5-Number(item.rating))}</div><p>{item.review_txt}</p></div><div><button onClick={()=>start(item)}>수정</button><button onClick={()=>remove(item)}>삭제</button></div></article>)}</section>
    {editing&&<div className="review-modal" onClick={()=>setEditing(null)}><form onSubmit={save} onClick={e=>e.stopPropagation()}><h2>리뷰 수정</h2><p>{editing.product_name}</p><label>별점<select value={rating} onChange={e=>setRating(e.target.value)}>{[5,4,3,2,1].map(v=><option value={v} key={v}>{"★".repeat(v)}{"☆".repeat(5-v)} {v}점</option>)}</select></label><label>후기<textarea required minLength="2" value={text} onChange={e=>setText(e.target.value)}/></label><div><button type="button" onClick={()=>setEditing(null)}>취소</button><button type="submit">저장</button></div></form></div>}
  </div>
}
export default MyReviews;
