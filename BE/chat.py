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
from qdrant_search import search_traffic_laws, format_context_for_llm

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
    # 🔥 QUERY REWRITING (if needed)
    # ================================================

    # Detect vague follow-up queries and rewrite using chat history
    search_query = message

    # Simple keyword check first (fast path)
    vague_patterns = [
        "trả lời lại",
        "nói lại",
        "giải thích lại",
        "chi tiết hơn",
        "rõ hơn",
        "cụ thể hơn",
        "nói rõ",
        "giải thích thêm",
        "thêm về",
    ]

    # Only check if message is short (likely a follow-up request)
    if len(message) < 100 and len(chat_history) >= 2:
        message_lower = message.lower()
        is_vague = any(pattern in message_lower for pattern in vague_patterns)

        if is_vague:
            # Get last user question from history
            last_user_msg = None
            for msg in reversed(chat_history):
                if msg["role"] == "user":
                    last_user_msg = msg["content"]
                    break

            if last_user_msg:
                search_query = last_user_msg
                logger.info(
                    f"🔄 Query rewritten from '{message}' to '{search_query[:100]}...' (vague follow-up detected)"
                )
        else:
            logger.info(
                f"✅ Using original query (not a follow-up): '{message[:100]}...'"
            )

    # ================================================
    # 🔥 TWO-STAGE RAG PIPELINE
    # ================================================

    # STAGE 1: Retrieve 50 candidate documents
    logger.info("STAGE 1: Retrieving 50 candidate documents from Qdrant...")
    candidate_results = search_traffic_laws(search_query, limit=50)

    if not candidate_results:
        logger.warning("No candidate documents found in Qdrant")
        # Early return with empty context
        search_results = []
        context = ""
    else:
        logger.info(
            f"Found {len(candidate_results)} candidates, now filtering to top 10 most relevant..."
        )

        # STAGE 2: AI selects top 10 most relevant documents
        # Build a summary of all 50 candidates for the AI to evaluate
        candidate_summary = "Danh sách 50 tài liệu tìm được:\n\n"
        for i, doc in enumerate(candidate_results, 1):
            candidate_summary += f"{i}. [{doc.get('year', 'N/A')}] {doc.get('title', 'Untitled')[:150]}\n"
            candidate_summary += f"   URL: {doc.get('url', '')[:100]}\n\n"

        # Ask AI to select top 10 most relevant documents
        selection_prompt = f"""Bạn là trợ lý chọn lọc tài liệu. Người dùng hỏi: "{search_query}"

Từ 50 tài liệu dưới đây, hãy chọn 10 tài liệu LIÊN QUAN NHẤT để trả lời câu hỏi.

Tiêu chí ưu tiên:
1. Tài liệu có tiêu đề khớp trực tiếp với câu hỏi (số văn bản cụ thể)
2. Văn bản chính thức (URL có "van-ban") hơn bài viết hỗ trợ (URL có "ho-tro-phap-luat")
3. Tài liệu mới nhất (năm 2024-2025 > 2023 > 2022...)
4. Nội dung liên quan đến vấn đề người dùng hỏi

{candidate_summary}

Chỉ trả về danh sách 10 số thứ tự (VD: 1,5,7,12,15,18,22,25,30,35), KHÔNG giải thích."""

        try:
            # Call Groq API for document selection
            selection_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": selection_prompt}],
                temperature=0.1,  # Low temperature for consistent selection
                max_tokens=100,
            )

            selected_indices_str = selection_response.choices[0].message.content.strip()
            logger.info(f"AI selected documents: {selected_indices_str}")

            # Parse selected indices
            import re

            selected_indices = [
                int(x) for x in re.findall(r"\d+", selected_indices_str)
            ]

            # Extract selected documents (adjust for 0-based indexing)
            search_results = [
                candidate_results[i - 1]
                for i in selected_indices
                if 0 < i <= len(candidate_results)
            ]
            search_results = search_results[:10]  # Ensure max 10

            logger.info(
                f"STAGE 2: Selected {len(search_results)} documents for final answer generation"
            )

            # Format context from selected documents
            context = format_context_for_llm(search_results)

        except Exception as e:
            logger.error(f"Error in document selection stage: {e}", exc_info=True)
            # Fallback: use top 10 from original ranking
            search_results = candidate_results[:10]
            context = format_context_for_llm(search_results)
            logger.warning("Fallback: Using top 10 from original ranking")

    if context:
        logger.info(
            f"Final context prepared: {len(search_results)} documents, context length: {len(context)}"
        )
    else:
        logger.warning("No relevant documents found in Qdrant")

    # ================================================
    # 🔥 STREAM GROQ (FINAL ANSWER GENERATION)
    # ================================================
    async def chat_stream_generator():
        system_prompt = (
            "Bạn là chatbot luật giao thông Việt Nam chuyên nghiệp, cập nhật đến cuối năm 2025. "
            "Chỉ trả lời chính xác câu hỏi theo luật hiện hành, không suy đoán. "
            "\n\n🎯 QUY TRÌNH XÁC MINH VĂN BẢN (BẮT BUỘC):"
            "\n1. KIỂM TRA NĂM: Xem xét TẤT CẢ các tài liệu được cung cấp và ghi chú năm ban hành của mỗi văn bản."
            "\n2. LỌC VĂN BẢN MỚI NHẤT: Ưu tiên tài liệu có năm 2025 → 2024 → 2023 → 2022... theo thứ tự giảm dần."
            "\n3. XÁC NHẬN LIÊN QUAN: Chỉ sử dụng văn bản MỚI NHẤT có nội dung thực sự liên quan đến câu hỏi."
            "\n4. LOẠI BỎ VĂN BẢN CŨ: Nếu có văn bản mới hơn về cùng vấn đề, KHÔNG trích dẫn văn bản cũ."
            "\n\n⛔ NGHIÊM CẤM HALLUCINATION:"
            "\n- CHỈ trả lời dựa trên tài liệu THỰC SỰ có trong ngữ cảnh được cung cấp"
            "\n- KHÔNG tự sáng tác hoặc trích dẫn văn bản KHÔNG có trong danh sách tài liệu"
            "\n- Nếu người dùng hỏi về văn bản CỤ THỂ (VD: 'Thông tư 35/2024') mà văn bản đó KHÔNG có trong tài liệu, hãy trả lời: 'Tôi không tìm thấy [tên văn bản] trong cơ sở dữ liệu. Các tài liệu liên quan tôi tìm được là: [liệt kê].'"
            "\n- KIỂM TRA KỸ: Văn bản bạn trích dẫn có THỰC SỰ xuất hiện trong danh sách [Tài liệu 1, 2, 3...] không?"
            "\n\n⚠️ CÁC VĂN BẢN QUAN TRỌNG CẦN LƯU Ý:"
            "\n- Nghị định 168/2024/NĐ-CP (hiệu lực 01/01/2025): Thay thế Nghị định 100/2019 và 123/2021 về xử phạt vi phạm hành chính giao thông đường bộ"
            "\n- Thông tư 12/2022/TT-BGTVT: Quy định về đào tạo, sát hạch, cấp GPLX"
            "\n- Luật Giao thông đường bộ 2024: Văn bản gốc mới nhất"
            "\n\n🔍 KHI TRẢ LỜI:"
            "\n- BẮT BUỘC ghi rõ năm ban hành: 'Theo Nghị định 168/2024/NĐ-CP...'"
            "\n- Nếu thấy văn bản cũ hơn (2019, 2020, 2021...), hãy cảnh báo: 'Lưu ý: Nghị định này có thể đã bị thay thế bởi văn bản mới hơn.'"
            "\n- Nếu không chắc chắn về tính hiện hành, hãy nói rõ: 'Thông tin dựa trên [văn bản] năm [X], vui lòng kiểm tra bản cập nhật mới nhất.'"
            "\n\n📋 CẤU TRÚC CÂU TRẢ LỜI CHI TIẾT (BẮT BUỘC):"
            "\n✅ LUÔN sử dụng cấu trúc đánh số nhiều cấp:"
            "\n   - Cấp 1: **1. Tiêu đề chính** (in đậm)"
            "\n   - Cấp 2: a) Mục con, b) Mục con, c) Mục con..."
            "\n   - Cấp 3: Dấu gạch đầu dòng (-) cho chi tiết nhỏ hơn"
            "\n✅ Trích dẫn cụ thể Điều/Khoản/Điểm khi có trong tài liệu:"
            "\n   - Ví dụ: 'Theo Điều 21, Khoản 2, Điểm a của Thông tư 35/2024/TT-BGTVT'"
            "\n   - CHỈ trích dẫn số Điều/Khoản THỰC TẾ từ tài liệu, KHÔNG dùng X/Y/Z"
            "\n✅ Đưa ra số liệu chính xác, KHÔNG ước lượng:"
            "\n   - Mức phạt: '4.000.000–6.000.000 đồng' (KHÔNG nói 'khoảng 4-6 triệu')"
            "\n   - Thời gian: '05 năm' hoặc '5 năm' (KHÔNG nói 'khoảng 5 năm')"
            "\n   - Học phí: '18.000.000–28.000.000 đồng' (có dấu nghìn)"
            "\n   - Điểm thi: '≥ 32/35 câu đúng' (ghi rõ tỷ lệ phần trăm nếu có)"
            "\n✅ Cấu trúc câu trả lời chuẩn gồm 5-7 phần:"
            "\n   1. Mở đầu ngắn gọn (1-2 câu giới thiệu vấn đề)"
            "\n   2-5. Các mục chính với tiêu đề in đậm và nội dung chi tiết"
            "\n   6. Lưu ý/Tóm lại (tổng hợp điểm quan trọng)"
            "\n   7. **📚 Tài liệu tham khảo** (BẮT BUỘC - chỉ liệt kê văn bản ĐÃ THỰC SỰ SỬ DỤNG)"
            "\n✅ Phần tài liệu tham khảo (BẮT BUỘC ở cuối mỗi câu trả lời):"
            "\n   - Thêm mục cuối cùng: '**📚 Tài liệu tham khảo:**'"
            "\n   - ⚠️ CHỈ liệt kê những văn bản mà bạn ĐÃ THỰC SỰ TRÍCH DẪN/SỬ DỤNG trong câu trả lời"
            "\n   - KHÔNG liệt kê hết 10 tài liệu nếu chỉ dùng 3-4 văn bản"
            "\n   - KIỂM TRA: Đọc lại câu trả lời → Văn bản nào được nhắc đến → CHỈ liệt kê những văn bản đó"
            "\n   - Format cho TỪNG tài liệu đã dùng: '- [Tài liệu X - NĂM YYYY] [Tên đầy đủ] ([URL])'"
            "\n   - Ví dụ (nếu chỉ dùng 3 văn bản):"
            "\n     - [Tài liệu 2 - NĂM 2024] Nghị định 168/2024/NĐ-CP về xử phạt (https://...)"
            "\n     - [Tài liệu 5 - NĂM 2025] Thông tư 35/2024 về đào tạo lái xe (https://...)"
            "\n     - [Tài liệu 7 - NĂM 2024] Quy định nâng hạng GPLX (https://...)"
            "\n   - QUY TRÌNH: Viết xong câu trả lời → Kiểm tra xem đã trích dẫn văn bản nào → Chỉ liệt kê những văn bản đó"
            "\n✅ Kết thúc bằng câu hỏi mở để hỗ trợ thêm (SAU phần tài liệu tham khảo):"
            "\n   - 'Bạn cần tôi giải thích thêm điều khoản nào không?'"
            "\n   - 'Bạn muốn biết thêm về [chủ đề liên quan] không?'"
            "\n   - 'Bạn muốn tôi cung cấp thêm thông tin về [vấn đề cụ thể] không?'"
            "\n\n💡 PHONG CÁCH TRÌNH BÀY:"
            "\n- Sử dụng đầy đủ markdown: **in đậm**, số thứ tự (1, 2, 3), chữ cái (a, b, c), gạch đầu dòng (-), bảng"
            "\n- Giải thích rõ ràng, chi tiết như một chuyên gia luật tư vấn"
            "\n- Chia nhỏ thông tin phức tạp thành các phần dễ hiểu với tiêu đề rõ ràng"
            "\n- Đưa ra ví dụ cụ thể khi cần thiết"
            "\n- Nếu có nhiều tình huống khác nhau (gây tai nạn, không gây tai nạn...), phải liệt kê đầy đủ theo từng mục a, b, c"
            "\n- TRÍCH XUẤT TỐI ĐA thông tin từ tài liệu: số giờ học, số câu hỏi thi, thời gian thi, điểm đạt, học phí, độ tuổi..."
            "\n- Nếu tài liệu có chi tiết cụ thể, phải đưa vào câu trả lời (VD: 20 giờ lý thuyết, 48 giờ thực hành, 30 câu hỏi trắc nghiệm...)"
            "\n- Sử dụng bảng so sánh khi có nhiều trường hợp khác nhau (xe máy vs ô tô, hạng B1 vs B2...)"
            "\n\n⚠️ LƯU Ý KHÁC:"
            "\n- CHỈ SỬ DỤNG TIẾNG VIỆT, KHÔNG dùng tiếng Trung, tiếng Anh hay ngôn ngữ khác."
            "\n- Trả lời đầy đủ, toàn diện như một bài hướng dẫn chi tiết (5-7 mục bao gồm phần tài liệu tham khảo)."
            "\n- Nếu có thông tin về xử phạt bổ sung (trừ điểm GPLX, tước GPLX...), phải nêu rõ trong mục riêng."
            "\n- LUÔN trích dẫn số liệu CỤ THỂ từ tài liệu, ghi rõ nguồn (Điều X, Khoản Y, văn bản Z)."
            "\n- MỖI câu trả lời phải có CẤU TRÚC RÕ RÀNG với đánh số 1, 2, 3... và a, b, c... (trừ câu hỏi đơn giản chỉ cần 1 câu trả lời)."
            "\n- ⚠️ QUAN TRỌNG NHẤT: Phải có phần **📚 Tài liệu tham khảo** ở cuối LIỆT KÊ TẤT CẢ văn bản đã sử dụng kèm URL."
        )

        max_retries = 3
        delay = 1

        for attempt in range(max_retries):
            try:
                # Build messages with session history
                messages = [{"role": "system", "content": system_prompt}]
                messages.extend(chat_history)

                # Add context from Qdrant if available
                if context:
                    messages.append({"role": "system", "content": context})

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
