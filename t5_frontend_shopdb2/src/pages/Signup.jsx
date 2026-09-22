import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import "./Auth.css";

function Signup() {
  const [form, setForm] = useState({ login_id: "", password: "", user_name: "", email: "", phone: "" });
  const [password2, setPassword2] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { signup } = useAuth();
  const navigate = useNavigate();

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (form.password !== password2) return setError("비밀번호 확인이 일치하지 않습니다.");
    setError("");
    setSubmitting(true);
    try {
      await signup(form);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth">
      <form className="auth__form" onSubmit={handleSubmit}>
        <h1>회원가입</h1>
        <p className="auth__intro">비밀번호는 DB에 원문이 아닌 해시값으로 저장됩니다.</p>
        <input name="login_id" placeholder="아이디 (4자 이상)" value={form.login_id} onChange={handleChange} minLength={4} required />
        <input name="password" type="password" placeholder="비밀번호 (8자 이상)" value={form.password} onChange={handleChange} minLength={8} required />
        <input type="password" placeholder="비밀번호 확인" value={password2} onChange={(e) => setPassword2(e.target.value)} minLength={8} required />
        <input name="user_name" placeholder="이름" value={form.user_name} onChange={handleChange} required />
        <input name="email" type="email" placeholder="이메일" value={form.email} onChange={handleChange} required />
        <input name="phone" placeholder="전화번호" value={form.phone} onChange={handleChange} />
        {error && <p className="auth__error">{error}</p>}
        <button type="submit" className="btn btn--primary" disabled={submitting}>{submitting ? "가입 중..." : "가입하기"}</button>
        <p className="auth__switch">이미 회원이신가요? <Link to="/login">로그인</Link></p>
      </form>
    </div>
  );
}

export default Signup;
