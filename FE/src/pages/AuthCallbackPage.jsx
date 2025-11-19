// src/pages/AuthCallbackPage.jsx
import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";

export default function AuthCallbackPage() {
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(location.search);

    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token");
    const name = params.get("name");
    const email = params.get("email");
    const picture = params.get("picture");
    
    console.log("callback params:", {
    accessToken,
    refreshToken,
    name,
    email,
    picture,
  });


    if (accessToken && refreshToken) {
      // Lưu token & user info
      localStorage.setItem("access_token", accessToken);
      localStorage.setItem("refresh_token", refreshToken);
      if (name) localStorage.setItem("user_name", name);
      if (email) localStorage.setItem("user_email", email);
      if (picture) localStorage.setItem("user_avatar", picture);

      // Điều hướng sang trang chat
      navigate("/chat");
    } else {
      // Thiếu token -> quay lại trang đăng nhập
      navigate("/");
    }
  }, [location, navigate]);

  return (
    <div className="w-full h-screen flex items-center justify-center">
      <p className="text-lg font-semibold">Đang đăng nhập, vui lòng chờ...</p>
    </div>
  );
}
