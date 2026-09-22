import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createAddress, deleteAddress, getAddresses, getProfile, setDefaultAddress, updateAddress, updateProfile, withdrawMember } from "../api/shopApi";
import { useAuth } from "../auth/AuthContext";
import "./MyPage.css";

const emptyAddress = { address_name:"", receiver_name:"", receiver_phone:"", zipcode:"", address1:"", address2:"", default_yn:"N" };

function MyPage() {
  const { refreshUser, logout } = useAuth();
  const navigate = useNavigate();
  const [profile, setProfile] = useState({ user_name:"", email:"", phone:"" });
  const [addresses, setAddresses] = useState([]);
  const [addressForm, setAddressForm] = useState(emptyAddress);
  const [editingId, setEditingId] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function load() {
    try {
      const [p, a] = await Promise.all([getProfile(), getAddresses()]);
      setProfile({ user_name:p.user_name || "", email:p.email || "", phone:p.phone || "" });
      setAddresses(a.items); setError("");
    } catch (err) { setError(err.message); }
  }
  useEffect(() => { load(); }, []);

  async function saveProfile(e) {
    e.preventDefault(); setMessage(""); setError("");
    try { const r = await updateProfile(profile); await refreshUser(); setMessage(r.message); }
    catch (err) { setError(err.message); }
  }

  function startEdit(item) {
    setEditingId(item.address_id);
    setAddressForm({ address_name:item.address_name||"", receiver_name:item.receiver_name||"", receiver_phone:item.receiver_phone||"", zipcode:item.zipcode||"", address1:item.address1||"", address2:item.address2||"", default_yn:item.default_yn||"N" });
  }

  async function saveAddress(e) {
    e.preventDefault(); setError("");
    try {
      const r = editingId ? await updateAddress(editingId, addressForm) : await createAddress(addressForm);
      setMessage(r.message); setEditingId(null); setAddressForm(emptyAddress); await load();
    } catch (err) { setError(err.message); }
  }

  async function makeDefault(id) { try { const r=await setDefaultAddress(id); setMessage(r.message); await load(); } catch(err){setError(err.message);} }
  async function removeAddress(id) { if(!confirm("이 배송지를 삭제할까요?")) return; try { const r=await deleteAddress(id); setMessage(r.message); await load(); } catch(err){setError(err.message);} }

  async function withdraw() {
    if (!confirm("정말 회원 탈퇴할까요? 주문 이력은 보존되고 계정 상태만 탈퇴로 변경됩니다.")) return;
    try { await withdrawMember(); await logout(); navigate("/", { replace:true }); }
    catch (err) { setError(err.message); }
  }

  return <div className="mypage"><div className="shop-list-page__title"><span>MY PAGE</span><h1>마이페이지</h1><p>회원정보와 배송지를 관리합니다.</p></div>
    <div className="mypage__quick"><Link to="/mypage/orders">주문 내역</Link><Link to="/mypage/reviews">내 리뷰</Link><Link to="/mypage/password">비밀번호 변경</Link><Link to="/wishlist">찜 목록</Link></div>
    {message && <div className="mypage__message">{message}</div>}{error && <div className="shop-state shop-state--error">{error}</div>}

    <section className="mypage__section"><h2>내 정보</h2><form className="mypage__form" onSubmit={saveProfile}>
      <label>이름<input value={profile.user_name} onChange={(e)=>setProfile({...profile,user_name:e.target.value})} required /></label>
      <label>이메일<input type="email" value={profile.email} onChange={(e)=>setProfile({...profile,email:e.target.value})} required /></label>
      <label>전화번호<input value={profile.phone} onChange={(e)=>setProfile({...profile,phone:e.target.value})} /></label>
      <button>회원정보 저장</button>
    </form></section>

    <section className="mypage__section"><div className="mypage__section-head"><h2>배송지 관리</h2><span>{addresses.length}개</span></div>
      <div className="address-list">{addresses.map((a)=><article key={a.address_id} className="address-card"><div><b>{a.address_name || "배송지"} {a.default_yn==="Y" && <em>기본</em>}</b><strong>{a.receiver_name} · {a.receiver_phone}</strong><p>[{a.zipcode}] {a.address1} {a.address2}</p></div><div>{a.default_yn!=="Y" && <button onClick={()=>makeDefault(a.address_id)}>기본 지정</button>}<button onClick={()=>startEdit(a)}>수정</button><button onClick={()=>removeAddress(a.address_id)}>삭제</button></div></article>)}</div>
      <form className="address-form" onSubmit={saveAddress}><h3>{editingId ? "배송지 수정" : "새 배송지 등록"}</h3>
        <input placeholder="배송지 이름 (예: 집)" value={addressForm.address_name} onChange={(e)=>setAddressForm({...addressForm,address_name:e.target.value})} />
        <input placeholder="받는 사람" value={addressForm.receiver_name} onChange={(e)=>setAddressForm({...addressForm,receiver_name:e.target.value})} required />
        <input placeholder="연락처" value={addressForm.receiver_phone} onChange={(e)=>setAddressForm({...addressForm,receiver_phone:e.target.value})} required />
        <input placeholder="우편번호" value={addressForm.zipcode} onChange={(e)=>setAddressForm({...addressForm,zipcode:e.target.value})} />
        <input placeholder="주소" value={addressForm.address1} onChange={(e)=>setAddressForm({...addressForm,address1:e.target.value})} required />
        <input placeholder="상세주소" value={addressForm.address2} onChange={(e)=>setAddressForm({...addressForm,address2:e.target.value})} />
        <label className="address-form__check"><input type="checkbox" checked={addressForm.default_yn==="Y"} onChange={(e)=>setAddressForm({...addressForm,default_yn:e.target.checked?"Y":"N"})} /> 기본 배송지로 설정</label>
        <div><button>{editingId ? "수정 저장" : "배송지 등록"}</button>{editingId && <button type="button" onClick={()=>{setEditingId(null);setAddressForm(emptyAddress);}}>취소</button>}</div>
      </form>
    </section>

    <section className="mypage__danger"><h2>회원 탈퇴</h2><p>DB 행을 삭제하지 않고 <code>user_status = WITHDRAWN</code>으로 변경해 주문 이력을 보존합니다.</p><button onClick={withdraw}>회원 탈퇴</button></section>
  </div>;
}
export default MyPage;
