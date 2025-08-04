import os

class Settings:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "aliprice")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASS = os.getenv("DB_PASS", "secret")
    SHOPEE_USERNAME = os.getenv("SHOPEE_USERNAME", "")
    SHOPEE_PASSWORD = os.getenv("SHOPEE_PASSWORD", "")
    SHOPEE_COOKIES_PATH = os.getenv("SHOPEE_COOKIES_PATH", "app/cookies/shopee_state.json")

settings = Settings()
