"use client";

import React from "react";
import { HelpCircle } from "lucide-react";

interface SliderProps {
  label: string;
  tooltip?: string;
  min: number;
  max: number;
  step?: number;
  value: number;
  onChange: (value: number) => void;
  formatValue?: (value: number) => string;
  accentColor?: "blue" | "indigo" | "amber" | "rose" | "purple";
}

export function Slider({
  label,
  tooltip,
  min,
  max,
  step = 1,
  value,
  onChange,
  formatValue,
  accentColor = "blue",
}: SliderProps) {
  const accentClasses = {
    blue: "accent-blue-500 focus:ring-blue-500/55 [&::-webkit-slider-thumb]:bg-blue-500 [&::-webkit-slider-thumb]:shadow-blue-500/50 [&::-moz-range-thumb]:bg-blue-500",
    indigo: "accent-indigo-500 focus:ring-indigo-500/55 [&::-webkit-slider-thumb]:bg-indigo-500 [&::-webkit-slider-thumb]:shadow-indigo-500/50 [&::-moz-range-thumb]:bg-indigo-500",
    amber: "accent-amber-500 focus:ring-amber-500/55 [&::-webkit-slider-thumb]:bg-amber-500 [&::-webkit-slider-thumb]:shadow-amber-500/50 [&::-moz-range-thumb]:bg-amber-500",
    rose: "accent-rose-500 focus:ring-rose-500/55 [&::-webkit-slider-thumb]:bg-rose-500 [&::-webkit-slider-thumb]:shadow-rose-500/50 [&::-moz-range-thumb]:bg-rose-500",
    purple: "accent-purple-500 focus:ring-purple-500/55 [&::-webkit-slider-thumb]:bg-purple-500 [&::-webkit-slider-thumb]:shadow-purple-500/50 [&::-moz-range-thumb]:bg-purple-500",
  };

  const textColors = {
    blue: "text-blue-400",
    indigo: "text-indigo-400",
    amber: "text-amber-400",
    rose: "text-rose-400",
    purple: "text-purple-400",
  };

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs font-mono">
        <span className="text-slate-300 flex items-center gap-1.5">
          {label}
          {tooltip && (
            <div className="relative group/tooltip inline-block">
              <HelpCircle className="h-3.5 w-3.5 text-slate-550 hover:text-slate-300 cursor-pointer" />
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden group-hover/tooltip:block bg-slate-900 border border-slate-800 text-slate-200 text-[10px] p-2.5 rounded-lg shadow-2xl w-52 leading-relaxed z-50 font-sans font-normal normal-case backdrop-blur-md">
                {tooltip}
              </div>
            </div>
          )}
        </span>
        <span className={`font-bold ${textColors[accentColor]}`}>
          {formatValue ? formatValue(value) : value}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className={`w-full h-1.5 bg-slate-950 rounded-lg appearance-none cursor-pointer focus:outline-none focus:ring-1 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:shadow-md [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:transition-all [&::-webkit-slider-thumb]:hover:scale-125 [&::-moz-range-thumb]:h-3.5 [&::-moz-range-thumb]:w-3.5 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:cursor-pointer [&::-moz-range-thumb]:transition-all [&::-moz-range-thumb]:hover:scale-125 ${accentClasses[accentColor]}`}
      />
    </div>
  );
}
