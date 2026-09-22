import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import "./Auth.css";

function Login() {
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const me = await login(loginId, password);
      // 역할별 기본 화면: 관리자 → 관리자센터, 판매자 → 판매자센터, 구매자 → 쇼핑몰 홈
      const next = params.get("next");
      const defaultPath = me.roles?.includes("ADMIN")
        ? "/admin"
        : me.roles?.includes("SELLER")
          ? "/seller"
          : "/";
      navigate(next || defaultPath, { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth">
      <form className="auth__form" onSubmit={handleSubmit}>
        <h1>로그인</h1>
        <p className="auth__intro">가입한 아이디와 비밀번호로 로그인하세요.</p>
        <input type="text" placeholder="아이디" value={loginId} onChange={(e) => setLoginId(e.target.value)} required />
        <input type="password" placeholder="비밀번호" value={password} onChange={(e) => setPassword(e.target.value)} required />
        {error && <p className="auth__error">{error}</p>}
        <p className="auth__forgot"><Link to="/forgot-password">비밀번호를 잊으셨나요?</Link></p>
        <button type="submit" className="btn btn--primary" disabled={submitting}>{submitting ? "로그인 중..." : "로그인"}</button>
        <p className="auth__switch">아직 회원이 아니신가요? <Link to="/signup">회원가입</Link></p>
      </form>
    </div>
  );
}

export default Login;
