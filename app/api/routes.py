from fastapi import APIRouter, HTTPException
import requests, re
from sqlalchemy.orm import Session
from app.schemas.schemas import ShortUrlRequest, TrackRequest
from app.db.session import SessionLocal
from app.models.models import ShopeeProduct
from app.crud import products
from app.crud.products import save_price_history
from app.services.router import route_by_domain
from app.core.logger import logger

router = APIRouter()

@router.post("/info")
async def resolve_and_save(payload: ShortUrlRequest):
    logger.info(f"[API] Nhận request cho URL: {payload.short_url}")
    
    db: Session = SessionLocal()
    existing = products.get_product_by_short_url(db, payload.short_url)
    if existing:
        logger.info("[API] Tìm thấy dữ liệu trong cache")
        db.close()
        return {
            "productUrl": existing.product_url,
            "shopId": existing.shop_id,
            "itemId": existing.item_id,
            "price": existing.current_price,
            "history": existing.price_history,
            "cached": True
        }

    logger.info("[API] Không tìm thấy trong cache, bắt đầu xử lý mới")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        # B1: Lấy URL thật từ short link
        logger.info("[API] Bước 1: Lấy URL thật từ short link")
        resp = requests.get(payload.short_url, headers=headers, allow_redirects=True, timeout=30)
        
        if resp.status_code != 200:
            logger.error(f"[API] Lỗi khi truy cập link: HTTP {resp.status_code}")
            raise Exception(f"Không thể truy cập link: HTTP {resp.status_code}")
        full_url = resp.url
        logger.info(f"[API] URL thật: {full_url}")

        # B2: Tách shop_id và item_id từ URL
        logger.info("[API] Bước 2: Tách shop_id và item_id từ URL")
        match = re.search(r'product/(\d+)/(\d+)', full_url) or re.search(r'-i\.(\d+)\.(\d+)', full_url)
        if not match:
            logger.error("[API] Không tìm thấy productId trong URL")
            raise HTTPException(status_code=400, detail="Không tìm thấy productId trong URL")

        shop_id, item_id = match.groups()
        logger.info(f"[API] Đã tách được shop_id={shop_id}, item_id={item_id}")

        # B3: Lấy giá từ service tương ứng với domain
        logger.info("[API] Bước 3: Lấy giá từ service tương ứng")
        result = await route_by_domain(full_url, shop_id, item_id, db)
        price = result.get("price")
        history = result.get("history")
        logger.info(f"[API] Kết quả từ service: price={price}, history={history}")

        # B4: Tạo bản ghi và lưu vào DB
        logger.info("[API] Bước 4: Lưu thông tin vào database")
        db_item = ShopeeProduct(
            short_url=payload.short_url,
            product_url=full_url,
            shop_id=shop_id,
            item_id=item_id,
            current_price=price,
            price_history=history
        )
        created = products.create_product(db, db_item)
        logger.info(f"[API] Đã tạo bản ghi với ID: {created.id}")
        
        save_price_history(db, created.id, price)
        logger.info("[API] Đã lưu lịch sử giá")

        db.close()
        logger.info("[API] Hoàn thành xử lý, trả về kết quả")

        return {
            "productUrl": full_url,
            "shopId": shop_id,
            "itemId": item_id,
            "price": price,
            "history": history
        }

    except Exception as e:
        logger.error(f"[API] Lỗi trong quá trình xử lý: {str(e)}")
        db.close()
        return {"error": f"Lỗi: {str(e)}"}

@router.post("/track")
def enable_tracking(req: TrackRequest):
    db: Session = SessionLocal()
    item = products.get_product_by_id(db, req.shop_id, req.item_id)
    if item:
        item.is_tracking = True
        db.commit()
        db.close()
        return {"message": "Đã bật theo dõi"}
    db.close()
    return {"error": "Không tìm thấy sản phẩm"}