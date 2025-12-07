from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from db import Base
from sqlalchemy.sql import func


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    google_id = Column(String(255), unique=True)
    email = Column(String(255), unique=True)
    name = Column(String(255))
    refresh_token = Column(String(512))

    chats = relationship("ChatHistory", back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())

    user = relationship("User")
    chats = relationship("ChatHistory", back_populates="session")


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(Integer, ForeignKey("sessions.id"))
    message = Column(Text)
    response = Column(Text)
    timestamp = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="chats")
    session = relationship("Session", back_populates="chats")
