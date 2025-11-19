from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from db import Base
from sqlalchemy.sql import func

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    google_id = Column(String, unique=True)
    email = Column(String, unique=True)
    name = Column(String)
    refresh_token = Column(String)

    chats = relationship("ChatHistory", back_populates="user")

class ChatHistory(Base):
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(Text)
    response = Column(Text)
    
    # THÊM CỘT THỜI GIAN
    # default=func.now() sẽ tự động điền thời gian hiện tại khi bản ghi được tạo
    timestamp = Column(DateTime, default=func.now()) 

    user = relationship("User", back_populates="chats")
