from playwright.async_api import async_playwright
from app.core.config import settings
from app.core.logger import logger
import asyncio

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

async def setup_browser_context(playwright) -> tuple:
    """Khởi tạo browser và context với các cấu hình cần thiết"""
    logger.info("[Shopee Login] Bắt đầu khởi tạo browser")
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
    logger.info("[Shopee Login] Browser đã được khởi tạo")
    
    logger.info("[Shopee Login] Đang tạo context")
    context = await browser.new_context(
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
    logger.info("[Shopee Login] Context đã được tạo")

    return context, browser

async def login_shopee_and_save_cookie():
    async with async_playwright() as p:
        try:
            # Khởi tạo browser và context
            context, browser = await setup_browser_context(p)
            page = await context.new_page()
            logger.info("[Shopee Login] Đã tạo page mới")

            # Thêm JavaScript để vượt qua anti-bot
            await page.add_init_script(STEALTH_JS)
            logger.info("[Shopee Login] Đã thêm stealth script")

            # Truy cập trang đăng nhập
            logger.info("[Shopee Login] Đang truy cập trang đăng nhập...")
            await page.goto("https://shopee.vn/buyer/login", wait_until="networkidle", timeout=30000)
            logger.info("[Shopee Login] Đã load trang đăng nhập, đang chờ trang ổn định...")
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
            await asyncio.sleep(2)

            # Kiểm tra và điền username
            logger.info("[Shopee Login] Đang tìm ô nhập username...")
            username_selectors = [
                'input[name="loginKey"]',
                'input[autocomplete="username"]',
                'input[type="text"]',
                '[placeholder*="email"]',
                '[placeholder*="số điện thoại"]'
            ]

            username_input = None
            for selector in username_selectors:
                try:
                    username_input = await page.wait_for_selector(selector, state="visible", timeout=5000)
                    if username_input:
                        logger.info(f"[Shopee Login] Tìm thấy input username với selector: {selector}")
                        break
                except:
                    continue

            if not username_input:
                raise Exception("Không tìm thấy ô nhập username")

            logger.info("[Shopee Login] Đang điền username...")
            await username_input.fill(settings.SHOPEE_USERNAME)
            await asyncio.sleep(1)
            logger.info("[Shopee Login] Đã điền username")

            # Kiểm tra và điền password
            logger.info("[Shopee Login] Đang tìm ô nhập password...")
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[autocomplete="current-password"]',
                '[placeholder*="mật khẩu"]'
            ]

            password_input = None
            for selector in password_selectors:
                try:
                    password_input = await page.wait_for_selector(selector, state="visible", timeout=5000)
                    if password_input:
                        logger.info(f"[Shopee Login] Tìm thấy input password với selector: {selector}")
                        break
                except:
                    continue

            if not password_input:
                raise Exception("Không tìm thấy ô nhập password")

            logger.info("[Shopee Login] Đang điền password...")
            await password_input.fill(settings.SHOPEE_PASSWORD)
            await asyncio.sleep(1)
            logger.info("[Shopee Login] Đã điền password")

            # Tìm và click nút đăng nhập
            logger.info("[Shopee Login] Đang tìm nút đăng nhập...")
            submit_button_selectors = [
                'button[type="submit"]',
                'button.btn-solid-primary',
                'button:has-text("Đăng nhập")',
                '[data-testid="submit-button"]',
                'button.login-btn'
            ]

            submit_button = None
            for selector in submit_button_selectors:
                try:
                    submit_button = await page.wait_for_selector(selector, state="visible", timeout=5000)
                    if submit_button:
                        logger.info(f"[Shopee Login] Tìm thấy nút đăng nhập với selector: {selector}")
                        break
                except:
                    continue

            if not submit_button:
                # Thử tìm bất kỳ button nào có text "Đăng nhập"
                logger.info("[Shopee Login] Không tìm thấy nút bằng selector, đang tìm theo text...")
                buttons = await page.query_selector_all('button')
                for button in buttons:
                    text = await button.text_content()
                    if "đăng nhập" in text.lower():
                        submit_button = button
                        logger.info("[Shopee Login] Tìm thấy nút đăng nhập bằng text")
                        break

            if not submit_button:
                raise Exception("Không tìm thấy nút đăng nhập")

            # Click nút đăng nhập
            logger.info("[Shopee Login] Đang click nút đăng nhập...")
            await submit_button.click()
            logger.info("[Shopee Login] Đã click nút đăng nhập, đang chờ xử lý...")
            
            # Chờ đăng nhập hoàn tất và kiểm tra chuyển hướng
            await asyncio.sleep(5)
            await page.wait_for_load_state("networkidle", timeout=60000)
            logger.info("[Shopee Login] Trang đã load xong sau khi click đăng nhập")

            # Lưu cookies
            logger.info("[Shopee Login] Đăng nhập thành công, đang lưu cookies...")
            await context.storage_state(path=settings.SHOPEE_COOKIES_PATH)
            logger.info("[Shopee Login] Đã lưu cookies")
            await browser.close()
            logger.info("[Shopee Login] Đã đóng browser")
            return True

        except Exception as e:
            logger.error(f"[Shopee Login] Lỗi trong quá trình đăng nhập: {str(e)}")
            try:
                await browser.close()
                logger.info("[Shopee Login] Đã đóng browser sau khi gặp lỗi")
            except:
                pass
            return False