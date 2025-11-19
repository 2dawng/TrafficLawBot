from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import jwt, os, asyncio

from db import SessionLocal
from models import ChatHistory
from sqlalchemy import select, desc

from groq import Groq  # 🟢 GROQ API

router = APIRouter(prefix="/chat")

JWT_SECRET = os.getenv("JWT_SECRET")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))  # 🟢 GROQ CLIENT

class ChatRequest(BaseModel):
    message: str


def decode_jwt(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except:
        return None


@router.post("/")
async def chat(req: ChatRequest, background_tasks: BackgroundTasks, Authorization: str = Header(None)):
    if not Authorization:
        raise HTTPException(401, detail="Missing Authorization header")

    token = Authorization.replace("Bearer ", "")
    payload = decode_jwt(token)

    if not payload:
        raise HTTPException(401, detail="Invalid token")

    user_id = payload["user_id"]
    message = req.message

    full_response_data = {"text": ""}

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
                response_stream = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message},
                    ],
                    stream=True
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
                print(f"Lỗi khi gọi Groq: {e}")

                if attempt < max_retries - 1:
                    print(f"Retry sau {delay}s…")
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue

                # Hết retry → trả lỗi
                error_message = "\n\n[ERROR: Groq service overloaded. Vui lòng thử lại sau.]"
                yield error_message.encode("utf-8")
                full_response_data["text"] = error_message
                return

        return
    background_tasks.add_task(save_chat_history, user_id, message, full_response_data)

    return StreamingResponse(chat_stream_generator(), media_type="text/plain")


@router.get("/history")
async def get_history(Authorization: str = Header(None)):
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
            .where(ChatHistory.user_id == user_id)
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


async def save_chat_history(user_id: int, message: str, response: dict):
    full_response = response["text"]

    if not full_response or full_response.startswith("\n\n[ERROR:"):
        print("DEBUG: Không lưu lịch sử vì lỗi.")
        return

    try:
        async with SessionLocal() as session:
            chat = ChatHistory(
                user_id=user_id,
                message=message,
                response=full_response,
            )
            session.add(chat)
            await session.commit()
    except Exception as e:
        print(f"Error saving chat history: {e}")
