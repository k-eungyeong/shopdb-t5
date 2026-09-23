const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const TOKEN_KEY = "t5_access_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function saveToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function normalizeImage(url) {
  if (!url) return null;
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return `${API_URL}${url.startsWith("/") ? "" : "/"}${url}`;
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  let response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    // 서버가 꺼져있거나 네트워크가 끊긴 경우 fetch 자체가 예외를 던집니다.
    // "Failed to fetch" 같은 개발자용 문구를 그대로 보여주지 않고, 사용자가 이해할 수 있는 메시지로 바꿉니다.
    const networkError = new Error("서버에 연결할 수 없습니다. 인터넷 연결을 확인하거나 잠시 후 다시 시도해주세요.");
    networkError.isNetworkError = true;
    throw networkError;
  }

  if (!response.ok) {
    let message = "요청 처리 중 오류가 발생했습니다.";
    try {
      const body = await response.json();
      message = body.detail || body.message || message;
    } catch {
      // JSON이 아닌 오류 응답은 기본 메시지를 사용합니다.
    }
    const httpError = new Error(message);
    httpError.status = response.status;
    throw httpError;
  }

  if (response.status === 204) return null;
  return response.json();
}

function withImage(item) {
  return { ...item, image: normalizeImage(item.image) };
}

// -------------------- 회원 / 로그인 --------------------
export async function signup(payload) {
  return request("/auth/signup", { method: "POST", body: JSON.stringify(payload) });
}

export async function login(payload) {
  return request("/auth/login", { method: "POST", body: JSON.stringify(payload) });
}

export async function logoutApi() {
  return request("/auth/logout", { method: "POST" });
}

export async function getMe() {
  return request("/auth/me");
}

// -------------------- 상품 --------------------
export async function getProducts({ keyword = "", categoryId = "", sort = "latest", page = 1, pageSize = 12, minPrice = "", maxPrice = "" } = {}) {
  const params = new URLSearchParams();
  if (keyword) params.set("keyword", keyword);
  if (categoryId) params.set("category_id", categoryId);
  if (sort) params.set("sort", sort);
  if (page) params.set("page", String(page));
  if (pageSize) params.set("page_size", String(pageSize));
  if (minPrice !== "") params.set("min_price", String(minPrice));
  if (maxPrice !== "") params.set("max_price", String(maxPrice));
  const data = await request(`/products${params.toString() ? `?${params}` : ""}`);
  return { ...data, items: data.items.map(withImage) };
}

export async function getCategories() {
  return request("/products/categories");
}

export async function getProduct(productId) {
  const data = await request(`/products/${productId}`);
  return withImage(data);
}

// -------------------- 장바구니 --------------------
// user_id를 프론트에서 보내지 않습니다. FastAPI가 JWT에서 현재 회원을 확인합니다.
export async function addToCart({ productId, variantId, quantity = 1 }) {
  return request("/cart", {
    method: "POST",
    body: JSON.stringify({ product_id: productId, variant_id: variantId, quantity }),
  });
}

export async function getCart() {
  const data = await request("/cart");
  return { ...data, items: data.items.map(withImage) };
}

export async function updateCart(cartsId, quantity) {
  return request(`/cart/${cartsId}`, { method: "PATCH", body: JSON.stringify({ quantity }) });
}

export async function deleteCart(cartsId) {
  return request(`/cart/${cartsId}`, { method: "DELETE" });
}

// -------------------- 찜 --------------------
export async function addWishlist(productId) {
  return request("/wishlist", { method: "POST", body: JSON.stringify({ product_id: productId }) });
}

export async function getWishlist() {
  const data = await request("/wishlist");
  return { ...data, items: data.items.map(withImage) };
}

export async function checkWishlist(productId) {
  return request(`/wishlist/check?product_id=${productId}`);
}

export async function deleteWishlist(wishlistId) {
  return request(`/wishlist/${wishlistId}`, { method: "DELETE" });
}

// -------------------- 주문 / 리뷰 --------------------
export async function getOrders() {
  return request("/orders");
}

export async function createReview(payload) {
  return request("/reviews", { method: "POST", body: JSON.stringify(payload) });
}
export async function getMyReviews() { return request("/reviews/mine"); }
export async function updateMyReview(reviewId, payload) {
  return request(`/reviews/${encodeURIComponent(reviewId)}`, { method: "PATCH", body: JSON.stringify(payload) });
}
export async function deleteMyReview(reviewId) {
  return request(`/reviews/${encodeURIComponent(reviewId)}`, { method: "DELETE" });
}


// 상품 상세 화면에서 현재 로그인 회원이 이 상품의 리뷰를 쓸 수 있는지 확인합니다.
// FastAPI는 JWT의 user_id와 실제 주문 내역을 함께 검사합니다.
export async function getReviewEligibility(productId) {
  return request(`/reviews/eligibility/${productId}`);
}

// -------------------- 비밀번호 --------------------
export async function requestPasswordReset(loginId, email) {
  return request("/auth/password-reset/request", {
    method: "POST",
    body: JSON.stringify({ login_id: loginId, email }),
  });
}

export async function verifyPasswordReset(email, code) {
  return request("/auth/password-reset/verify", {
    method: "POST",
    body: JSON.stringify({ email, code }),
  });
}

export async function confirmPasswordReset(resetToken, newPassword) {
  return request("/auth/password-reset/confirm", {
    method: "POST",
    body: JSON.stringify({ reset_token: resetToken, new_password: newPassword }),
  });
}

export async function changePassword(currentPassword, newPassword) {
  return request("/auth/password", {
    method: "PATCH",
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
}

// -------------------- 마이페이지 / 배송지 --------------------
export async function getProfile() { return request("/mypage/profile"); }
export async function updateProfile(payload) {
  return request("/mypage/profile", { method: "PATCH", body: JSON.stringify(payload) });
}
export async function getAddresses() { return request("/mypage/addresses"); }
export async function createAddress(payload) {
  return request("/mypage/addresses", { method: "POST", body: JSON.stringify(payload) });
}
export async function updateAddress(addressId, payload) {
  return request(`/mypage/addresses/${addressId}`, { method: "PATCH", body: JSON.stringify(payload) });
}
export async function setDefaultAddress(addressId) {
  return request(`/mypage/addresses/${addressId}/default`, { method: "PATCH" });
}
export async function deleteAddress(addressId) {
  return request(`/mypage/addresses/${addressId}`, { method: "DELETE" });
}
export async function withdrawMember() { return request("/mypage/withdraw", { method: "PATCH" }); }

export async function createOrder(addressId, cartIds) {
  const body = { address_id: addressId };
  if (Array.isArray(cartIds) && cartIds.length) body.cart_ids = cartIds;
  return request("/orders", { method: "POST", body: JSON.stringify(body) });
}

// -------------------- 개발용 결제 --------------------
export async function getPaymentOrder(orderId) { return request(`/payments/order/${orderId}`); }
export async function approveDevPayment(orderId, paymentMethod) {
  return request("/payments/dev-approve", {
    method: "POST",
    body: JSON.stringify({ order_id: orderId, payment_method: paymentMethod }),
  });
}

// -------------------- 주문 상세 / 취소 --------------------
export async function getOrderDetail(orderId) { return request(`/orders/${orderId}`); }
export async function cancelOrder(orderId) { return request(`/orders/${orderId}/cancel`, { method: "POST" }); }

export async function requestRefund(orderId, refundReason) {
  return request(`/orders/${orderId}/refund`, { method: "POST", body: JSON.stringify({ refund_reason: refundReason }) });
}

// 배송완료 주문을 고객이 직접 구매완료 상태로 확정합니다.
export async function completeOrder(orderId) {
  return request(`/orders/${orderId}/complete`, { method: "POST" });
}

// -------------------- 관리자 주문 / 배송 관리 --------------------
export async function getAdminOrders() {
  return request("/admin/orders");
}

export async function updateAdminShippingStatus(orderId, status) {
  return request(`/admin/orders/${orderId}/shipping-status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

// 관리자 화면에서 여러 주문의 배송 상태를 한 번에 변경합니다.
export async function bulkUpdateAdminShippingStatus(orderIds, status) {
  return request("/admin/orders/bulk-shipping-status", {
    method: "PATCH",
    body: JSON.stringify({ order_ids: orderIds, status }),
  });
}

export async function correctAdminDeliveredToShipping(orderId) {
  return request(`/admin/orders/${orderId}/correct-to-shipping`, { method: "PATCH" });
}

// -------------------- 관리자 센터 --------------------
export async function getAdminDashboard() { return request("/admin/dashboard"); }
export async function getAdminMembers() { return request("/admin/members"); }
export async function updateAdminMemberStatus(userId, userStatus) {
  return request(`/admin/members/${userId}/status`, { method: "PATCH", body: JSON.stringify({ user_status: userStatus }) });
}
export async function getAdminSellers() { return request("/admin/sellers"); }
export async function updateAdminSellerStatus(sellerId, sellerStatus) {
  return request(`/admin/sellers/${sellerId}/status`, { method: "PATCH", body: JSON.stringify({ seller_status: sellerStatus }) });
}
export async function getAdminProducts() { return request("/admin/products"); }
export async function updateAdminProduct(productId, payload) {
  return request(`/admin/products/${productId}`, { method: "PATCH", body: JSON.stringify(payload) });
}
export async function getAdminCategories() { return request("/admin/categories"); }
export async function createAdminCategory(payload) {
  return request("/admin/categories", { method: "POST", body: JSON.stringify(payload) });
}
export async function updateAdminCategory(categoryId, payload) {
  return request(`/admin/categories/${categoryId}`, { method: "PATCH", body: JSON.stringify(payload) });
}
export async function getAdminPolicies() { return request("/admin/policies"); }

export async function getAdminRefunds() { return request("/admin/refunds"); }
export async function updateAdminRefund(refundRequestId, refundStatus, approvedAmount = null) {
  return request(`/admin/refunds/${refundRequestId}`, { method: "PATCH", body: JSON.stringify({ refund_status: refundStatus, approved_amount: approvedAmount }) });
}
export async function getAdminReviews() { return request("/admin/reviews"); }
export async function deleteAdminReview(reviewId) { return request(`/admin/reviews/${encodeURIComponent(reviewId)}`, { method: "DELETE" }); }

// -------------------- 판매자 센터 --------------------
export async function getSellerDashboard() { return request("/seller/dashboard"); }
export async function getSellerProducts() { return request("/seller/products"); }
export async function createSellerProduct(payload) {
  return request("/seller/products", { method: "POST", body: JSON.stringify(payload) });
}
export async function updateSellerProduct(productId, payload) {
  return request(`/seller/products/${productId}`, { method: "PATCH", body: JSON.stringify(payload) });
}
export async function deleteSellerProduct(productId) {
  return request(`/seller/products/${productId}`, { method: "DELETE" });
}
export async function createSellerVariant(productId, payload) {
  return request(`/seller/products/${productId}/variants`, { method: "POST", body: JSON.stringify(payload) });
}
export async function updateSellerVariant(variantId, payload) {
  return request(`/seller/variants/${variantId}`, { method: "PATCH", body: JSON.stringify(payload) });
}
export async function getSellerOrders() { return request("/seller/orders"); }
export async function updateSellerShippingStatus(orderId, status) {
  return request(`/seller/orders/${orderId}/shipping-status`, { method: "PATCH", body: JSON.stringify({ status }) });
}
export async function getSellerSettlement() { return request("/seller/settlement"); }
export async function getSellerInquiries() { return request("/seller/inquiries"); }
export async function answerSellerInquiry(inquiryId, answerContent) {
  return request(`/seller/inquiries/${inquiryId}/answer`, { method: "PATCH", body: JSON.stringify({ answer_content: answerContent }) });
}
export async function getSellerReviews() { return request("/seller/reviews"); }
