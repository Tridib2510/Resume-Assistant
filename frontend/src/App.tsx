import { useState, useRef, useEffect } from "react";
import { ChatInterface } from "./components/ChatInterface";
import { Sidebar } from "./components/Sidebar";
import { Button } from "@/components/ui/button";
import { Menu, Plus, Trash2 } from "lucide-react";
import "./index.css";

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

const API_BASE = "http://localhost:8000";
const API_URL = `${API_BASE}/v1/graph`;

export function App() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
      if (window.innerWidth < 768) {
        setSidebarOpen(false);
      }
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const activeSession = sessions.find((s) => s.id === activeSessionId) || null;

  const createNewSession = () => {
    const newSession: ChatSession = {
      id: crypto.randomUUID(),
      title: "New Chat",
      messages: [],
      hasResume: false,
    };
    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionId(newSession.id);
    if (isMobile) setSidebarOpen(false);
  };

  const deleteSession = (id: string) => {
    setSessions((prev) => prev.filter((s) => s.id !== id));
    if (activeSessionId === id) {
      const remaining = sessions.filter((s) => s.id !== id);
      setActiveSessionId(remaining[0]?.id || null);
    }
  };

  const updateSessionMessages = (sessionId: string, messages: Message[]) => {
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id === sessionId) {
          const title = messages.length > 0
            ? (messages[0]?.content.slice(0, 30) ?? "") + (messages[0]?.content.length ?? 0 > 30 ? "..." : "")
            : s.title;
          return { ...s, messages, title };
        }
        return s;
      })
    );
  };

  const markResumeUploaded = (sessionId: string) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === sessionId ? { ...s, hasResume: true } : s))
    );
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      {/* Mobile overlay */}
      {sidebarOpen && isMobile && (
        <div
          className="fixed inset-0 bg-black/50 z-20"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={(id) => {
          setActiveSessionId(id);
          if (isMobile) setSidebarOpen(false);
        }}
        onNewChat={createNewSession}
        onDeleteSession={deleteSession}
        isOpen={sidebarOpen}
        isMobile={isMobile}
      />

      {/* Main content */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Top bar */}
        <header className="flex items-center gap-2 p-2 border-b border-border bg-background">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="shrink-0"
          >
            <Menu className="h-5 w-5" />
          </Button>
          {activeSession && (
            <span className="text-sm text-muted-foreground truncate">
              {activeSession.title}
            </span>
          )}
          {activeSession?.hasResume && (
            <span className="ml-auto text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
              Resume Loaded
            </span>
          )}
        </header>

        {/* Chat area */}
        {activeSession ? (
          <ChatInterface
            session={activeSession}
            onUpdateMessages={updateSessionMessages}
            onResumeUploaded={() => markResumeUploaded(activeSession.id)}
            apiUrl={API_URL}
          />
        ) : (
          <div className="flex flex-1 items-center justify-center text-muted-foreground">
            <div className="text-center space-y-4">
              <div className="text-6xl">📄</div>
              <p className="text-lg font-medium">No chat selected</p>
              <p className="text-sm">
                Select a chat from the sidebar or start a new one
              </p>
              <Button onClick={createNewSession} className="mt-4">
                <Plus className="h-4 w-4 mr-2" />
                New Chat
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
