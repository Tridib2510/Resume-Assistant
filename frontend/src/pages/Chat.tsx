import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send, Loader2, Upload, FileText, Sparkles, MessageCircle, CheckCircle } from "lucide-react";
import { Link } from "react-router-dom";
import { Toaster, toast } from "../components/Toaster";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export function Chat() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [userId] = useState(() => crypto.randomUUID());
  const [hasResume, setHasResume] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (overrideInput?: string) => {
    const text = overrideInput ?? input.trim();
    if (!text || isStreaming) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsStreaming(true);

    try {
      const response = await fetch(`${process.env.BUN_PUBLIC_BACKEND_ENDPOINT}/v1/graph/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: localStorage.getItem("user_id"), query: text }),
      });

      if (!response.ok) throw new Error("Chat failed");

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";
      let fullContent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        while (buffer.includes("\n")) {
          const newlineIndex = buffer.indexOf("\n");
          let line = buffer.slice(0, newlineIndex);
          buffer = buffer.slice(newlineIndex + 1);

          if (line.endsWith("\r")) {
            line = line.slice(0, -1);
          }

          if (line.startsWith("data: ")) {
            const data = line.slice(6).trim();
            if (data && !data.startsWith("[DOC]")) {
              fullContent += data + "\n";
            }
          }
        }
      }

      if (buffer.startsWith("data: ")) {
        const data = buffer.slice(6).trim();
        if (data && !data.startsWith("[DOC]")) {
          fullContent += data + "\n";
        }
      }

      // Try to parse LLMResponseStructure to extract generation field
      let generationText = fullContent.trim();
      try {
        const genMatch = fullContent.match(/generation='([^']*)'/);
        if (genMatch?.[1]) {
          generationText = genMatch[1];
        } else {
          // Try to find content after "generation="
          const genContentMatch = fullContent.match(/generation=(.+?)(?:,|\s*confidence|\s*source|\s*missing|$)/s);
          if (genContentMatch?.[1]) {
            generationText = genContentMatch[1].trim();
          }
        }
      } catch {
        // Keep fullContent as fallback
      }

      // Check if the response indicates an invalid/no resume
      if (generationText.includes("Please upload a valid resume")) {
        toast("Please provide a valid resume. The uploaded document does not appear to be a resume.", "error");
        setIsStreaming(false);
        return;
      }

      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: generationText || "I couldn't process that request.",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (error) {
      console.error("Chat error:", error);
      const errorMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "Sorry, I encountered an error. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50 dark:from-slate-950 dark:via-slate-900 dark:to-indigo-950 flex flex-col relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-gradient-to-br from-violet-500/10 to-transparent rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-gradient-to-br from-indigo-500/10 to-transparent rounded-full blur-3xl" />
      </div>

      {/* Header */}
      <header className="relative z-10 border-b border-slate-200/50 dark:border-slate-700/50 bg-white/60 dark:bg-slate-900/60 backdrop-blur-xl">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              to="/"
              className="flex items-center gap-2 text-slate-600 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
            >
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                <FileText className="h-5 w-5 text-white" />
              </div>
            </Link>
            <div>
              <h1 className="text-xl font-bold text-slate-900 dark:text-white">AI Chat Assistant</h1>
              <p className="text-xs text-slate-500">Powered by advanced NLP</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {hasResume && (
              <span className="flex items-center gap-1.5 text-xs bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 px-3 py-1.5 rounded-full font-medium">
                <CheckCircle className="h-3.5 w-3.5" />
                Resume Active
              </span>
            )}
            <Link to="/">
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
              >
                <Upload className="h-3.5 w-3.5" />
                Upload Resume
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Chat Area */}
      <div className="relative z-10 flex-1 flex flex-col max-w-4xl mx-auto w-full">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center space-y-6 py-12">
              <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-2xl shadow-indigo-500/30">
                <MessageCircle className="h-12 w-12 text-white" />
              </div>
              <div className="space-y-2">
                <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Welcome to AI Chat</h2>
                <p className="text-slate-500 dark:text-slate-400 max-w-md">
                  Ask anything about your resume or general questions. Upload your resume first for personalized answers.
                </p>
              </div>
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <Sparkles className="h-4 w-4 text-indigo-500" />
                AI processes your requests in real-time
              </div>
            </div>
          )}

          {messages.map((msg, index) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} animate-in fade-in slide-in-from-bottom-2 duration-500`}
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <div className="flex gap-3 max-w-[85%]">
                {msg.role === "assistant" && (
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shrink-0 mt-1 shadow-lg shadow-indigo-500/20">
                    <Sparkles className="h-4 w-4 text-white" />
                  </div>
                )}
                <div
                  className={`rounded-2xl px-5 py-3 shadow-lg ${
                    msg.role === "user"
                      ? "bg-gradient-to-r from-indigo-600 to-violet-600 text-white shadow-indigo-500/30"
                      : "bg-white/80 dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200/50 dark:border-slate-700/50 text-slate-900 dark:text-white"
                  }`}
                >
                  <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                  <p
                    className={`text-xs mt-2 ${
                      msg.role === "user" ? "text-white/60" : "text-slate-400"
                    }`}
                  >
                    {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </p>
                </div>
              </div>
            </div>
          ))}

          {isStreaming && (
            <div className="flex justify-start">
              <div className="flex gap-3 max-w-[85%]">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shrink-0 shadow-lg shadow-indigo-500/20">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
                <div className="bg-white/80 dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200/50 dark:border-slate-700/50 rounded-2xl px-5 py-4 shadow-lg">
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" style={{ animationDelay: "0ms" }} />
                      <span className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" style={{ animationDelay: "150ms" }} />
                      <span className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" style={{ animationDelay: "300ms" }} />
                    </div>
                    <span className="text-sm text-slate-500">Thinking...</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-6 border-t border-slate-200/50 dark:border-slate-700/50 bg-white/40 dark:bg-slate-900/40 backdrop-blur-xl">
          <div className="flex gap-3 items-end max-w-3xl mx-auto">
            <div className="flex-1 relative">
              <Textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  adjustTextareaHeight();
                }}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your resume..."
                className="min-h-[48px] max-h-[200px] resize-none rounded-xl border-2 bg-white/80 dark:bg-slate-900/80 backdrop-blur py-3 px-4 pr-12 focus:border-indigo-500 focus:ring-0 transition-all"
                disabled={isStreaming}
              />
              <Button
                onClick={() => handleSend()}
                disabled={!input.trim() || isStreaming}
                size="icon"
                className="absolute right-2 bottom-2 w-9 h-9 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white shadow-lg shadow-indigo-500/30 transition-all disabled:opacity-50"
              >
                {isStreaming ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
          <p className="text-xs text-center text-slate-400 mt-3 max-w-3xl mx-auto">
            Press <kbd className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 rounded text-xs">Enter</kbd> to send, <kbd className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 rounded text-xs">Shift + Enter</kbd> for new line
          </p>
        </div>
      </div>

      {/* Toast Notifications */}
      <Toaster />
    </div>
  );
}