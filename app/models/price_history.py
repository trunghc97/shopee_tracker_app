from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.db.session import Base

class PriceHistory(Base):
    __tablename__ = "price_history"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("shopee_products.id"))
    price = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow)
