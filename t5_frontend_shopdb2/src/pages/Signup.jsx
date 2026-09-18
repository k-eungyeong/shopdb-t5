import { useState } from "react";
import { Link } from "react-router-dom";
import "./Auth.css";

function Signup() {
  const [form, setForm] = useState({ loginId: "", password: "", userName: "", email: "", phone: "" });

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  function handleSubmit(e) {
    e.preventDefault();
    // TODO: 회원가입 API가 준비되면 여기서 POST 요청으로 users 테이블에 등록
    alert("회원가입 API가 아직 준비되지 않았습니다 (화면만 먼저 구현)");
  }

  return (
    <div className="auth">
      <form className="auth__form" onSubmit={handleSubmit}>
        <h1>회원가입</h1>
        <input name="loginId" placeholder="아이디" value={form.loginId} onChange={handleChange} />
        <input name="password" type="password" placeholder="비밀번호" value={form.password} onChange={handleChange} />
        <input name="userName" placeholder="이름" value={form.userName} onChange={handleChange} />
        <input name="email" type="email" placeholder="이메일" value={form.email} onChange={handleChange} />
        <input name="phone" placeholder="전화번호" value={form.phone} onChange={handleChange} />
        <button type="submit" className="btn btn--primary">가입하기</button>
        <p className="auth__switch">이미 회원이신가요? <Link to="/login">로그인</Link></p>
      </form>
    </div>
  );
}

export default Signup;