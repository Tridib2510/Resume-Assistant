import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ResumeUpload } from "./pages/ResumeUpload";
import { Chat } from "./pages/Chat";
export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  hasResume: boolean;
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ResumeUpload />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;