import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import ProductDetail from "./pages/ProductDetail";
import Cart from "./pages/Cart";
import Wishlist from "./pages/Wishlist";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import MyOrders from "./pages/MyOrders";
import ForgotPassword from "./pages/ForgotPassword";
import ChangePassword from "./pages/ChangePassword";
import MyPage from "./pages/MyPage";
import MyReviews from "./pages/MyReviews";
import Checkout from "./pages/Checkout";
import Payment from "./pages/Payment";
import OrderDetail from "./pages/OrderDetail";
import AdminOrders from "./pages/AdminOrders";
import AdminCenter from "./pages/AdminCenter";
import SellerCenter from "./pages/SellerCenter";
import ProtectedRoute from "./auth/ProtectedRoute";
import RoleRoute from "./auth/RoleRoute";
import "./App.css";

const protectedPage = (component) => <ProtectedRoute>{component}</ProtectedRoute>;

function App() {
  return <Routes><Route element={<Layout />}>
    <Route path="/" element={<Home />} />
    <Route path="/products/:id" element={<ProductDetail />} />
    <Route path="/cart" element={protectedPage(<Cart />)} />
    <Route path="/wishlist" element={protectedPage(<Wishlist />)} />
    <Route path="/checkout" element={protectedPage(<Checkout />)} />
    <Route path="/payment/:orderId" element={protectedPage(<Payment />)} />
    <Route path="/mypage" element={protectedPage(<MyPage />)} />
    <Route path="/mypage/orders" element={protectedPage(<MyOrders />)} />
    <Route path="/mypage/reviews" element={protectedPage(<MyReviews />)} />
    <Route path="/mypage/orders/:orderId" element={protectedPage(<OrderDetail />)} />
    <Route path="/admin" element={<RoleRoute role="ADMIN"><AdminCenter /></RoleRoute>} />
    <Route path="/admin/orders" element={<RoleRoute role="ADMIN"><AdminOrders /></RoleRoute>} />
    <Route path="/seller" element={<RoleRoute role="SELLER"><SellerCenter /></RoleRoute>} />
    <Route path="/login" element={<Login />} />
    <Route path="/signup" element={<Signup />} />
    <Route path="/forgot-password" element={<ForgotPassword />} />
    <Route path="/mypage/password" element={protectedPage(<ChangePassword />)} />
  </Route></Routes>;
}

export default App;