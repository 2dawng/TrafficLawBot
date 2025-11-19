import React, { useState, useEffect, useRef } from "react";
import ChatInput from "../components/ui/ChatInput";

function App() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      text: "Xin chào! Tôi là AI Assistant giao thông. Tôi có thể giúp gì cho bạn?",
      sender: "ai",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = () => {
    if (input.trim() === "") return;

    const userMessage = {
      id: Date.now(),
      text: input,
      sender: "user",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsTyping(true);

    setTimeout(() => {
      const aiReplies = [
        "Cảm ơn bạn đã hỏi! Tôi đang kiểm tra luật liên quan...",
        "Rất thú vị! Bạn có muốn tôi giải thích chi tiết không?",
        "Theo quy định hiện hành, câu trả lời là như sau...",
        "Đó là một câu hỏi quan trọng! Hãy để tôi hướng dẫn bạn...",
        "Tôi có thể cung cấp thêm thông tin về luật giao thông.",
      ];
      const reply = aiReplies[Math.floor(Math.random() * aiReplies.length)];

      const aiMessage = {
        id: Date.now() + 1,
        text: reply,
        sender: "ai",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, aiMessage]);
      setIsTyping(false);
    }, 1200 + Math.random() * 800);
  };


  return (
    <div className="flex flex-col h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-gradient-to-r from-yellow-500 via-red-500 to-red-700 text-white p-5 shadow-md flex flex-col items-center">
        <h1 className="text-2xl font-bold">AI Giao Thông</h1>
        <p className="text-sm opacity-90 mt-1">
          Hỗ trợ bạn tra cứu luật và biển báo
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${
              msg.sender === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-xs md:max-w-md lg:max-w-lg px-4 py-3 rounded-2xl shadow-md border ${
                msg.sender === "user"
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-800 border-gray-300"
              } relative`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
              <span
                className={`text-xs mt-1 block ${
                  msg.sender === "user"
                    ? "text-blue-100"
                    : "text-gray-500"
                }`}
              >
                {msg.timestamp.toLocaleTimeString("vi-VN", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
              {msg.sender === "ai" && (
                <span className="absolute top-0 -left-2 w-3 h-3 bg-red-500 rounded-full animate-pulse"></span>
              )}
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-white px-4 py-3 rounded-2xl shadow-md border border-gray-300">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: "0.1s" }}
                ></div>
                <div
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: "0.2s" }}
                ></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ✅ Chat Input */}
      <div className="border-t border-gray-300 bg-white p-4 shadow-inner">
        <ChatInput onSend={handleSend} />
      </div>
    </div>
  );
}

export default App;
