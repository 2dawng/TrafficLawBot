import React, { useEffect, useRef, useState } from "react";
import AvatarImg from "../../assets/imgs/avatar.png";
import { Bolt, LogOut } from "lucide-react";

export default function AvatarBubble({ avatarUrl = AvatarImg, size = 10 }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function onDocClick(e) {
      if (!ref.current) return;
      if (!ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  useEffect(() => {
    function onKey(e) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const menuItems = [
    { key: "settings", label: "Cài đặt", icon: Bolt },
    { key: "logout", label: "Đăng xuất", icon: LogOut },
  ];

  return (
    <div className="wrapper flex items-center justify-center">
      <div className="relative inline-block" ref={ref}>
        <button
          onClick={() => setOpen((s) => !s)}
          aria-haspopup="true"
          aria-expanded={open}
          className={`w-${size} h-${size} cursor-pointer rounded-full overflow-hidden border-2 border-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500`}
        >
          <img
            src={avatarUrl}
            alt="avatar"
            className="w-full h-full object-cover"
          />
        </button>

        {/* Menu bubble: appears above the avatar, left-aligned to avatar's left edge */}
        {open && (
          <div className="absolute left-0 bottom-full mb-3 z-50">
            <div className="relative">
              <div className="bg-white/100 text-black rounded-2xl w-48 overflow-hidden">
                <div className="p-0 space-y-1">
                  {menuItems.map((it) => (
                    <button
                      key={it.key}
                      onClick={() => {
                        setOpen(false);
                        if (it.key === "logout") {
                          // Xóa token & user info
                          localStorage.removeItem("access_token");
                          localStorage.removeItem("refresh_token");
                          localStorage.removeItem("user_name");
                          localStorage.removeItem("user_email");
                          localStorage.removeItem("user_avatar");

                          // Điều hướng về trang login
                          window.location.href = "/";
                        }
                        if (it.key === "settings") {
                          console.log("Đi tới trang cài đặt");
                        }
                      }}
                      className="flex flex-row items-center gap-3 w-full text-left px-4 py-4 rounded-lg hover:bg-black/5 transition cursor-pointer"
                    >
                      <span className="flex-none">
                        <it.icon className="w-5 h-5" />
                      </span>
                      <span className="flex-1 text-sm font-medium">
                        {it.label}
                      </span>
                      {it.trailing && (
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          className="w-4 h-4 text-gray-300"
                          fill="none"
                          viewBox="0 0 24 24"
                          strokeWidth="2"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M9 5l7 7-7 7"
                          />
                        </svg>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
