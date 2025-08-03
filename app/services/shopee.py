from app.services.aliprice import get_price_data
from app.crud.products import get_product_by_id, create_product, save_price_history
from app.models.models import ShopeeProduct
from sqlalchemy.orm import Session
from datetime import datetime
import json
from app.core.logger import logger
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def get_shopee_data(url: str, shop_id: str, item_id: str):
    """Lấy giá hiện tại và lịch sử giá sử dụng Playwright"""
    logger.info(f"[Shopee] Đang lấy dữ liệu cho URL: {url}")
    
    with sync_playwright() as p:
        try:
            # Khởi tạo browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state="app/cookies/shopee_state.json")
            page = context.new_page()

            # Truy cập trang sản phẩm
            logger.info(f"[Shopee] Truy cập trang sản phẩm: {url}")
            page.goto(url, wait_until="networkidle")
            page.wait_for_load_state("domcontentloaded")

            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            logger.info("[Shopee] Bắt đầu in toàn bộ <div> trong trang:")
            for idx, div in enumerate(soup.find_all("div")):
                text = div.get_text(strip=True)
                if text:
                    logger.info(f"[{idx}] <div>: {text}")

            # Thử các selector có khả năng chứa giá
            selectors = [
                '.IZPeQz',  # class chính thức cho giá
                '[class*="price"]',
                '[class*="Price"]',
                '[data-testid="price"]',
                '.product-price',
                '.product-detail-price'
            ]

            price_text = None
            for selector in selectors:
                logger.info(f"[Shopee] Thử tìm giá với selector: {selector}")
                try:
                    price_locator = page.locator(selector)
                    price_text = price_locator.first.inner_text(timeout=5000)
                    if "₫" in price_text:
                        logger.info(f"[Shopee] Lấy được giá: {price_text}")
                        break
                except Exception as sel_error:
                    logger.debug(f"[Shopee] Selector thất bại: {selector} - {str(sel_error)}")
                    continue

            if not price_text:
                raise Exception("Không tìm thấy phần tử chứa giá")

            # Xử lý text giá (VD: ₫159.000 → 159000)
            current_price = (
                price_text.replace("₫", "")
                .replace(".", "")
                .replace(",", "")
                .strip()
            )

            logger.info(f"[Shopee] Giá hiện tại: {current_price} VND")

            # Lấy lịch sử từ AliPrice nếu có
            _, history = get_price_data(page)

            return current_price, history

        except Exception as e:
            logger.error(f"[Shopee] Lỗi khi lấy giá sản phẩm: {str(e)}")
            try:
                browser.close()
            except:
                pass
            return None, None

def get_shopee_price_data(url: str, shop_id: str, item_id: str, db: Session):
    logger.info(f"[Shopee] Bắt đầu lấy giá cho URL: {url}")
    
    existing = get_product_by_id(db, shop_id, item_id)
    if existing and existing.is_tracking:
        logger.info(f"[Shopee] Tìm thấy dữ liệu trong cache: price={existing.current_price}")
        return {
            "productUrl": existing.product_url,
            "shopId": existing.shop_id,
            "itemId": existing.item_id,
            "price": existing.current_price,
            "history": existing.price_history,
            "cached": True
        }

    # Lấy giá hiện tại và lịch sử giá
    logger.info("[Shopee] Lấy giá hiện tại và lịch sử giá")
    current_price, history = get_shopee_data(url, shop_id, item_id)
    if not current_price:
        logger.error("[Shopee] Không lấy được giá hiện tại")
        raise Exception("Không thể lấy được giá hiện tại từ trang sản phẩm")

    if not history or history == "Không thấy lịch sử giá":
        history = "Đang cập nhật"

    # Tạo bản ghi với giá hiện tại
    logger.info("[Shopee] Tạo bản ghi mới trong database")
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
    created_item = create_product(db, db_item)
    logger.info(f"[Shopee] Đã tạo bản ghi với ID: {created_item.id}")
    
    logger.info("[Shopee] Lưu lịch sử giá")
    save_price_history(db, created_item.id, current_price)
    logger.info("[Shopee] Hoàn thành lưu lịch sử giá")

    logger.info("[Shopee] Trả về kết quả")
    return {
        "productUrl": url,
        "shopId": shop_id,
        "itemId": item_id,
        "price": current_price,
        "history": history,
        "cached": False
    }
