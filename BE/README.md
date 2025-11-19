1. Tải Postgres server
2. Sửa mật khẩu postgres trong .env: postgresql+asyncpg://postgres:{password}@localhost:5432/postgres
3. 
- Sửa GOOGLE_CLIENT_SECRET, GOOGLE_CLIENT_ID(tra AI): https://console.cloud.google.com/apis/credentials(lúc tạo credentials set luôn secret ko thì ko xem lại được)
- Add credentials cho OAuth client ID sau đó set Authorized redirect URIs: http://localhost:8000/auth/callback
4. Tạo venv: python -m venv venv
5. Activate .env: venv\Scripts\activate
6.Ở terminal chạy: pip install -r requirements.txt
7. Chạy app: uvicorn main:app --reload

