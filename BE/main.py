from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI
from auth import router as auth_router
from chat import router as chat_router
from db import Base, engine

app = FastAPI()

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # cho phép FE gọi
    allow_credentials=True,
    allow_methods=["*"],          # GET, POST, OPTIONS,...
    allow_headers=["*"],          # cho phép Authorization, Content-Type,...
)

app.include_router(auth_router)
app.include_router(chat_router)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
def root():
    return {"message": "API is running"}