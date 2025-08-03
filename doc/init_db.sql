
-- Tạo bảng lưu sản phẩm
CREATE TABLE IF NOT EXISTS shopee_products (
    id SERIAL PRIMARY KEY,
    short_url TEXT,
    product_url TEXT,
    shop_id TEXT,
    item_id TEXT,
    current_price TEXT,
    price_history TEXT,
    is_tracking BOOLEAN DEFAULT FALSE,
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tạo bảng lưu lịch sử giá
CREATE TABLE IF NOT EXISTS price_history (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES shopee_products(id),
    price TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
