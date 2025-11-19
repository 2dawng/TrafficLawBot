import "./App.css";
import AppRoutes from "./routes/AppRoutes";
import ChatPage from "./pages/ChatPage";
import ChatBox from "./pages/ChatBox";
import LandingPage from "./pages/LandingPage";
import Button from "./components/ui/ChatInput";
import AuthCallbackPage from "./pages/AuthCallbackPage";
import { BrowserRouter, Routes, Route } from "react-router-dom";

function App() {
  return (
    <>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/auth/callback" element={<AuthCallbackPage />} />
          <Route path="/chat" element={<ChatPage />} />
        </Routes>
      </BrowserRouter>
    </>
  );
}

export default App;
