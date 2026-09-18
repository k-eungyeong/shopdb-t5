import { useState } from "react";
import { Link } from "react-router-dom";
import "./Auth.css";

function Login() {
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    // TODO: 로그인 API(JWT 발급)가 아직 백엔드에 없어서 지금은 동작하지 않음
    alert("로그인 API가 아직 준비되지 않았습니다 (화면만 먼저 구현)");
  }

  return (
    <div className="auth">
      <form className="auth__form" onSubmit={handleSubmit}>
        <h1>로그인</h1>
        <input type="text" placeholder="아이디" value={loginId} onChange={(e) => setLoginId(e.target.value)} />
        <input type="password" placeholder="비밀번호" value={password} onChange={(e) => setPassword(e.target.value)} />
        <button type="submit" className="btn btn--primary">로그인</button>
        <p className="auth__switch">아직 회원이 아니신가요? <Link to="/signup">회원가입</Link></p>
      </form>
    </div>
  );
}

export default Login;