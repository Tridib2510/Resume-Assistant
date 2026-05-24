import { useEffect, useState } from "react";
import { X } from "lucide-react";

interface Toast {
  id: string;
  message: string;
  type: "error" | "success" | "info";
}

let toastIdCounter = 0;
const listeners: Array<(toast: Toast) => void> = [];

export function toast(message: string, type: "error" | "success" | "info" = "info") {
  const newToast: Toast = {
    id: `toast-${++toastIdCounter}`,
    message,
    type,
  };
  listeners.forEach((listener) => listener(newToast));
}

export function Toaster() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const listener = (toast: Toast) => {
      setToasts((prev) => [...prev, toast]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== toast.id));
      }, 4000);
    };
    listeners.push(listener);
    return () => {
      const index = listeners.indexOf(listener);
      if (index > -1) listeners.splice(index, 1);
    };
  }, []);

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`flex items-center gap-3 px-5 py-4 rounded-2xl shadow-2xl backdrop-blur-xl animate-in slide-in-from-right ${
            t.type === "error"
              ? "bg-red-50/90 dark:bg-red-950/90 border border-red-200 dark:border-red-800"
              : t.type === "success"
              ? "bg-emerald-50/90 dark:bg-emerald-950/90 border border-emerald-200 dark:border-emerald-800"
              : "bg-slate-50/90 dark:bg-slate-900/90 border border-slate-200 dark:border-slate-700"
          }`}
        >
          <span
            className={`text-sm font-medium ${
              t.type === "error"
                ? "text-red-700 dark:text-red-300"
                : t.type === "success"
                ? "text-emerald-700 dark:text-emerald-300"
                : "text-slate-700 dark:text-slate-300"
            }`}
          >
            {t.message}
          </span>
          <button
            onClick={() => setToasts((prev) => prev.filter((to) => to.id !== t.id))}
            className={`p-1 rounded-lg hover:bg-black/10 dark:hover:bg-white/10 ${
              t.type === "error"
                ? "text-red-500"
                : t.type === "success"
                ? "text-emerald-500"
                : "text-slate-500"
            }`}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  );
}