import { Button } from "@/components/ui/button";
import { Plus, Trash2, Menu, X, MessageSquare } from "lucide-react";
import type { ChatSession } from "../App";

interface SidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onDeleteSession: (id: string) => void;
  isOpen: boolean;
  isMobile: boolean;
}

export function Sidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  isOpen,
  isMobile,
}: SidebarProps) {
  return (
    <>
      {/* Mobile close button */}
      {isMobile && isOpen && (
        <Button
          variant="ghost"
          size="icon"
          className="absolute top-2 right-2 z-30"
          onClick={() => {}}
        >
          <X className="h-5 w-5" />
        </Button>
      )}

      {/* Sidebar */}
      <aside
        className={`${
          isOpen ? "translate-x-0" : "-translate-x-full"
        } ${isMobile ? "fixed inset-y-0 left-0 z-30 w-64" : "relative"} flex flex-col border-r border-border bg-background transition-transform duration-200 ease-in-out`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          {!isMobile && (
            <h1 className="font-semibold text-lg flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              Resume Chat
            </h1>
          )}
          <Button variant="ghost" size="icon" onClick={onNewChat}>
            <Plus className="h-5 w-5" />
          </Button>
        </div>

        {/* Sessions list */}
        <nav className="flex-1 overflow-y-auto p-2 space-y-1">
          {sessions.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              <p className="text-sm">No chats yet</p>
              <Button variant="link" onClick={onNewChat} className="mt-2">
                Create your first chat
              </Button>
            </div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                className={`group relative flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors cursor-pointer ${
                  activeSessionId === session.id
                    ? "bg-muted font-medium"
                    : "hover:bg-muted/50"
                }`}
                onClick={() => onSelectSession(session.id)}
              >
                <MessageSquare className="h-4 w-4 shrink-0" />
                <span className="truncate flex-1">{session.title}</span>
                {session.hasResume && (
                  <span className="h-2 w-2 rounded-full bg-green-500 shrink-0" title="Resume loaded" />
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  className="opacity-0 group-hover:opacity-100 h-6 w-6 shrink-0"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteSession(session.id);
                  }}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            ))
          )}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-border text-xs text-muted-foreground">
          {sessions.length} chat{sessions.length !== 1 ? "s" : ""}
        </div>
      </aside>
    </>
  );
}