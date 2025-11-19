"use client";

import React, { useState, useEffect, useRef } from "react";
import RobotLogo from "../assets/imgs/botLogo.gif";
import {
  Compass,
  BookOpen,
  Plug,
  FileText,
  GraduationCap,
  Image,
  Code,
  Lightbulb,
  Menu,
  X,
  Sparkles,
  SendHorizontal,
  Send,
  Plus,
} from "lucide-react";
import AvatarBubble from "../components/ui/AvatarBubble";

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isLoaded, setIsLoaded] = useState(false);

  // ==== STATE CHAT ====
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]); // {from:'user'|'bot', text:string}
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);

  const userAvatar = localStorage.getItem("user_avatar");
  const hasChat = messages.length > 0;

  const textareaRef = useRef(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleChange = (e) => {
    setMessage(e.target.value);

    const el = textareaRef.current;
    el.style.height = "auto"; // reset height
    el.style.height = el.scrollHeight + "px"; // set to full height
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault(); // chặn xuống dòng mặc định
      handleSend(); // gọi hàm gửi
    }
  };

  const handleResetChat = () => {
    setMessages([]);
    setMessage("");
  };

  useEffect(() => {
    setIsLoaded(true);
    const token = localStorage.getItem("access_token");
    if (!token) {
      window.location.href = "/";
    }

    // gọi API lấy lịch sử
    const fetchHistory = async () => {
      try {
        const res = await fetch("http://localhost:8000/chat/history", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!res.ok) {
          console.error("Lỗi lấy history:", await res.text());
          return;
        }

        const data = await res.json();
        // data từ BE: [{ message, response, timestamp }]
        setHistory(data);
      } catch (err) {
        console.error("Lỗi fetch history:", err);
      }
    };

    fetchHistory();
  }, []);

  const features = [
    {
      icon: <FileText className="w-6 h-6" />,
      title: "Tư vấn luật",
      description: "Hỗ trợ giải đáp mọi thắc mắc về luật giao thông Việt Nam",
      color: "from-blue-400 to-cyan-400",
      question: "Hãy tư vấn giúp tôi về luật giao thông đường bộ hiện hành.",
    },
    {
      icon: <GraduationCap className="w-6 h-6" />,
      title: "Ôn thi GPLX",
      description: "Luyện tập 450 câu hỏi sát hạch lái xe chính thức",
      color: "from-purple-400 to-pink-400",
      question:
        "Hướng dẫn tôi cách ôn thi giấy phép lái xe và cấu trúc đề thi.",
    },
    {
      icon: <Image className="w-6 h-6" />,
      title: "Nhận diện biển báo",
      description: "Tải ảnh lên để AI phân tích và giải thích biển báo",
      color: "from-orange-400 to-red-400",
      question:
        "Các nhóm biển báo giao thông chính và ý nghĩa của chúng là gì?",
    },
    {
      icon: <Code className="w-6 h-6" />,
      title: "Tra cứu nhanh",
      description: "Tìm kiếm mức phạt, quy định theo từ khóa",
      color: "from-green-400 to-emerald-400",
      question:
        "Cho tôi biết một số mức phạt phổ biến khi tham gia giao thông đường bộ.",
    },
    {
      icon: <Lightbulb className="w-6 h-6" />,
      title: "Mẹo lái xe an toàn",
      description: "Gợi ý tình huống thực tế và cách xử lý đúng luật",
      color: "from-yellow-400 to-amber-400",
      question:
        "Gợi ý cho tôi một số mẹo lái xe an toàn và tuân thủ luật giao thông.",
    },
  ];

  const sidebarItems = [
    { icon: <Plus className="w-5 h-5" />, label: "Đoạn chat mới" },
    { icon: <BookOpen className="w-5 h-5" />, label: "Thư viện luật" },
    { icon: <Plug className="w-5 h-5" />, label: "Tiện ích" },
  ];

  const formatTime = (isoString) => {
    if (!isoString) return "";

    const date = new Date(isoString);
    const now = new Date();

    // chuẩn hóa để so sánh: bỏ giờ phút giây
    const d = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const n = new Date(now.getFullYear(), now.getMonth(), now.getDate());

    const diffTime = n - d;
    const diffDays = diffTime / (1000 * 60 * 60 * 24);

    if (diffDays === 0) return "Hôm nay";
    if (diffDays === 1) return "Hôm qua";

    // nếu không phải hôm nay/hôm qua → return dd/mm/yyyy
    return date.toLocaleDateString("vi-VN");
  };

  // ==== HÀM GỬI CHUNG ====
  const sendMessage = async (text) => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      alert("Bạn chưa đăng nhập hoặc token đã hết hạn.");
      window.location.href = "/";
      return;
    }

    const trimmed = text.trim();
    if (!trimmed) return;

    // clear ô input
    setMessage("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    // push câu hỏi của user
    setMessages((prev) => [...prev, { from: "user", text: trimmed }]);

    try {
      setLoading(true);

      const res = await fetch("http://localhost:8000/chat/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: trimmed }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        console.error("Lỗi từ backend:", err);
        alert("Gọi API chat lỗi. Kiểm tra console.");
        return;
      }

      const reply = await res.text();

      setMessages((prev) => [...prev, { from: "bot", text: reply }]);

      // thêm record mới vào history để hiện bên trái
      setHistory((prev) => [
        {
          message: trimmed,
          response: reply,
          timestamp: new Date().toISOString(),
        },
        ...prev, // mới nhất nằm trên cùng
      ]);
    } catch (error) {
      console.error("Lỗi khi gọi API:", error);
      alert("Không gọi được backend. Kiểm tra lại server.");
    } finally {
      setLoading(false);
    }
  };

  const handleSend = () => {
    sendMessage(message);
  };

  const handleFeatureClick = (q) => {
    if (!q) return;
    sendMessage(q);
  };

  return (
    <>
      <div className="h-full">
        <div className="flex h-full gap-3 px-4 py-4">
          {/* Sidebar */}
          <aside
            className={`${
              sidebarOpen ? "w-80" : "w-0 lg:w-20"
            } transition-all duration-300 bg-white/5 backdrop-blur-xl overflow-hidden flex flex-col rounded-4xl overflow-y-scroll ${
              isLoaded ? "animate-slide-left" : "opacity-0"
            }`}
          >
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-15 h-15 rounded-full relative overflow-hidden flex-none">
                    <img
                      className="w-full h-full absolute bg-cover"
                      src={RobotLogo}
                      alt="no img"
                    />
                  </div>
                  {sidebarOpen && (
                    <div>
                      <h1 className="text-xl font-bold text-gray-900">
                        TrafficBot
                      </h1>
                    </div>
                  )}
                </div>
                <button
                  onClick={() => setSidebarOpen(!sidebarOpen)}
                  className="lg:hidden text-gray-500 hover:text-gray-700"
                >
                  {sidebarOpen ? (
                    <X className="w-5 h-5" />
                  ) : (
                    <Menu className="w-5 h-5" />
                  )}
                </button>
              </div>
            </div>

            {/* Navigation */}
            <nav className="p-4 space-y-1">
              {sidebarItems.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    if (item.label === "Đoạn chat mới") {
                      handleResetChat();
                    }
                  }}
                  className={`w-full cursor-pointer flex items-center gap-3 px-3 py-3 rounded-xl transition-all text-gray-600 hover:bg-white`}
                >
                  {item.icon}
                  {sidebarOpen && (
                    <span className="flex-1 text-left font-medium">
                      {item.label}
                    </span>
                  )}
                </button>
              ))}
            </nav>

            {/* Recent Chats */}
            {sidebarOpen && (
              <div className="flex-1 flex flex-col border-t border-b border-gray-200 min-h-0">
                <div className="p-4 shrink-0 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-gray-700">
                    Cuộc trò chuyện gần đây
                  </h3>
                </div>
                <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-2">
                  {history.map((chat, idx) => (
                    <button
                      key={idx}
                      className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-gray-100 transition-all text-left cursor-pointer"
                      onClick={() => {
                        // nếu sau này bạn muốn click để load lại đoạn chat đó thì xử lý ở đây
                        // tạm thời mình chỉ console.log
                        console.log("Clicked history item:", chat);
                      }}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {chat.message}
                        </p>
                        <p className="text-xs text-gray-500">
                          {formatTime(chat.timestamp)}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* User Info */}
            {sidebarOpen && (
              <div className="px-6 py-4 border-b border-gray-200 mt-auto shrink-0">
                <div className="flex items-center gap-3">
                  <AvatarBubble avatarUrl={userAvatar} />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">
                      {localStorage.getItem("user_name") || "User"}
                    </p>
                    <p className="text-xs text-gray-500">
                      {localStorage.getItem("user_email") || "user@email.com"}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </aside>

          {/* Main Content */}
          <main
            className={`relative flex-1 flex flex-col main-chat rounded-4xl items-center justify-center bg-white/5 backdrop-blur-xl px-4 py-4 ${
              isLoaded ? "animate-slide-right" : "opacity-0"
            }`}
          >
            <div className="chatArea flex-1 flex flex-col h-full">
              {/* HEADER – chỉ hiện nếu chưa chat */}
              {!hasChat && (
                <header className="px-8 py-6">
                  <div className="text-center">
                    <h1 className="text-4xl font-bold text-gray-900">
                      Chào mừng đến với TrafficBot
                    </h1>
                    <p className="text-xl text-gray-600">
                      Trợ lý AI chuyên về luật giao thông Việt Nam
                    </p>
                  </div>
                </header>
              )}

              {/* KHỐI CUỘN CHAT */}
              <div className="chat-area flex-1 overflow-y-auto px-8 pb-4 mb-3">
                <div className="max-w-7xl mx-auto">
                  {/* 5 CARD — chỉ hiện khi CHƯA có chat */}
                  {!hasChat && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
                      {features.map((feature, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleFeatureClick(feature.question)}
                          className={`flex flex-col items-start bg-white/70 backdrop-blur-xl rounded-2xl p-6 border 
                border-gray-200 hover:border-gray-300 transition-all hover:shadow-lg hover:-translate-y-1
                ${isLoaded ? "animate-slide-down" : "opacity-0"}`}
                        >
                          <div
                            className={`w-12 h-12 bg-linear-to-br ${feature.color} rounded-xl 
                flex items-center justify-center text-white mb-4`}
                          >
                            {feature.icon}
                          </div>
                          <h3 className="font-semibold text-gray-900 mb-2">
                            {feature.title}
                          </h3>
                          <p className="text-sm text-gray-600 text-start">
                            {feature.description}
                          </p>
                        </button>
                      ))}
                    </div>
                  )}

                  {/* LỊCH SỬ CHAT */}
                  {hasChat && (
                    <div className="max-w-4xl mx-auto mb-6 space-y-4">
                      {messages.map((m, idx) => (
                        <div
                          key={idx}
                          className={`flex items-end gap-1 relative ${
                            m.from === "user" ? "justify-end" : "justify-start"
                          }`}
                        >
                          {/* Avatar chatbot (chỉ hiện khi KHÔNG phải user) */}
                          {m.from !== "user" && (
                            <div className="w-8 h-8 rounded-full relative overflow-hidden -mb-8 flex-none">
                              <img
                                className="absolute w-full h-full object-cover"
                                src="/public/favicon.avif"
                                alt="Chatbot"
                              />
                            </div>
                          )}
                          <div
                            className={`px-4 py-2 rounded-2xl max-w-[80%] whitespace-pre-wrap text-sm wrap-break-word bubble-pop ${
                              m.from === "user"
                                ? "bg-[#FF9E8C] text-black rounded-br-none"
                                : "bg-[#FFF7FB] text-gray-800 rounded-bl-none shadow-[0_2px_5px_-1px_rgba(50,50,93,0.25)] shadow-[0_1px_3px_-1px_rgba(0,0,0,0.3)]"
                            }`}
                          >
                            {m.text}
                          </div>
                        </div>
                      ))}
                      {loading && (
                        <div className="flex justify-start">
                          <div
                            className="
            px-4 py-2 rounded-2xl max-w-[80%]
            bg-white text-gray-800
            animate-fade-up
          "
                          >
                            <div className="flex items-center gap-2">
                              <div className="w-6 h-6 rounded-full relative overflow-hidden">
                                <img
                                  className="absolute w-full h-full object-cover"
                                  src="/public/favicon.avif"
                                  alt=""
                                />
                              </div>
                              <div className="flex gap-1">
                                <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" />
                                <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce [animation-delay:0.15s]" />
                                <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce [animation-delay:0.3s]" />
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                      <div ref={bottomRef}></div>
                    </div>
                  )}
                </div>
              </div>

              {/* Ô NHẬP TIN NHẮN - luôn nằm dưới */}
              <div className="chat-input bg-transparent">
                <div className="max-w-4xl mx-auto px-8 py-3">
                  {!hasChat && (
                    <div className="text-center mb-4">
                      <p className="text-gray-700 font-medium">
                        TrafficBot có thể giúp gì cho bạn hôm nay?
                      </p>
                    </div>
                  )}
                  <div className="flex gap-2 relative rounded-4xl  px-1.5 py-1 items-center bg-amber-50">
                    <textarea
                      ref={textareaRef}
                      className="w-full p-3 text-sm resize-none overflow-hidden focus:outline-none"
                      value={message}
                      onChange={handleChange}
                      onKeyDown={handleKeyDown}
                      placeholder="Nhập câu hỏi…"
                      rows={1}
                    />

                    <button
                      onClick={handleSend}
                      disabled={loading}
                      className="
      h-12 w-12 flex items-center justify-center rounded-full
      bg-amber-400 text-black flex-none
      shadow-md shadow-amber-200/40
      hover:bg-amber-500 hover:shadow-lg hover:shadow-amber-300/50
      active:scale-95 
      transition-all duration-200
      disabled:opacity-50 disabled:cursor-not-allowed
      cursor-pointer
    "
                    >
                      {loading ? (
                        <Send size={18} />
                      ) : (
                        <SendHorizontal size={18} />
                      )}
                    </button>
                  </div>

                  <div className="flex items-center justify-center">
                    <div className="text-xs mt-2">Chatbot có thể bị lỗi!</div>
                  </div>
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>
    </>
  );
}
