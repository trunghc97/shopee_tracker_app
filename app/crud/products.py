from sqlalchemy.orm import Session
from app.models.models import ShopeeProduct

def get_product_by_short_url(db: Session, short_url: str):
    return db.query(ShopeeProduct).filter(ShopeeProduct.short_url == short_url).order_by(ShopeeProduct.crawled_at.desc()).first()

def get_product_by_id(db: Session, shop_id: str, item_id: str):
    return db.query(ShopeeProduct).filter(ShopeeProduct.shop_id == shop_id, ShopeeProduct.item_id == item_id).first()

def create_product(db: Session, product: ShopeeProduct):
    db.add(product)
    db.commit()


from app.models.price_history import PriceHistory

def save_price_history(db: Session, product_id: int, price: str):
    history = PriceHistory(product_id=product_id, price=price)
    db.add(history)
    db.commit()
