from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime
from app.db.session import Base

class ShopeeProduct(Base):
    __tablename__ = "shopee_products"
    id = Column(Integer, primary_key=True)
    short_url = Column(String(255))
    product_url = Column(String(255))
    shop_id = Column(String(50))
    item_id = Column(String(50))
    current_price = Column(String(100))
    price_history = Column(Text)
    is_tracking = Column(Boolean, default=False)
    crawled_at = Column(DateTime, default=datetime.utcnow)
