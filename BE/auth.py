from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, update
import httpx, os, jwt, datetime, time
from db import SessionLocal # Đảm bảo SessionLocal là Async SessionMaker
from models import User # Đảm bảo User có trường refresh_token
from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()

router = APIRouter(prefix="/auth")

# Định nghĩa các biến môi trường
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
JWT_SECRET = os.getenv("JWT_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# --- Model cho Refresh API ---
class RefreshTokenRequest(BaseModel):
    refresh_token: str

# --- Hàm tiện ích tạo Token ---

def create_tokens(user_id: int):
    """Tạo Access Token và Refresh Token mới."""
    
    # 1. Access Token (AT) - Hạn 15 phút
    access_token_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
    access_payload = {
        "user_id": user_id,
        "token_type": "access",
        "iat": int(time.time()),
        "exp": int(access_token_expiry.timestamp())
    }
    access_token = jwt.encode(access_payload, JWT_SECRET, algorithm="HS256")

    # 2. Refresh Token (RT) - Hạn 7 ngày
    refresh_token_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
    refresh_payload = {
        "user_id": user_id,
        "token_type": "refresh",
        "exp": int(refresh_token_expiry.timestamp())
    }
    refresh_token = jwt.encode(refresh_payload, JWT_SECRET, algorithm="HS256")
    
    return access_token, refresh_token

# --- 1. Endpoint Redirect Google ---
@router.get("/login")
def login():
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        "?response_type=code"
        f"&client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        "&scope=openid%20email%20profile"
        "&prompt=select_account"
    )
    return RedirectResponse(google_auth_url)

# --- 2. Endpoint Callback (Xử lý Đăng nhập) ---
@router.get("/callback")
async def callback(code: str):
    try:
        # 1. Exchange code <-> access_token (Google's token)
        # ... (Phần code lấy Google access_token và user profile giữ nguyên) ...
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": GOOGLE_REDIRECT_URI,
        }

        async with httpx.AsyncClient() as client:
            token_res = await client.post(token_url, data=data)
            token_json = token_res.json()
            
            if token_res.status_code != 200 or "access_token" not in token_json:
                return JSONResponse(status_code=400, content={"detail": "Lỗi lấy access_token từ Google"})

            access_token_google = token_json["access_token"]
            
            # 2. Get user info
            user_info_res = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token_google}"}
            )
            profile = user_info_res.json()
            picture_url = profile.get("picture", "")

            
            if user_info_res.status_code != 200 or "id" not in profile:
                return JSONResponse(status_code=400, content={"detail": "Lỗi lấy thông tin người dùng"})
        
        # 3. Lưu user vào DB & Lấy user_id
        async with SessionLocal() as session:
            # Tìm kiếm người dùng hiện có
            stmt_select = select(User).where(User.google_id == profile["id"])
            result = await session.execute(stmt_select)
            existing_user = result.scalars().first() # Lấy ORM object

            if existing_user is None:
                # Người dùng mới
                new_user = User(
                    google_id=profile["id"],
                    email=profile["email"],
                    name=profile["name"]
                )
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user) # Lấy ID mới được tạo
                user_id = new_user.id
                
            else:
                # Người dùng đã tồn tại
                user_id = existing_user.id

            # 4. Tạo cặp Token mới
            access_token, refresh_token = create_tokens(user_id)
            
            # 5. Lưu Refresh Token mới vào DB
            update_stmt = (
                update(User)
                .where(User.id == user_id)
                .values(refresh_token=refresh_token) # Cập nhật RT
            )
            await session.execute(update_stmt)
            await session.commit()

            # 6. Redirect về FE kèm token
            redirect_url = (
                f"{FRONTEND_URL}/auth/callback"
                f"?access_token={access_token}"
                f"&refresh_token={refresh_token}"
                f"&name={quote(profile['name'])}"
                f"&email={quote(profile['email'])}"
                f"&picture={quote(picture_url)}"
            )
            return RedirectResponse(redirect_url)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"detail": "Lỗi máy chủ nội bộ không xác định", "error": str(e)}
        )

# --- 3. Endpoint Refresh Token ---
@router.post("/refresh")
async def refresh_token(req: RefreshTokenRequest):
    rt_token = req.refresh_token
    
    try:
        # 1. Giải mã Refresh Token (RT)
        payload = jwt.decode(rt_token, JWT_SECRET, algorithms=["HS256"])
        
        # Kiểm tra token_type và exp
        if payload.get("token_type") != "refresh":
            raise HTTPException(401, detail="Invalid token type.")
            
        user_id = payload["user_id"]
        
        # 2. Truy vấn DB để xác nhận RT
        async with SessionLocal() as session:
            stmt_select = select(User).where(User.id == user_id)
            result = await session.execute(stmt_select)
            user = result.scalars().first()
            
            # Kiểm tra người dùng tồn tại và RT trong DB khớp với RT người dùng cung cấp
            if not user or user.refresh_token != rt_token:
                raise HTTPException(401, detail="Invalid or revoked refresh token.")
            
            # 3. Tạo cặp Token mới
            new_access_token, new_refresh_token = create_tokens(user_id)
            
            # 4. Lưu RT mới vào DB (Thu hồi RT cũ)
            update_stmt = (
                update(User)
                .where(User.id == user_id)
                .values(refresh_token=new_refresh_token)
            )
            await session.execute(update_stmt)
            await session.commit()

        # 5. Trả về Token mới
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "Bearer"
        }

    except jwt.ExpiredSignatureError:
        # RT hết hạn
        raise HTTPException(401, detail="Refresh token expired. Please login again.")
    except jwt.InvalidTokenError:
        # RT không hợp lệ (sai signature)
        raise HTTPException(401, detail="Invalid refresh token signature.")
    except Exception as e:
        print(f"Lỗi refresh token: {e}")
        raise HTTPException(500, detail="Internal server error during token refresh.")