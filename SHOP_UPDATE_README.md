# T5 SHOP 프론트-백엔드 연결 업데이트

## 중요
- 업로드된 MySQL SQL 백업의 **테이블 구조는 수정하지 않았습니다.**
- 기존 테이블(products, product_variants, inventories, product_images, file_assets, t5_carts, t5_wishlist_items, orders, order_items, t5_product_reviews)을 그대로 사용합니다.
- 개발 화면의 기본 구매자는 SQL 샘플 데이터가 충분한 `user_id = 4`입니다. 로그인 API를 완성하면 `src/api/shopApi.js`의 `DEMO_USER_ID`를 로그인 사용자 ID로 교체하세요.

## 추가된 백엔드 API
- GET /products : 상품 목록/검색/카테고리 필터
- GET /products/categories : 카테고리
- GET /products/{product_id} : 상품 상세/옵션/재고/리뷰
- GET /orders?user_id=4 : 주문 및 주문상품
- POST /reviews : 실구매 주문상품 리뷰 등록
- 기존 /cart, /wishlist : 프론트 표시용 상품/이미지/옵션 정보를 함께 반환하도록 보완

## 실행
### 백엔드
```bash
cd t5_backend_shopdb2
uv sync
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
Swagger: http://127.0.0.1:8000/docs

### 프론트엔드
```bash
cd t5_frontend_shopdb2
npm install
npm run dev -- --port 5174
```
웹: http://localhost:5174/

## 연결 주소
`t5_frontend_shopdb2/.env`
```env
VITE_API_URL=http://127.0.0.1:8000
```

FastAPI CORS에는 5173과 5174의 localhost/127.0.0.1을 모두 허용하도록 추가했습니다.
