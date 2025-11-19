# db.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# 1. Tạo Async Engine
engine = create_async_engine(DATABASE_URL, echo=True)

# 2. Tạo Async Session Maker
# Thêm class_=AsyncSession để đảm bảo session được tạo là bất đồng bộ
SessionLocal = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, # Rất quan trọng để xác định kiểu session
    autoflush=False,
    expire_on_commit=False, # Tùy chọn, nhưng là default tốt cho async
)

Base = declarative_base()