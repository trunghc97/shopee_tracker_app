from fastapi import FastAPI
from app.api.routes import router
from app.db.session import Base, engine

def init_db():
    Base.metadata.create_all(bind=engine)

init_db()

app = FastAPI()
app.include_router(router)