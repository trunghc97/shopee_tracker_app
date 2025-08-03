from pydantic import BaseModel

class ShortUrlRequest(BaseModel):
    short_url: str

class TrackRequest(BaseModel):
    shop_id: str
    item_id: str
