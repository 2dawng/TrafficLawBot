from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI
from auth import router as auth_router
from chat import router as chat_router
from db import Base, engine

# Configure logging
log_filename = f"trafficbot_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Suppress verbose loggers
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown (if needed)


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.devtunnels\.ms|http://localhost:5173|http://127\.0\.0\.1:5173",
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST, OPTIONS,...
    allow_headers=["*"],  # cho phép Authorization, Content-Type,...
    expose_headers=["*"],  # expose all headers
)

app.include_router(auth_router)
app.include_router(chat_router)


@app.get("/")
def root():
    return {"message": "API is running"}
