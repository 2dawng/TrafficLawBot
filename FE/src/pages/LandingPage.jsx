// src/pages/LandingPage.jsx
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import LoginCard from "../components/auth/SignInForm";
import { Car, Globe, MapPin, Phone, DoorOpen, UserPlus } from "lucide-react";
import Bot from "../assets/imgs/bot.gif";;

export default function LandingPage() {
  const [isLoaded, setIsLoaded] = useState(false);
  useEffect(() => {
    setIsLoaded(true);
  }, []);
  return (
    <>
      <div className="wrapper flex flex-col h-full gap-10 px-10 py-5">
        <header
          className={`glass-nav sticky top-0 z-50 backdrop-blur-lg gradient shadow-sm mt-2 rounded-full ${isLoaded ? "animate-slide-down" : "opacity-0"
            }`}
        >
          <div className="flex justify-between items-center px-6 py-4 md:px-10">
            <div className="flex items-center gap-3 font-black text-xl">
              <div className="avt-img">
                <img
                  className="w-10 h-10"
                  src="/src/assets/imgs/apple-icon-180x180.png"
                  alt=""
                />
              </div>
              <span className="tracking-widest uppercase">TrafficBot</span>
            </div>
            <div className="flex items-center gap-4">
              <button className="cursor-pointer flex items-center gap-2 bg-black text-white px-4 py-2 rounded-full text-sm font-semibold">
                <Globe className="w-4 h-4" /> VI
              </button>
              <button className="cursor-pointer bg-white/90 text-black px-5 py-2.5 rounded-full font-semibold text-sm shadow-md hover:shadow-lg transition-all hover:-translate-y-0.5">
                Dùng thử TrafficBot
              </button>
            </div>
          </div>
        </header>
        <main className="flex flex-row lg:flex-row items-center justify-center gap-10 max-w-full mx-auto h-full w-full rounded-4xl">
          {/* Map Section */}
          <div
            className={`map-section w-full flex flex-col gap-10 h-full flex-6 ${isLoaded ? "animate-slide-left" : "opacity-0"
              }`}
          >
            <div className="relative w-full h-60 min-h-100 rounded-4xl overflow-hidden shadow-2xl flex-1">
              <img
                src="/src/assets/imgs/map.jpg"
                alt="City map"
                className="inset-0 object-cover absolute w-full h-full"
              />
              <div className="absolute inset-0 bg-gradient-to-br from-yellow-100/90 via-yellow-200/70 to-yellow-300/80 rounded-3xl flex items-center justify-center p-8">
                <div className="traffic-police-anm w-60 h-60 relative">
                  <img
                    className="w-full h-full object-cover absolute"
                    src="/src/assets/imgs/Traffic Police Loading Screen Animation.gif"
                    alt=""
                  />
                </div>
                <h2 className="text-4xl md:text-5xl font-black text-center leading-tight">
                  Lái xe thông minh,
                  <br />
                  <span className="text-green-600">
                    An toàn hơn bao giờ hết
                  </span>
                </h2>
              </div>
            </div>
            <div className="introduce px-6 py-6 rounded-4xl relative overflow-hidden z-0 shadow-[0_3px_8px_rgba(0, 0, 0, 0.24)] ">
              <h3 className="uppercase text-base tracking-widest pb-2 font-extrabold">
                Traffic law
              </h3>
              <div className="flex flex-row align-center gap-10">
                <div className="flex flex-col">
                  <p className="font-bold text-3xl py-2">
                    Trợ lý AI luật giao thông
                  </p>
                  <p className="text-sm">
                    Tra cứu quy định xử phạt, chuẩn bị giấy tờ và luyện tập đối
                    thoại với lực lượng chức năng trước khi bạn bước ra đường.
                  </p>
                </div>
                <div className="flex flex-row gap-3">
                  <button className="text-center text-sm border border-y-black bg-amber-300 text-black-600 rounded-full px-3 cursor-pointer h-fit py-2 font-bold">
                    Tài liệu cập nhật 2026
                  </button>
                  <button className="text-center text-sm border border-y-black bg-transparent text-black-600 rounded-full px-3 cursor-pointer h-fit py-2 font-bold">
                    Yêu cầu tích hợp API
                  </button>
                </div>
              </div>
              <div className="flex flex-row justify-space-between gap-4 mt-10">
                <div className="flex flex-row items-center text-sm h-fit px-3 py-2 border rounded-full gap-3">
                  {" "}
                  <div className="w-3 h-3 rounded-full bg-green-800 flex border flex-none"></div>{" "}
                  Luồng mô phỏng theo Nghị định 100/2019 và 123/2021
                </div>
                <div className="flex flex-row items-center text-sm h-fit px-3 py-2 border rounded-full gap-3">
                  {" "}
                  <div className="w-3 h-3 rounded-full bg-blue-700 flex border flex-none"></div>{" "}
                  Độ chính xác ưu tiên, có trích dẫn nguồn tham khảo
                </div>
                <div className="flex flex-row items-center text-sm h-fit px-3 py-2 border rounded-full gap-3">
                  {" "}
                  <div className="w-3 h-3 rounded-full bg-yellow-500 flex border flex-none"></div>{" "}
                  Đề xuất hành động tiếp theo theo tình huống cụ thể
                </div>
              </div>
            </div>
          </div>

          {/* Auth Section */}
          <div
            className={`flex-4 auth-section w-full flex flex-col items-center h-full justify-center rounded-4xl ${isLoaded ? "animate-slide-right" : "opacity-0"
              }`}
          >
            <div className="flex items-center gap-4 mb-6 relative">
              <div className="w-20 h-20 bg-white rounded-full flex items-center justify-center shadow-xl animate-float absolute left-[-100px]">
                <img src={Bot} alt="Robot Gif" />
              </div>
              <h1 className="text-5xl md:text-6xl font-black tracking-widest typewriter inline-block">
                WELCOME
              </h1>
            </div>

            <p className="text-center text-gray-700 max-w-md mb-6 leading-relaxed italic">
              "Trợ lý AI <strong>TrafficBot</strong> sẽ giúp bạn tra cứu luật
              giao thông mới nhất và chính xác nhất."
            </p>
            <div className="login-btn w-fit h-fit p-10 rounded-4xl bg-white">
              <div className="text-center mb-8">
                <p className="text-gray-500 text-2xs">
                  Đăng nhập để tiếp tục sử dụng TrafficBot
                </p>
              </div>

              <button
                onClick={() => {
                  const apiUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
                  window.location.href = `${apiUrl}/auth/login`;
                }}
                className="cursor-pointer w-full flex items-center justify-center gap-3 py-3.5 
                   border border-gray-300 rounded-full font-semibold bg-white
                   hover:shadow-lg transition-all"
              >
                <img
                  src="https://www.google.com/favicon.ico"
                  alt="Google"
                  className="w-5 h-5"
                />
                Đăng nhập với Google
              </button>

              <p className="text-xs text-gray-500 text-center mt-6 leading-relaxed">
                Bằng việc tiếp tục, bạn đồng ý với{" "}
                <a
                  href="#"
                  className="font-bold hover:underline transition-all hover:text-blue-700"
                >
                  Chính sách bảo mật
                </a>{" "}
                của TrafficBot.
              </p>
            </div>
            {/* Auth Card */}
            {/* <AuthSwitcher /> */}
          </div>
        </main>
      </div>
    </>
  );
}
