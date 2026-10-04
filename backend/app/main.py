import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models
from .database import engine
from .routers import auth, donations, stats

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="NourishFlow AI", version="0.2.0")

origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
if os.getenv("FRONTEND_ORIGIN"):
    origins.append(os.environ["FRONTEND_ORIGIN"])

app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router)
app.include_router(donations.router)
app.include_router(stats.router)


@app.get("/")
def health():
    return {"status": "NourishFlow AI is running"}