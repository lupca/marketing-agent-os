"use client";

import React, { useEffect } from "react";
import { X } from "lucide-react";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  headerIcon?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  maxWidth?: "sm" | "md" | "lg" | "xl" | "2xl" | "3xl" | "4xl";
}

export function Modal({
  isOpen,
  onClose,
  title,
  subtitle,
  headerIcon,
  children,
  footer,
  maxWidth = "md",
}: ModalProps) {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };

    if (isOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleEscape);
    }

    return () => {
      document.body.style.overflow = "unset";
      window.removeEventListener("keydown", handleEscape);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const maxWidthClasses = {
    sm: "max-w-sm",
    md: "max-w-md",
    lg: "max-w-lg",
    xl: "max-w-xl",
    "2xl": "max-w-2xl",
    "3xl": "max-w-3xl",
    "4xl": "max-w-4xl",
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 animate-fade-in">
      <div className={`bg-slate-950 border border-slate-800 rounded-xl w-full ${maxWidthClasses[maxWidth]} flex flex-col shadow-2xl max-h-[90vh] overflow-hidden`}>
        {/* Header */}
        <div className="p-4 border-b border-slate-900 flex justify-between items-center bg-slate-950">
          <div className="flex items-center gap-2.5">
            {headerIcon && <span className="text-xl leading-none select-none">{headerIcon}</span>}
            <div>
              <h4 className="text-xs font-bold text-slate-200 uppercase tracking-widest font-mono">
                {title}
              </h4>
              {subtitle && (
                <p className="text-[9px] text-slate-500 font-mono mt-0.5">
                  {subtitle}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-200 h-6 w-6 flex items-center justify-center rounded border border-slate-900 hover:bg-slate-900 transition-all cursor-pointer font-bold"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-950/40">
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div className="p-4 border-t border-slate-900 flex justify-end gap-2 bg-slate-950">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
