1. Tải MySQL server
2. Tạo database: CREATE DATABASE trafficlawbot;
3. Sửa thông tin MySQL trong .env: mysql+aiomysql://root:{password}@localhost:3306/trafficlawbot
4. 
- Sửa GOOGLE_CLIENT_SECRET, GOOGLE_CLIENT_ID(tra AI): https://console.cloud.google.com/apis/credentials(lúc tạo credentials set luôn secret ko thì ko xem lại được)
- Add credentials cho OAuth client ID sau đó set Authorized redirect URIs: http://localhost:8000/auth/callback
5. Tạo venv: python -m venv venv
6. Activate .env: venv\Scripts\activate
7. Ở terminal chạy: pip install -r requirements.txt
8. Chạy app: uvicorn main:app --reload

