from app.services.aliprice import get_price_data
from app.crud.products import get_product_by_id, create_product, save_price_history
from app.models.models import ShopeeProduct
from sqlalchemy.orm import Session
from datetime import datetime
import json, re
from app.core.logger import logger
from playwright.async_api import async_playwright, Page, BrowserContext
from bs4 import BeautifulSoup, Doctype, Comment, NavigableString
import asyncio
import app.services.shopee_login as shopee_login

# User agent cho thiết bị di động
MOBILE_USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"

# JavaScript để vượt qua anti-bot
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {
    get: () => false,
});
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});
window.chrome = {
    runtime: {},
};
Object.defineProperty(navigator, 'languages', {
    get: () => ['vi-VN', 'vi', 'en-US', 'en'],
});
Object.defineProperty(navigator, 'platform', {
    get: () => 'iPhone',
});
"""

async def setup_browser_context(playwright) -> tuple[BrowserContext, any]:
    """Khởi tạo browser và context với các cấu hình cần thiết"""
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--window-size=375,812',
            '--enable-features=NetworkService',
            '--allow-running-insecure-content',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--js-flags="--max-old-space-size=8192"'
        ]
    )
    
    context = await browser.new_context(
        storage_state="app/cookies/shopee_state.json",
        user_agent=MOBILE_USER_AGENT,
        viewport={'width': 375, 'height': 812},
        device_scale_factor=2,
        is_mobile=True,
        has_touch=True,
        locale='vi-VN',
        timezone_id='Asia/Ho_Chi_Minh',
        permissions=['geolocation'],
        bypass_csp=True,  # Bỏ qua Content Security Policy
    )

    # Thêm các headers giả mạo
    await context.set_extra_http_headers({
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1'
    })

    return context, browser

async def check_login_status(page: Page) -> bool:
    """Kiểm tra trạng thái đăng nhập của Shopee"""
    try:
        # Truy cập trang profile để kiểm tra đăng nhập
        await page.goto("https://shopee.vn/user/account/profile", wait_until="networkidle")
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)  # Chờ thêm để trang load hoàn toàn

        # Kiểm tra các dấu hiệu của trang lỗi hoặc chưa đăng nhập
        error_texts = ["Trang không khả dụng", "vui lòng đăng nhập lại", "Đăng nhập"]
        page_content = await page.content()
        
        for text in error_texts:
            if text.lower() in page_content.lower():
                logger.info(f"[Shopee] Phát hiện trạng thái chưa đăng nhập: {text}")
                return False

        # Kiểm tra URL
        if "login" in page.url or "captcha" in page.url:
            logger.info("[Shopee] URL chứa 'login' hoặc 'captcha'")
            return False

        return True
    except Exception as e:
        logger.error(f"[Shopee] Lỗi khi kiểm tra trạng thái đăng nhập: {str(e)}")
        return False

def is_valid_price_format(text: str) -> bool:
    """
    Kiểm tra xem một chuỗi có phải là định dạng giá tiền hợp lệ không
    Ví dụ hợp lệ: ₫1.234.567, ₫123.456, ₫12.345
    """
    # Loại bỏ ký tự ₫ và khoảng trắng
    price_text = text.replace("₫", "").strip()
    
    # Kiểm tra xem có phải là số được phân cách bởi dấu chấm không
    if not re.match(r'^\d{1,3}(\.\d{3})*$', price_text):
        return False
    
    # Kiểm tra độ dài hợp lý (giá Shopee thường từ 5-7 chữ số)
    num_digits = len(price_text.replace(".", ""))
    if num_digits < 4 or num_digits > 8:
        return False
        
    return True

def print_element_info(element, indent=0):
    """In thông tin chi tiết về một element HTML"""
    try:
        indent_str = "  " * indent

        # Bỏ qua các loại node không cần thiết
        if isinstance(element, (Comment, Doctype)):
            return

        # Xử lý text node
        if isinstance(element, NavigableString):
            text = str(element).strip()
            if text:
                logger.info(f"{indent_str}[DEBUG] Text: {text}")
            return

        # Xử lý element node
        if hasattr(element, 'name'):
            logger.info(f"{indent_str}[DEBUG] Thẻ: {element.name}")
            
            # In các thuộc tính nếu có
            if hasattr(element, 'attrs') and element.attrs:
                logger.info(f"{indent_str}[DEBUG] Thuộc tính: {element.attrs}")
            
            # In nội dung text nếu có
            text = element.get_text(strip=True)
            if text:
                logger.info(f"{indent_str}[DEBUG] Nội dung: {text}")

    except Exception as e:
        logger.error(f"[DEBUG] Lỗi khi in thông tin element: {str(e)}")

async def get_shopee_data(url: str, shop_id: str, item_id: str):
    """Lấy giá hiện tại và lịch sử giá sử dụng Playwright"""
    logger.info(f"[Shopee] Đang lấy dữ liệu cho URL: {url}")
    
    async with async_playwright() as p:
        browser = None
        try:
            # Khởi tạo browser và context
            context, browser = await setup_browser_context(p)
            page = await context.new_page()

            # Thêm JavaScript để vượt qua anti-bot
            await page.add_init_script(STEALTH_JS)

            # Kiểm tra trạng thái đăng nhập
            if not await check_login_status(page):
                logger.info("[Shopee] Cookie hết hạn, tiến hành đăng nhập lại")
                await browser.close()
                browser = None

                # Đăng nhập lại để lấy cookie mới
                if await shopee_login.login_shopee_and_save_cookie():
                    logger.info("[Shopee] Đăng nhập thành công, khởi tạo lại browser")
                    # Khởi tạo lại browser và context
                    context, browser = await setup_browser_context(p)
                    page = await context.new_page()
                    await page.add_init_script(STEALTH_JS)

                    # Kiểm tra lại trạng thái đăng nhập
                    if not await check_login_status(page):
                        raise Exception("Vẫn không thể đăng nhập sau khi làm mới cookie")
                else:
                    raise Exception("Không thể đăng nhập lại Shopee")

            # Truy cập trang sản phẩm
            logger.info(f"[Shopee] Truy cập trang sản phẩm: {url}")
            
            # Chờ JavaScript load
            await page.route("**/*", lambda route: route.continue_())
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_load_state("load")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)  # Tăng thời gian chờ để JavaScript chạy

            # Chờ cho JavaScript load xong
            try:
                await page.wait_for_selector('div', timeout=10000)
                # Thêm đoạn JavaScript để kiểm tra trang đã load xong chưa
                await page.evaluate("""
                    () => new Promise((resolve) => {
                        if (document.readyState === 'complete') {
                            resolve();
                        } else {
                            window.addEventListener('load', resolve);
                        }
                    })
                """)
            except Exception as e:
                logger.warning(f"[Shopee] Lỗi khi chờ trang load: {str(e)}")

            # Kiểm tra nếu trang hiển thị lỗi
            page_content = await page.content()
            if "Trang không khả dụng" in page_content or "vui lòng đăng nhập lại" in page_content.lower():
                raise Exception("Trang sản phẩm không khả dụng hoặc yêu cầu đăng nhập lại")

            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # In thông tin debug về cấu trúc trang
            logger.info("[DEBUG] ========== BẮT ĐẦU IN THÔNG TIN DEBUG ==========")
            logger.info("[DEBUG] URL hiện tại: " + page.url)
            
            # In tất cả các thẻ và nội dung của chúng
            for element in soup.find_all(True):  # True để lấy tất cả các thẻ HTML
                print_element_info(element)

            logger.info("[DEBUG] ========== KẾT THÚC THÔNG TIN DEBUG ==========")

            # Tìm tất cả thẻ có chứa ký tự ₫
            price_candidates = []
            for element in soup.find_all(string=re.compile('₫')):
                text = element.strip()
                logger.info(f"[Shopee] Tìm thấy giá tiềm năng: {text}")
                if is_valid_price_format(text):
                    price_candidates.append(text)
                    logger.info(f"[Shopee] Giá hợp lệ: {text}")

            if not price_candidates:
                raise Exception("Không tìm thấy giá hợp lệ trong trang")

            # Lấy giá cao nhất (thường là giá gốc) nếu có nhiều giá
            price_text = max(price_candidates, key=lambda x: int(x.replace("₫", "").replace(".", "")))
            logger.info(f"[Shopee] Chọn giá: {price_text}")

            # Xử lý text giá (VD: ₫159.000 → 159000)
            current_price = (
                price_text.replace("₫", "")
                .replace(".", "")
                .replace(",", "")
                .strip()
            )

            logger.info(f"[Shopee] Giá hiện tại: {current_price} VND")

            # Lấy lịch sử từ AliPrice nếu có
            _, history = await get_price_data(page)

            return current_price, history

        except Exception as e:
            logger.error(f"[Shopee] Lỗi khi lấy giá sản phẩm: {str(e)}")
            if browser:
                try:
                    await browser.close()
                except:
                    pass
            return None, None

async def get_shopee_price_data(url: str, shop_id: str, item_id: str, db: Session):
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
    current_price, history = await get_shopee_data(url, shop_id, item_id)
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