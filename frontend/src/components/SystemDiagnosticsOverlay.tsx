"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface DiagnosticsStatus {
  is_ready: boolean;
  missing_components: string[];
}

export default function SystemDiagnosticsOverlay() {
  const [status, setStatus] = useState<DiagnosticsStatus | null>(null);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const checkReadiness = async () => {
      try {
        const headers: Record<string, string> = {};
        if (typeof window !== "undefined") {
          const token = localStorage.getItem("token");
          if (token) {
            headers["Authorization"] = `Bearer ${token}`;
          }
        }
        const res = await fetch(`${API_BASE}/api/diagnostics/readiness`, { headers });
        if (res.ok) {
          const data = await res.json();
          setStatus(data);
        }
      } catch (err) {
        console.error("Failed to check system readiness:", err);
      }
    };
    
    checkReadiness();
    const interval = setInterval(checkReadiness, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!status || status.is_ready) return null;

  const isSettingsPage = pathname?.includes("/settings");

  // Nếu đang ở trang Settings, chỉ hiện Banner nhỏ ở dưới cùng để không che khuất form nhập liệu
  if (isSettingsPage) {
    return (
      <div className="fixed bottom-4 right-4 left-4 md:left-auto md:w-[400px] z-[9999] bg-white rounded-2xl p-6 shadow-2xl border border-rose-500/50 animate-bounce">
        <h3 className="font-bold text-rose-600 mb-2 flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
          Hệ thống cần cấu hình
        </h3>
        <p className="text-sm text-slate-600 mb-3">Vui lòng cung cấp API Key cho các thành phần:</p>
        <ul className="space-y-1">
          {status.missing_components.map((c, i) => (
            <li key={i} className="text-xs font-semibold text-rose-700 bg-rose-50 p-1.5 rounded">{c}</li>
          ))}
        </ul>
      </div>
    );
  }

  // Khóa Overlay toàn màn hình nếu ở trang khác
  return (
    <div className="fixed inset-0 z-[9999] bg-slate-900/90 backdrop-blur-md flex items-center justify-center p-6">
      <div className="bg-white rounded-3xl p-8 max-w-lg w-full shadow-[0_0_50px_rgba(225,29,72,0.15)] border border-rose-500/30">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-14 h-14 rounded-full bg-rose-100 flex items-center justify-center shrink-0">
            <svg className="w-7 h-7 text-rose-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
          </div>
          <div>
            <h2 className="text-2xl font-black text-slate-900 tracking-tight">Hệ Thống Tạm Dừng</h2>
            <p className="text-slate-500 font-medium">Thiếu cấu hình AI Models quan trọng</p>
          </div>
        </div>
        
        <p className="text-slate-600 mb-6 leading-relaxed">Marketing Agent OS yêu cầu thiết lập đầy đủ các AI Model trước khi hoạt động để ngăn chặn rác dữ liệu Vector. Vui lòng cung cấp API Key cho các thành phần sau:</p>
        
        <ul className="space-y-2.5 mb-8">
          {status.missing_components.map((c, i) => (
            <li key={i} className="flex items-center gap-3 text-rose-800 bg-rose-50/80 p-3.5 rounded-xl text-sm font-semibold border border-rose-100">
              <svg className="w-5 h-5 flex-shrink-0 text-rose-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              {c}
            </li>
          ))}
        </ul>
        
        <button 
          onClick={() => router.push("/settings/models")}
          className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-4 px-6 rounded-xl shadow-xl shadow-indigo-600/20 transition-all flex items-center justify-center gap-2 group"
        >
          Đến trang Cài Đặt
          <svg className="w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
        </button>
      </div>
    </div>
  );
}
