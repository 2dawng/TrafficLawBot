import React, { useState } from "react";
import { Send } from "lucide-react";

export default function ChatInput({onSend}) {
  const [searchQuery, setSearchQuery] = useState("");
  
  const handleSend = () => {
    if (searchQuery.trim() === "") return;
    onSend(searchQuery);
    setSearchQuery("");
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }
  return (
    <>
      <div className="flex items-center gap-3 mb-4">
        <div className="flex-1 relative flex gap-3 items-center border rounded-full overflow-hidden border-gray-300 px-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Hỏi về luật giao thông, mức phạt, biển báo..."
            className="flex-1 px-2 py-3 pr-12 focus:outline-none transition-all"
          />
          <button className="rounded-full cursor-pointer w-10 h-10 flex items-center justify-center bg-linear-to-r from-blue-500 to-purple-600 text-white p-3 hover:from-blue-600 hover:to-purple-700 transition-all">
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </>
  );
}
