# 🛒 Shopee Price Tracker (with Lazada, TikTok & Proxy)

## 📌 Features
- ✅ Track product prices on **Shopee**, **Lazada**, and **TikTok Shop**
- 🔄 Automatically fetch real proxies from [GeoNode](https://geonode.com)
- 🧠 Uses [AliPrice](https://www.aliprice.com) for price + historical data
- 🗃 Store products and historical prices in **PostgreSQL**
- ⚙️ Docker + Docker Compose ready for full deployment

---

## 🚀 Quick Start

### 1. Requirements
- Docker & Docker Compose
- Python 3.10+ (if running manually)

### 2. Start with Docker
```bash
docker-compose up --build
```

> PostgreSQL volume is persisted to avoid data loss

---

## 🔧 API Usage

### `POST /track`
Track a product URL

```json
{
  "url": "https://shopee.vn/product/12345/67890"
}
```

### `GET /products`
List all tracked products

### `GET /products/{item_id}`
Get product detail & current price

---

## 📁 Project Structure

```
shopee_price_tracker/
├── app/
│   ├── api/          # API routes (FastAPI)
│   ├── core/         # Config
│   ├── crud/         # DB operations
│   ├── db/           # DB connection
│   ├── models/       # SQLAlchemy models
│   ├── schemas/      # Pydantic schemas
│   ├── services/     # Crawlers (Shopee, Lazada, TikTok, Proxy)
│   └── main.py       # App entry point
├── docker-compose.yml
└── README.md
```

---

## 🛠 Proxy Notes
Using [GeoNode API](https://geonode.com) for free rotating HTTP proxies:
```python
https://proxylist.geonode.com/api/proxy-list?limit=10&page=1&sort_by=lastChecked
```

---

## 📈 Coming soon
- Chart view of price history
- Telegram/email alerts for price drops
- CSV/Excel export

---

## 🤝 Contributing
Feel free to submit issues or feature requests!

