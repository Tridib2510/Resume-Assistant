import { useState, useRef } from "react";
import { ChatMessage } from "./ChatMessage";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send, Loader2, Plus } from "lucide-react";
import type { Message } from "../App";

interface ChatInterfaceProps {
  session: {
    id: string;
    hasResume: boolean;
    messages: Message[];
  };
  onUpdateMessages: (sessionId: string, messages: Message[]) => void;
  onResumeUploaded: () => void;
  apiUrl: string;
}

export function ChatInterface({ session, onUpdateMessages, onResumeUploaded, apiUrl }: ChatInterfaceProps) {
  const [input, setInput] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSend = async (overrideInput?: string) => {
    const text = overrideInput ?? input.trim();
    if (!text || isStreaming) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };

    setInput("");
    setIsStreaming(true);

    try {
      const response = await fetch(`${apiUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: session.id, query: text }),
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

        // Process all complete lines (ending with \n or \r\n)
        while (buffer.includes("\n")) {
          const newlineIndex = buffer.indexOf("\n");
          let line = buffer.slice(0, newlineIndex);
          buffer = buffer.slice(newlineIndex + 1);

          // Handle Windows line endings \r\n
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

      // Process any remaining buffer
      if (buffer.startsWith("data: ")) {
        const data = buffer.slice(6).trim();
        if (data && !data.startsWith("[DOC]")) {
          fullContent += data + "\n";
        }
      }

      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: fullContent.trim() || "I couldn't process that request.",
        timestamp: new Date(),
      };

      onUpdateMessages(session.id, [...session.messages, userMsg, assistantMsg]);
    } catch (error) {
      console.error("Chat error:", error);
      const errorMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "Sorry, I encountered an error. Please try again.",
        timestamp: new Date(),
      };
      onUpdateMessages(session.id, [...session.messages, userMsg, errorMsg]);
    } finally {
      setIsStreaming(false);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const uploadId = crypto.randomUUID();
    const userMessage: Message = {
      id: uploadId,
      role: "user",
      content: `Uploading resume: ${file.name}`,
      timestamp: new Date(),
    };

    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append("user_id", uploadId);
      formData.append("query", "tell me about this applicant");
      formData.append("file", file);

      const response = await fetch(`${apiUrl}/upload_resume`, {
        method: "POST",
        body: formData,
      });

      console.log(response)

      if (!response.ok) throw new Error("Upload failed");

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
          const line = buffer.slice(0, newlineIndex);
          buffer = buffer.slice(newlineIndex + 1);

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

      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: fullContent || "Resume uploaded and processed successfully!",
        timestamp: new Date(),
      };

      onUpdateMessages(session.id, [...session.messages, userMessage, assistantMsg]);
      onResumeUploaded();
    } catch (error) {
      console.error("Upload error:", error);
      const errorMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "Sorry, failed to upload resume. Please try again.",
        timestamp: new Date(),
      };
      onUpdateMessages(session.id, [...session.messages, errorMsg]);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
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
    <div className="flex flex-col flex-1 min-h-0">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        className="hidden"
        onChange={handleFileSelect}
      />

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-4">
          {session.messages.map((msg: Message) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}
          {isStreaming && (
            <div className="flex gap-3">
              <div className="flex flex-col space-y-2 rounded-2xl bg-muted p-3">
                <Loader2 className="h-4 w-4 animate-spin" />
              </div>
            </div>
          )}
        </div>
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="p-4 border-t border-border">
        <div className="flex gap-2 items-end max-w-4xl mx-auto">
          <Button
            variant="outline"
            size="icon"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            title="Upload Resume"
          >
            {isUploading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Plus className="h-4 w-4" />
            )}
          </Button>
          <div className="flex-1 relative">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                adjustTextareaHeight();
              }}
              onKeyDown={handleKeyDown}
              placeholder="Ask about the resume..."
              className="min-h-[44px] max-h-[200px] resize-none pr-12"
              disabled={isStreaming}
            />
          </div>
          <Button
            onClick={() => handleSend()}
            disabled={!input.trim() || isStreaming}
            size="icon"
          >
            {isStreaming ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
        <p className="text-xs text-center text-muted-foreground mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}