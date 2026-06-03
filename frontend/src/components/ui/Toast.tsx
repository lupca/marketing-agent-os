"use client";

import React, { createContext, useContext, useState, useCallback } from "react";

type ToastType = "success" | "error" | "info";

interface ToastContextType {
  showToast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toast, setToast] = useState<{ message: string; type: ToastType } | null>(null);

  const showToast = useCallback((message: string, type: ToastType = "success") => {
    setToast({ message, type });
    setTimeout(() => {
      setToast(null);
    }, 4500);
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {toast && (
        <div className="fixed bottom-6 right-6 z-[9999] transition-all duration-300 transform scale-100 opacity-100 animate-fade-in">
          <div className={`flex items-center gap-3 px-4.5 py-3 rounded-xl border shadow-2xl backdrop-blur-md text-xs font-mono font-bold tracking-wider bg-slate-950/90 ${
            toast.type === "success" 
              ? "border-emerald-500/30 text-emerald-400 shadow-emerald-950/20" 
              : toast.type === "error"
              ? "border-rose-500/30 text-rose-400 shadow-rose-950/20"
              : "border-blue-500/30 text-blue-400 shadow-blue-950/20"
          }`}>
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-900 border border-slate-800 text-[10px]">
              {toast.type === "success" ? "✓" : toast.type === "error" ? "✗" : "ℹ"}
            </span>
            <span>{toast.message}</span>
          </div>
        </div>
      )}
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
