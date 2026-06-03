"use client";

import React from "react";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  glowColor?: "blue" | "emerald" | "indigo" | "amber" | "purple" | "rose" | "none";
}

export function Card({ children, className = "", glowColor = "none", ...props }: CardProps) {
  const glowClasses = {
    blue: "absolute top-0 right-0 h-12 w-12 bg-blue-500/10 blur-xl group-hover:bg-blue-500/20 transition-all",
    emerald: "absolute top-0 right-0 h-12 w-12 bg-emerald-500/10 blur-xl group-hover:bg-emerald-500/20 transition-all",
    indigo: "absolute top-0 right-0 h-12 w-12 bg-indigo-500/10 blur-xl group-hover:bg-indigo-500/20 transition-all",
    amber: "absolute top-0 right-0 h-12 w-12 bg-amber-500/10 blur-xl group-hover:bg-amber-500/20 transition-all",
    purple: "absolute top-0 right-0 h-12 w-12 bg-purple-500/10 blur-xl group-hover:bg-purple-500/20 transition-all",
    rose: "absolute top-0 right-0 h-12 w-12 bg-rose-500/10 blur-xl group-hover:bg-rose-500/20 transition-all",
    none: "",
  };

  const shadowClasses = {
    blue: "hover:shadow-blue-500/5",
    emerald: "hover:shadow-emerald-500/5",
    indigo: "hover:shadow-indigo-500/5",
    amber: "hover:shadow-amber-500/5",
    purple: "hover:shadow-purple-500/5",
    rose: "hover:shadow-rose-500/5",
    none: "",
  };

  return (
    <div
      className={`bg-slate-900/40 backdrop-blur-md border border-slate-850 hover:border-slate-700/80 rounded-xl p-4 hover:-translate-y-1 hover:shadow-xl ${shadowClasses[glowColor]} transition-all duration-300 flex flex-col gap-2 relative overflow-hidden group ${className}`}
      {...props}
    >
      {glowColor !== "none" && <div className={glowClasses[glowColor]}></div>}
      {children}
    </div>
  );
}
