import re
from app.services.shopee import get_shopee_price_data
from app.services.lazada import get_lazada_price_data
from app.services.tiktok import get_tiktok_price_data
from app.services.proxy import get_next_proxy

async def route_by_domain(url: str, shop_id: str = None, item_id: str = None, db = None):
    proxy = get_next_proxy()
    if "shopee.vn" in url:
        return await get_shopee_price_data(url, shop_id, item_id, db)
    elif "lazada.vn" in url:
        return get_lazada_price_data(url, proxy)
    elif "tiktok.com" in url:
        return get_tiktok_price_data(url, proxy)
    else:
        return "Không hỗ trợ", "Không hỗ trợ"