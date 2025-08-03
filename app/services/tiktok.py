from playwright.sync_api import sync_playwright
from app.core.logger import logger
from sqlalchemy.orm import Session
from app.crud.products import get_product_by_id
from datetime import datetime
from app.models.models import ShopeeProduct

def get_tiktok_current_price(url: str):
    """Lấy giá hiện tại từ trang sản phẩm TikTok"""
    logger.info(f"[TikTok] Đang lấy giá hiện tại cho URL: {url}")
    
    with sync_playwright() as p:
        try:
            # Khởi tạo browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state="app/cookies/tiktok_state.json")
            page = context.new_page()

            # Truy cập trang sản phẩm
            logger.info("[TikTok] Truy cập trang sản phẩm")
            page.goto(url)
            page.wait_for_timeout(3000)  # Đợi trang load

            # Lấy giá hiện tại
            try:
                price_element = page.locator('[data-e2e="product-price"]').first
                price_text = price_element.text_content()
                # Xử lý text giá (ví dụ: "150.000₫" -> "150000")
                price = price_text.replace("₫", "").replace(".", "").strip()
                logger.info(f"[TikTok] Lấy giá hiện tại thành công: {price} VND")
                browser.close()
                return price
            except Exception as e:
                logger.error(f"[TikTok] Không tìm thấy giá trên trang: {str(e)}")
                browser.close()
                return None

        except Exception as e:
            logger.error(f"[TikTok] Lỗi khi truy cập trang: {str(e)}")
            try:
                browser.close()
            except:
                pass
            return None

def get_tiktok_price_data(url: str, shop_id: str, item_id: str, db: Session):
    """Lấy giá và lịch sử giá cho sản phẩm TikTok"""
    logger.info(f"[TikTok] Bắt đầu lấy giá cho URL: {url}")
    
    # Kiểm tra cache
    existing = get_product_by_id(db, shop_id, item_id)
    if existing and existing.is_tracking:
        logger.info(f"[TikTok] Tìm thấy dữ liệu trong cache: price={existing.current_price}")
        return {
            "productUrl": existing.product_url,
            "shopId": existing.shop_id,
            "itemId": existing.item_id,
            "price": existing.current_price,
            "history": existing.price_history,
            "cached": True
        }

    # Lấy giá hiện tại
    current_price = get_tiktok_current_price(url)
    if not current_price:
        logger.error("[TikTok] Không lấy được giá hiện tại")
        raise Exception("Không thể lấy được giá hiện tại từ trang sản phẩm")

    # Sử dụng lịch sử từ database nếu có, nếu không thì "Đang cập nhật"
    history = existing.price_history if existing else "Đang cập nhật"
    
    # Tạo hoặc cập nhật bản ghi
    if existing:
        logger.info("[TikTok] Cập nhật giá mới")
        existing.current_price = current_price
        existing.crawled_at = datetime.utcnow()
        db.commit()
    else:
        logger.info("[TikTok] Tạo bản ghi mới")
        db_item = ShopeeProduct(
            short_url=url,
            product_url=url,
            shop_id=shop_id,
            item_id=item_id,
            current_price=current_price,
            price_history=history,
            is_tracking=False,
            crawled_at=datetime.utcnow()
        )
        db.add(db_item)
        db.commit()

    logger.info("[TikTok] Trả về kết quả")
    return {
        "productUrl": url,
        "shopId": shop_id,
        "itemId": item_id,
        "price": current_price,
        "history": history,
        "cached": False
    }
