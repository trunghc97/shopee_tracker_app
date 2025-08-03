from playwright.sync_api import Page
from app.core.logger import logger

def get_price_data(page: Page):
    """Lấy lịch sử giá từ AliPrice trên trình duyệt hiện tại"""
    logger.info("[AliPrice] Bắt đầu lấy lịch sử giá")
    
    try:
        # Lấy lịch sử giá từ biểu đồ
        history_element = page.locator('.price-history-container').first
        if history_element:
            history = history_element.text_content()
            logger.info("[AliPrice] Lấy lịch sử giá thành công")
            return "Đang cập nhật", history
        else:
            logger.warning("[AliPrice] Không tìm thấy biểu đồ lịch sử giá")

    except Exception as e:
        logger.error(f"[AliPrice] Lỗi khi truy cập trang: {str(e)}")

    return "Đang cập nhật", "Không thấy lịch sử giá"
