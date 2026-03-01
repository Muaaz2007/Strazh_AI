# main.py

from fastapi import FastAPI
from api.routes import router
from config import settings

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG
)

app.include_router(router)

@app.get("/health")
def health_check():
    return {"status": "ok"}