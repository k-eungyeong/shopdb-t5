import { createContext, useContext, useEffect, useState } from "react";
import { clearToken, getMe, getToken, login as loginApi, logoutApi, saveToken, signup as signupApi } from "../api/shopApi";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function restoreLogin() {
      if (!getToken()) {
        setLoading(false);
        return;
      }
      try {
        // 새로고침했을 때 토큰이 유효한지 서버에 확인합니다.
        // /auth/me 응답에는 현재 회원의 roles도 포함됩니다.
        const me = await getMe();
        setUser(me);
      } catch {
        clearToken();
        setUser(null);
      } finally {
        setLoading(false);
      }
    }
    restoreLogin();
  }, []);

  async function login(loginId, password) {
    const result = await loginApi({ login_id: loginId, password });
    saveToken(result.access_token);

    // 로그인 API의 간단한 user 정보만 사용하지 않고 /auth/me를 다시 조회합니다.
    // 이렇게 해야 로그인 직후에도 ADMIN / BUYER / SELLER 역할이 즉시 화면에 반영됩니다.
    const me = await getMe();
    setUser(me);
    return me;
  }

  async function signup(form) {
    const result = await signupApi(form);
    saveToken(result.access_token);

    // 신규 회원도 실제 권한(BUYER 등)을 서버에서 다시 읽어옵니다.
    const me = await getMe();
    setUser(me);
    return me;
  }

  async function logout() {
    try {
      if (getToken()) await logoutApi();
    } catch (error) {
      // 서버 로그아웃 요청이 실패해도 브라우저의 토큰은 반드시 제거합니다.
      console.warn("서버 로그아웃 요청은 실패했지만 로컬 로그인 정보는 제거합니다.", error);
    } finally {
      clearToken();
      setUser(null);
    }
  }

  async function refreshUser() {
    const me = await getMe();
    setUser(me);
    return me;
  }

  return <AuthContext.Provider value={{ user, loading, login, signup, logout, refreshUser }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth는 AuthProvider 안에서 사용해야 합니다.");
  return context;
}
