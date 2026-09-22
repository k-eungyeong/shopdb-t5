import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { confirmPasswordReset, requestPasswordReset, verifyPasswordReset } from "../api/shopApi";
import "./Auth.css";

function ForgotPassword() {
  const [step, setStep] = useState(1);
  const [loginId, setLoginId] = useState("");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [devCode, setDevCode] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function requestCode(e) {
    e.preventDefault(); setError(""); setMessage("");
    try {
      const result = await requestPasswordReset(loginId, email);
      setDevCode(result.dev_code || "");
      setMessage(result.delivery === "email" ? "이메일로 인증번호를 보냈습니다." : "개발 모드 인증번호가 발급되었습니다.");
      setStep(2);
    } catch (err) { setError(err.message); }
  }

  async function verifyCode(e) {
    e.preventDefault(); setError("");
    try {
      const result = await verifyPasswordReset(email, code);
      setResetToken(result.reset_token); setStep(3); setMessage("본인 확인이 완료되었습니다.");
    } catch (err) { setError(err.message); }
  }

  async function resetPassword(e) {
    e.preventDefault(); setError("");
    if (password !== password2) return setError("새 비밀번호 확인이 일치하지 않습니다.");
    try {
      const result = await confirmPasswordReset(resetToken, password);
      alert(result.message);
      navigate("/login", { replace: true });
    } catch (err) { setError(err.message); }
  }

  return <div className="auth"><div className="auth__form">
    <h1>비밀번호 재설정</h1>
    <p className="auth__intro">1. 계정 확인 → 2. 인증번호 확인 → 3. 새 비밀번호 설정</p>
    {message && <p className="auth__success">{message}</p>}
    {error && <p className="auth__error">{error}</p>}

    {step === 1 && <form onSubmit={requestCode} className="auth__inner-form">
      <input placeholder="가입한 아이디" value={loginId} onChange={(e)=>setLoginId(e.target.value)} required />
      <input type="email" placeholder="가입한 이메일" value={email} onChange={(e)=>setEmail(e.target.value)} required />
      <button className="btn btn--primary">인증번호 받기</button>
    </form>}

    {step === 2 && <form onSubmit={verifyCode} className="auth__inner-form">
      {devCode && <div className="auth__dev-code">개발 모드 인증번호: <strong>{devCode}</strong><small>SMTP를 설정하면 실제 이메일로 전송됩니다.</small></div>}
      <input inputMode="numeric" maxLength={6} placeholder="6자리 인증번호" value={code} onChange={(e)=>setCode(e.target.value.replace(/\D/g,""))} required />
      <button className="btn btn--primary">본인 확인</button>
    </form>}

    {step === 3 && <form onSubmit={resetPassword} className="auth__inner-form">
      <input type="password" minLength={8} placeholder="새 비밀번호 (8자 이상)" value={password} onChange={(e)=>setPassword(e.target.value)} required />
      <input type="password" minLength={8} placeholder="새 비밀번호 확인" value={password2} onChange={(e)=>setPassword2(e.target.value)} required />
      <button className="btn btn--primary">비밀번호 변경</button>
    </form>}
    <p className="auth__switch"><Link to="/login">로그인으로 돌아가기</Link></p>
  </div></div>;
}

export default ForgotPassword;
