import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { changePassword } from "../api/shopApi";
import "./Auth.css";

function ChangePassword() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newPassword2, setNewPassword2] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const navigate = useNavigate();

  async function submit(e) {
    e.preventDefault(); setError(""); setMessage("");
    if (newPassword !== newPassword2) return setError("새 비밀번호 확인이 일치하지 않습니다.");
    try {
      const result = await changePassword(currentPassword, newPassword);
      setMessage(result.message); setCurrentPassword(""); setNewPassword(""); setNewPassword2("");
    } catch (err) { setError(err.message); }
  }

  return <div className="auth"><form className="auth__form" onSubmit={submit}>
    <h1>비밀번호 변경</h1>
    <p className="auth__intro">로그인한 회원이 현재 비밀번호를 확인한 뒤 변경합니다.</p>
    <input type="password" placeholder="현재 비밀번호" value={currentPassword} onChange={(e)=>setCurrentPassword(e.target.value)} required />
    <input type="password" minLength={8} placeholder="새 비밀번호" value={newPassword} onChange={(e)=>setNewPassword(e.target.value)} required />
    <input type="password" minLength={8} placeholder="새 비밀번호 확인" value={newPassword2} onChange={(e)=>setNewPassword2(e.target.value)} required />
    {error && <p className="auth__error">{error}</p>}{message && <p className="auth__success">{message}</p>}
    <button className="btn btn--primary">변경하기</button>
    <button type="button" className="auth__secondary" onClick={()=>navigate(-1)}>돌아가기</button>
  </form></div>;
}
export default ChangePassword;
