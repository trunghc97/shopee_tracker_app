from app.services.aliprice import get_price_data
from app.crud.products import get_product_by_id, create_product, save_price_history
from app.models.models import ShopeeProduct
from sqlalchemy.orm import Session
from datetime import datetime
from playwright.sync_api import sync_playwright
from app.core.logger import logger

def get_lazada_data(url: str, shop_id: str, item_id: str):
    """Lấy giá hiện tại và lịch sử giá sử dụng Playwright"""
    logger.info(f"[Lazada] Đang lấy dữ liệu cho URL: {url}")
    
    with sync_playwright() as p:
        try:
            # Khởi tạo browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state="app/cookies/lazada_state.json")
            page = context.new_page()

            # Truy cập trang sản phẩm
            logger.info("[Lazada] Truy cập trang sản phẩm")
            page.goto(url)
            page.wait_for_timeout(3000)  # Đợi trang load

            # Lấy giá hiện tại
            try:
                price_element = page.locator('.pdp-price').first
                price_text = price_element.text_content()
                # Xử lý text giá (ví dụ: "₫150.000" -> "150000")
                current_price = price_text.replace("₫", "").replace(".", "").strip()
                logger.info(f"[Lazada] Lấy giá hiện tại thành công: {current_price} VND")

                # Lấy lịch sử giá từ AliPrice
                _, history = get_price_data(page)
                
                browser.close()
                return current_price, history
            except Exception as e:
                logger.error(f"[Lazada] Không tìm thấy giá trên trang: {str(e)}")
                browser.close()
                return None, None

        except Exception as e:
            logger.error(f"[Lazada] Lỗi khi truy cập trang: {str(e)}")
            try:
                browser.close()
            except:
                pass
            return None, None

def get_lazada_price_data(url: str, shop_id: str, item_id: str, db: Session):
    """Lấy giá và lịch sử giá cho sản phẩm Lazada"""
    logger.info(f"[Lazada] Bắt đầu lấy giá cho URL: {url}")
    
    # Kiểm tra cache
    existing = get_product_by_id(db, shop_id, item_id)
    if existing and existing.is_tracking:
        logger.info(f"[Lazada] Tìm thấy dữ liệu trong cache: price={existing.current_price}")
        return {
            "productUrl": existing.product_url,
            "shopId": existing.shop_id,
            "itemId": existing.item_id,
            "price": existing.current_price,
            "history": existing.price_history,
            "cached": True
        }

    # Lấy giá hiện tại và lịch sử giá
    logger.info("[Lazada] Lấy giá hiện tại và lịch sử giá")
    current_price, history = get_lazada_data(url, shop_id, item_id)
    if not current_price:
        logger.error("[Lazada] Không lấy được giá hiện tại")
        raise Exception("Không thể lấy được giá hiện tại từ trang sản phẩm")

    if not history or history == "Không thấy lịch sử giá":
        history = "Đang cập nhật"

    # Tạo hoặc cập nhật bản ghi
    if existing:
        logger.info("[Lazada] Cập nhật giá mới")
        existing.current_price = current_price
        existing.crawled_at = datetime.utcnow()
        db.commit()
    else:
        logger.info("[Lazada] Tạo bản ghi mới")
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

    logger.info("[Lazada] Trả về kết quả")
    return {
        "productUrl": url,
        "shopId": shop_id,
        "itemId": item_id,
        "price": current_price,
        "history": history,
        "cached": False
    }
