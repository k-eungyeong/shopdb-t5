import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

function RoleRoute({ role, children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="shop-state">권한을 확인하는 중입니다...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (!user.roles?.includes(role)) return <Navigate to="/" replace />;
  return children;
}

export default RoleRoute;
