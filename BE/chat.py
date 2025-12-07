from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import jwt, os, asyncio, logging

logger = logging.getLogger(__name__)

from db import SessionLocal
from models import ChatHistory, Session
from sqlalchemy import select, desc

from groq import Groq  # 🟢 GROQ API

router = APIRouter(prefix="/chat")

JWT_SECRET = os.getenv("JWT_SECRET")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))  # 🟢 GROQ CLIENT


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = None


@router.post("/session")
async def create_session(Authorization: str = Header(None)):
    if not Authorization:
        raise HTTPException(401, "Missing Authorization header")
    token = Authorization.replace("Bearer ", "")
    payload = decode_jwt(token)
    if not payload:
        raise HTTPException(401, "Invalid token")
    user_id = payload["user_id"]
    logger.info(f"Creating session for user_id: {user_id}")
    async with SessionLocal() as session:
        new_session = Session(user_id=user_id)
        session.add(new_session)
        await session.commit()
        await session.refresh(new_session)
        logger.info(f"Created session {new_session.id} for user {user_id}")
        return {
            "session_id": new_session.id,
            "created_at": new_session.created_at.isoformat(),
        }


@router.get("/sessions")
async def list_sessions(Authorization: str = Header(None)):
    if not Authorization:
        raise HTTPException(401, "Missing Authorization header")
    token = Authorization.replace("Bearer ", "")
    payload = decode_jwt(token)
    if not payload:
        raise HTTPException(401, "Invalid token")
    user_id = payload["user_id"]
    async with SessionLocal() as session:
        stmt = (
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(desc(Session.created_at))
        )
        result = await session.execute(stmt)
        sessions = result.scalars().all()
        return [
            {"session_id": s.id, "created_at": s.created_at.isoformat()}
            for s in sessions
        ]


def decode_jwt(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except:
        return None


@router.post("/")
async def chat(
    req: ChatRequest,
    background_tasks: BackgroundTasks,
    Authorization: str = Header(None),
):
    if not Authorization:
        raise HTTPException(401, detail="Missing Authorization header")

    token = Authorization.replace("Bearer ", "")
    payload = decode_jwt(token)

    if not payload:
        raise HTTPException(401, detail="Invalid token")

    user_id = payload["user_id"]
    message = req.message
    session_id = req.session_id
    full_response_data = {"text": ""}

    logger.info(
        f"Chat request: user_id={user_id}, session_id={session_id}, message={message[:50]}"
    )

    # Retrieve session history if session_id is provided
    chat_history = []
    if session_id:
        logger.info(f"Retrieving history for session {session_id}")
        async with SessionLocal() as db_session:
            stmt = (
                select(ChatHistory)
                .where(ChatHistory.session_id == session_id)
                .order_by(ChatHistory.timestamp)
            )
            result = await db_session.execute(stmt)
            history_rows = result.scalars().all()

            logger.info(f"Found {len(history_rows)} messages in session history")
            # Build conversation history for context
            for row in history_rows:
                chat_history.append({"role": "user", "content": row.message})
                chat_history.append({"role": "assistant", "content": row.response})
    else:
        logger.warning("No session_id provided - chat will have no context")

    # ================================================
    # 🔥 STREAM GROQ
    # ================================================
    async def chat_stream_generator():
        system_prompt = (
            "Bạn là chatbot luật giao thông Việt Nam, cập nhật đến đầu 2026. "
            "Chỉ trả lời chính xác câu hỏi theo luật hiện hành, không suy đoán. "
        )

        max_retries = 3
        delay = 1

        for attempt in range(max_retries):
            try:
                # Build messages with session history
                messages = [{"role": "system", "content": system_prompt}]
                messages.extend(chat_history)
                messages.append({"role": "user", "content": message})

                response_stream = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    stream=True,
                )

                for chunk in response_stream:
                    delta = chunk.choices[0].delta

                    # delta.content là STRING, không phải dict
                    if delta and delta.content:
                        text = delta.content
                        full_response_data["text"] += text
                        yield text.encode("utf-8")

                return

            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                logger.error(
                    f"Groq API error (attempt {attempt + 1}/{max_retries}): {error_type} - {error_msg}"
                )

                if attempt < max_retries - 1:
                    logger.info(f"Retrying after {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue

                # Hết retry → trả lỗi chi tiết
                if (
                    "rate_limit" in error_msg.lower()
                    or "overloaded" in error_msg.lower()
                ):
                    error_message = (
                        "\n\n[LỖI: Dịch vụ AI đang quá tải. Vui lòng thử lại sau ít phút.]\n"
                        "Groq API hiện đang xử lý nhiều yêu cầu. Hãy thử lại sau 1-2 phút."
                    )
                elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
                    error_message = (
                        "\n\n[LỖI: Đã vượt giới hạn API.]\n"
                        "Hệ thống đã hết quota miễn phí. Vui lòng liên hệ quản trị viên."
                    )
                else:
                    error_message = (
                        f"\n\n[LỖI: Không thể kết nối đến dịch vụ AI.]\n"
                        f"Chi tiết: {error_type}\n"
                        f"Vui lòng thử lại sau hoặc liên hệ hỗ trợ."
                    )

                logger.error(f"Final error response: {error_message}")
                yield error_message.encode("utf-8")
                full_response_data["text"] = error_message
                return

        return

    background_tasks.add_task(
        save_chat_history, user_id, message, full_response_data, session_id
    )

    return StreamingResponse(chat_stream_generator(), media_type="text/plain")


@router.get("/history")
async def get_history(session_id: int, Authorization: str = Header(None)):
    if not Authorization:
        raise HTTPException(401, "Missing Authorization")

    token = Authorization.replace("Bearer ", "")
    payload = decode_jwt(token)

    if not payload:
        raise HTTPException(401, "Invalid token")

    user_id = payload["user_id"]

    async with SessionLocal() as session:
        stmt = (
            select(ChatHistory)
            .where(ChatHistory.user_id == user_id, ChatHistory.session_id == session_id)
            .order_by(desc(ChatHistory.timestamp))
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()
    return [
        {
            "message": r.message,
            "response": r.response,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        }
        for r in rows
    ]


async def save_chat_history(
    user_id: int, message: str, response: dict, session_id: int = None
):
    full_response = response["text"]

    if not full_response or full_response.startswith("\n\n[ERROR:"):
        logger.warning("Not saving chat history due to error response")
        return

    logger.info(
        f"Saving chat: user_id={user_id}, session_id={session_id}, msg_len={len(message)}"
    )
    try:
        async with SessionLocal() as session:
            chat = ChatHistory(
                user_id=user_id,
                session_id=session_id,
                message=message,
                response=full_response,
            )
            session.add(chat)
            await session.commit()
            logger.info(f"Chat history saved successfully")
    except Exception as e:
        logger.error(f"Error saving chat history: {e}", exc_info=True)
