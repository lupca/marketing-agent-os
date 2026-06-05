"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Search,
  FileText,
  Trash2,
  Edit,
  Loader2,
  ArrowRight
} from "lucide-react";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface TagRecord {
  tag_id: string;
  tag_name: string;
  description: string;
  color: string;
}

interface DocRecord {
  document_id: string;
  file_name: string;
  file_key: string;
  access_tags: string[];
  upload_status: string;
  sync_status: string;
  chunk_count: number;
  file_size_bytes: number;
  created_at?: string;
}

interface RagChunk {
  document_id: string;
  chunk_id?: string;
  similarity_score: number;
  content_full?: string;
  content_preview?: string;
  access_tags?: string[];
}

interface StudioLog {
  title: string;
  time: string;
  text: string;
}

interface ChatBubble {
  sender: "user" | "ai";
  text: string;
  results?: RagChunk[];
}

export default function KnowledgeBase() {
  const { showToast } = useToast();
  // Core States
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [tags, setTags] = useState<TagRecord[]>([]);
  const [documents, setDocuments] = useState<DocRecord[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [selectedUploadTags, setSelectedUploadTags] = useState<string[]>(["global"]);
  const [selectedPlaygroundTags, setSelectedPlaygroundTags] = useState<string[]>(["global"]);
  
  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [tagFilter, setTagFilter] = useState("all");

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 6;

  // Drag & Drop
  const [dragOver, setDragOver] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  // Chat Playground
  const [chatQuery, setChatQuery] = useState("");
  const [chatHistory, setChatHistory] = useState<ChatBubble[]>([]);
  const [activeLimit, setActiveLimit] = useState(5);
  const [retrievalStats, setRetrievalStats] = useState("");
  const [querying, setQuerying] = useState(false);

  // Studio logs
  const [studioLogs, setStudioLogs] = useState<StudioLog[]>([
    { title: "Tổng quan tài liệu nguồn", time: "5 phút trước", text: "Tóm tắt tổng quan RAG toàn bộ nguồn tài liệu đang có trong workspace" },
    { title: "Quy chuẩn nội dung & luật cấm", time: "15 phút trước", text: "Trích xuất các quy chuẩn viết kịch bản và luật cấm quảng cáo của nền tảng" }
  ]);

  // Modals
  const [readerDoc, setReaderDoc] = useState<DocRecord | null>(null);
  const [readerChunks, setReaderChunks] = useState<RagChunk[]>([]);
  const [loadingChunks, setLoadingChunks] = useState(false);

  const [editDoc, setEditDoc] = useState<DocRecord | null>(null);
  const [editDocName, setEditDocName] = useState("");
  const [editDocTags, setEditDocTags] = useState<string[]>([]);
  const [savingEdit, setSavingEdit] = useState(false);

  // Pollings
  const pollIntervals = useRef<{ [key: string]: NodeJS.Timeout }>({});

  // Helper size label
  const formatBytes = (bytes: number) => {
    if (!bytes || bytes === 0) return "—";
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  };

  // Icon selector
  const getFileIcon = (filename: string) => {
    const ext = filename.split(".").pop()?.toLowerCase();
    switch (ext) {
      case "pdf": return "📕";
      case "mp3":
      case "wav":
      case "m4a": return "🎧";
      case "xlsx":
      case "xls":
      case "csv": return "📊";
      case "docx":
      case "doc":
      case "md": return "📝";
      case "pptx":
      case "ppt": return "🗂️";
      default: return "📄";
    }
  };

  const getAgentAccessExplanation = (tagName: string) => {
    switch (tagName) {
      case "global": return "Tất cả các Agents";
      case "marketing": return "Creative Agent (Lên ý tưởng)";
      case "anti_patterns": return "Analyst & Creative Agent";
      case "policies": return "Researcher & Brand Guardian";
      case "manager_feedback": return "Tất cả Agents (CMO Feedback)";
      case "psychology": return "Creative Agent (Tâm lý học)";
      case "economics": return "Analyst Agent (Kinh tế)";
      default: return "Agents được cấp quyền";
    }
  };

  // API calls
  const loadDocumentsRef = useRef<() => Promise<void>>(async () => {});

  const loadTags = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/rag/tags`);
      const data = await response.json();
      setTags(data.tags || []);
      if (data.workspace_id) {
        setWorkspaceId(data.workspace_id);
      }
    } catch (error) {
      console.error(error);
      showToast("Lỗi tải Access Tags RAG.", "error");
    }
  }, [showToast]);

  const startPolling = useCallback((docId: string) => {
    if (pollIntervals.current[docId]) return;
    
    let attempts = 0;
    pollIntervals.current[docId] = setInterval(async () => {
      attempts++;
      if (attempts > 30) {
        clearInterval(pollIntervals.current[docId]);
        delete pollIntervals.current[docId];
        return;
      }

      try {
        const response = await fetch(`${API_BASE}/api/rag/documents/${docId}/status`);
        const statusData = await response.json();
        if (statusData.upload_status === "ready" && statusData.sync_status === "synced") {
          clearInterval(pollIntervals.current[docId]);
          delete pollIntervals.current[docId];
          showToast(`✅ Tài liệu "${statusData.file_name}" đã băm thành công ${statusData.chunk_count} chunks!`, "success");
          loadDocumentsRef.current();
        } else if (statusData.upload_status === "failed") {
          clearInterval(pollIntervals.current[docId]);
          delete pollIntervals.current[docId];
          showToast(`❌ Băm vector thất bại cho tệp: "${statusData.file_name}"`, "error");
          loadDocumentsRef.current();
        }
      } catch {
        // Silent error on polling
      }
    }, 4000);
  }, [showToast]);

  const loadDocuments = useCallback(async () => {
    setLoadingDocs(true);
    try {
      let allDocs: DocRecord[] = [];
      let page = 1;
      let hasMore = true;

      while (hasMore && page <= 10) {
        const response = await fetch(`${API_BASE}/api/rag/documents?page=${page}&limit=100`);
        const data = await response.json();
        const docs = data.documents || [];
        allDocs = [...allDocs, ...docs];

        if (allDocs.length >= (data.total || 0) || docs.length < 100) {
          hasMore = false;
        } else {
          page++;
        }
      }

      setDocuments(allDocs);
      
      // Auto poll docs in processing status
      allDocs.forEach((doc: DocRecord) => {
        if (doc.upload_status === "processing" || doc.sync_status === "syncing") {
          startPolling(doc.document_id);
        }
      });
    } catch (error) {
      console.error(error);
      showToast("Lỗi tải danh mục tài liệu RAG.", "error");
    } finally {
      setLoadingDocs(false);
    }
  }, [showToast, startPolling]);

  // Keep ref updated
  useEffect(() => {
    loadDocumentsRef.current = loadDocuments;
  }, [loadDocuments]);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadTags();
      loadDocuments();
    }, 0);

    const currentPolls = pollIntervals.current;
    return () => {
      clearTimeout(timer);
      // Clean pollings on unmount
      Object.keys(currentPolls).forEach(k => {
        clearInterval(currentPolls[k]);
      });
    };
  }, [loadDocuments, loadTags]);

  // Upload Logic
  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      showToast("Bạn chưa chọn tập tin nào để upload!", "error");
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append("file", uploadFile);
    formData.append("access_tags", JSON.stringify(selectedUploadTags));
    if (workspaceId) {
      formData.append("workspace_id", workspaceId);
    }

    try {
      const response = await fetch(`${API_BASE}/api/rag/upload`, {
        method: "POST",
        body: formData
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Upload error");
      }

      const resData = await response.json();
      showToast(`✅ File "${uploadFile.name}" đã tải lên! Đang băm vector...`, "success");
      setUploadFile(null);
      loadDocuments();
      if (resData.document_id) {
        startPolling(resData.document_id);
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Unknown error";
      showToast(`❌ Tải lên thất bại: ${msg}`, "error");
    } finally {
      setUploading(false);
    }
  };

  // Drag Drop handlers
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragOver(true);
    } else if (e.type === "dragleave") {
      setDragOver(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      // Type checks
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      const allowed = [".pdf", ".txt", ".docx", ".xlsx", ".pptx", ".csv", ".mp3", ".md"];
      if (allowed.includes(ext)) {
        setUploadFile(file);
      } else {
        showToast("Định dạng file không được hỗ trợ.", "error");
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setUploadFile(e.target.files[0]);
    }
  };

  // Delete document
  const handleDeleteDoc = async (id: string, name: string) => {
    if (!confirm(`Bạn có chắc chắn muốn xóa tài liệu "${name}"?\n\nDữ liệu sẽ bị xóa mềm và biến mất khỏi vector search.`)) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/rag/documents/${id}`, {
        method: "DELETE"
      });
      if (!response.ok) throw new Error("Delete failed");
      showToast(`🗑️ Đã kích hoạt yêu cầu xóa "${name}"...`, "info");
      loadDocuments();
    } catch {
      showToast("Lỗi xóa tài liệu.", "error");
    }
  };

  // Open Raw Text reader
  const handleOpenReader = async (doc: DocRecord) => {
    setReaderDoc(doc);
    setLoadingChunks(true);
    setReaderChunks([]);

    try {
      // Run test-retrieval searching for the file name specifically
      const payload = {
        query: doc.file_name,
        access_tags: doc.access_tags || ["global"],
        limit: 10
      };

      const response = await fetch(`${API_BASE}/api/rag/test-retrieval`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      
      // Filter matching only this doc ID
      const matched = (data.results || []).filter((r: RagChunk) => r.document_id === doc.document_id);
      setReaderChunks(matched);
    } catch {
      showToast("Lỗi trích xuất phân đoạn tri thức.", "error");
    } finally {
      setLoadingChunks(false);
    }
  };

  // Open tags editor
  const handleOpenEdit = (doc: DocRecord) => {
    setEditDoc(doc);
    setEditDocName(doc.file_name);
    setEditDocTags([...doc.access_tags]);
  };

  const handleSaveEdit = async () => {
    if (!editDoc) return;
    if (!editDocName.trim()) {
      showToast("Tên tài liệu không được để trống.", "error");
      return;
    }

    setSavingEdit(true);
    try {
      const response = await fetch(`${API_BASE}/api/rag/documents/${editDoc.document_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          file_name: editDocName.trim(),
          access_tags: editDocTags
        })
      });

      if (!response.ok) throw new Error("Save edit failed");
      showToast("Đã lưu thay đổi! Hệ thống đang cập nhật...", "success");
      setEditDoc(null);
      loadDocuments();
    } catch {
      showToast("Lỗi lưu thông tin tài liệu.", "error");
    } finally {
      setSavingEdit(false);
    }
  };

  // Chat test retrieval logic
  const runChatQuery = async (queryText: string) => {
    if (!queryText.trim() || queryText.length < 3) {
      showToast("Câu hỏi phải có ít nhất 3 ký tự.", "error");
      return;
    }

    setQuerying(true);
    const userMsg: ChatBubble = { sender: "user", text: queryText };
    setChatHistory(prev => [...prev, userMsg]);
    setChatQuery("");

    try {
      const payload = {
        query: queryText,
        access_tags: selectedPlaygroundTags,
        limit: activeLimit,
        workspace_id: workspaceId
      };

      const response = await fetch(`${API_BASE}/api/rag/test-retrieval`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();

      setRetrievalStats(`⚡ Truy vấn: ${data.elapsed_ms}ms | Phân đoạn khớp: ${data.result_count}`);
      
      const aiMsg: ChatBubble = {
        sender: "ai",
        text: data.results && data.results.length > 0
          ? data.results[0].content_full || data.results[0].content_preview
          : "Không tìm thấy tri thức hay kết quả phù hợp nào khớp với bộ tags trong HNSW Index. Vui lòng nạp thêm file hoặc điều chỉnh Access Tags.",
        results: data.results || []
      };

      setChatHistory(prev => [...prev, aiMsg]);
    } catch {
      const errorMsg: ChatBubble = {
        sender: "ai",
        text: "Lỗi kết nối: Không thể thực hiện RAG Vector search. Vui lòng kiểm tra cổng API nhúng."
      };
      setChatHistory(prev => [...prev, errorMsg]);
    } finally {
      setQuerying(false);
    }
  };

  // Filter logic
  const getFilteredDocs = () => {
    return documents.filter(doc => {
      const matchesSearch = doc.file_name.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === "all" ? true : doc.upload_status === statusFilter;
      const matchesTag = tagFilter === "all" ? true : doc.access_tags.includes(tagFilter);
      return matchesSearch && matchesStatus && matchesTag;
    });
  };

  const filteredDocs = getFilteredDocs();
  const totalPages = Math.ceil(filteredDocs.length / pageSize) || 1;

  // Reset page when filters change
  useEffect(() => {
    const timer = setTimeout(() => {
      setCurrentPage(1);
    }, 0);
    return () => clearTimeout(timer);
  }, [searchQuery, statusFilter, tagFilter]);

  // Paginated slice
  const paginatedDocs = filteredDocs.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <div className="flex-1 flex gap-5 min-h-[600px] font-sans">
      
      {/* COLUMN 1: SOURCES & UPLOADS */}
      <aside className="w-80 border border-slate-900 bg-slate-950/20 rounded-xl p-4 flex flex-col gap-4 shrink-0">
        <div className="flex justify-between items-center pb-2 border-b border-slate-900">
          <h3 className="text-xs font-extrabold uppercase tracking-widest text-slate-300 font-mono">📁 Nguồn Tài Liệu</h3>
          <span className="text-[10px] font-mono font-bold bg-slate-900 border border-slate-800 text-slate-400 px-2 py-0.5 rounded">
            {documents.length} Nguồn
          </span>
        </div>

        {/* Search & filters */}
        <div className="space-y-2 shrink-0">
          <div className="relative">
            <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-500" />
            <input
              type="text"
              placeholder="Tìm nguồn tài liệu..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950 border border-slate-900 focus:border-slate-800 rounded pl-8 pr-3 py-1.5 text-xs text-slate-200 outline-none"
            />
          </div>

          <div className="flex flex-wrap gap-1.5">
            {[
              { id: "all", label: "🌐 Tất cả" },
              { id: "ready", label: "✅ Sẵn sàng" },
              { id: "processing", label: "⏳ Băm vector" },
              { id: "failed", label: "❌ Lỗi" }
            ].map(pill => (
              <button
                key={pill.id}
                onClick={() => setStatusFilter(pill.id)}
                className={`px-2 py-0.5 rounded text-[10px] font-medium transition-all cursor-pointer ${
                  statusFilter === pill.id 
                    ? "bg-blue-950 text-blue-400 border border-blue-900/40" 
                    : "bg-slate-900/30 text-slate-400 hover:text-slate-200"
                }`}
              >
                {pill.label}
              </button>
            ))}
          </div>

          <div className="relative">
            <select
              value={tagFilter}
              onChange={e => setTagFilter(e.target.value)}
              className="w-full bg-slate-950 border border-slate-900 focus:border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-300 outline-none accent-slate-950 cursor-pointer"
            >
              <option value="all">🏷️ Tất cả Access Tags</option>
              {tags.map(t => (
                <option key={t.tag_id} value={t.tag_name} style={{ color: t.color }}>
                  {t.tag_name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Scrollable list */}
        <div className="flex-1 overflow-y-auto space-y-2 pr-1 min-h-0">
          {loadingDocs ? (
            <div className="h-full flex items-center justify-center text-xs text-slate-500 gap-2">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Đang tải tài liệu RAG...
            </div>
          ) : paginatedDocs.length > 0 ? (
            paginatedDocs.map(doc => {
              const icon = getFileIcon(doc.file_name);
              const statusColor = doc.upload_status === "ready" ? "text-emerald-500" : doc.upload_status === "processing" ? "text-amber-500" : "text-rose-500";
              const statusLabel = doc.upload_status === "ready" ? "Sẵn sàng" : doc.upload_status === "processing" ? "Băm..." : "Lỗi";

              return (
                <div
                  key={doc.document_id}
                  onClick={() => handleOpenReader(doc)}
                  className="bg-slate-900/25 border border-slate-900 hover:border-slate-800 rounded-lg p-2.5 flex items-start gap-2.5 cursor-pointer relative group transition-all"
                >
                  <span className="text-lg leading-none select-none">{icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-[11px] font-bold text-slate-200 truncate pr-6" title={doc.file_name}>{doc.file_name}</div>
                    <div className="text-[9px] text-slate-500 font-mono mt-1 flex flex-wrap items-center gap-1.5">
                      <span className={`${statusColor} font-semibold`}>{statusLabel}</span>
                      <span>&bull;</span>
                      <span>{formatBytes(doc.file_size_bytes)}</span>
                      <span>&bull;</span>
                      <div className="flex items-center gap-0.5">
                        {doc.access_tags.map(t => {
                          const tg = tags.find(at => at.tag_name === t);
                          return (
                            <span
                              key={t}
                              className="h-1.5 w-1.5 rounded-full"
                              style={{ backgroundColor: tg?.color || "#6366f1" }}
                              title={`Access Tag: ${t} - ${getAgentAccessExplanation(t)}`}
                            ></span>
                          );
                        })}
                      </div>
                    </div>
                  </div>

                  <div className="absolute right-2 top-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity" onClick={e => e.stopPropagation()}>
                    <button
                      onClick={() => handleOpenEdit(doc)}
                      className="text-slate-500 hover:text-slate-200 p-0.5 cursor-pointer"
                      title="Sửa thông tin"
                    >
                      <Edit className="h-3 w-3" />
                    </button>
                    <button
                      onClick={() => handleDeleteDoc(doc.document_id, doc.file_name)}
                      className="text-slate-500 hover:text-rose-400 p-0.5 cursor-pointer"
                      title="Xóa tài liệu"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="text-center py-10 text-xs text-slate-500">Thư mục trống. Hãy upload tệp.</div>
          )}
        </div>

        {/* Pagination controls */}
        {filteredDocs.length > pageSize && (
          <div className="flex items-center justify-between border-t border-slate-900 pt-3 text-[10px] font-mono shrink-0">
            <button
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              className="px-2 py-1 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 rounded disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer font-bold"
            >
              &larr; Trước
            </button>
            <span className="text-slate-500">
              Trang <strong className="text-slate-350">{currentPage}</strong> / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages}
              className="px-2 py-1 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 rounded disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer font-bold"
            >
              Sau &rarr;
            </button>
          </div>
        )}

        {/* Upload Container */}
        <div className="border-t border-slate-900 pt-3 space-y-3 shrink-0">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">🏷️ Access Tags Mới</span>
            <div className="flex flex-wrap gap-1 mt-1.5">
              {tags.map(t => {
                const isSelected = selectedUploadTags.includes(t.tag_name);
                return (
                  <button
                    key={t.tag_id}
                    onClick={() => {
                      if (isSelected) {
                        if (selectedUploadTags.length === 1) return;
                        setSelectedUploadTags(selectedUploadTags.filter(ut => ut !== t.tag_name));
                      } else {
                        setSelectedUploadTags([...selectedUploadTags, t.tag_name]);
                      }
                    }}
                    className="flex items-center gap-1 px-1.5 py-0.5 border rounded text-[9px] font-mono font-semibold uppercase tracking-wider transition-all cursor-pointer"
                    style={{
                      borderColor: isSelected ? t.color : "rgba(255,255,255,0.06)",
                      color: isSelected ? t.color : "#94a3b8",
                      backgroundColor: isSelected ? `${t.color}0a` : "transparent"
                    }}
                  >
                    <span className="h-1 w-1 rounded-full" style={{ backgroundColor: t.color }}></span>
                    {t.tag_name}
                  </button>
                );
              })}
            </div>
          </div>

          <form
            onSubmit={handleUploadSubmit}
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-all duration-300 ${
              dragOver 
                ? "border-blue-500 bg-blue-950/20 shadow-lg shadow-blue-500/5 scale-[1.02] animate-pulse" 
                 : "border-slate-800 bg-slate-950/45 hover:border-slate-700 hover:bg-slate-950/60"
            }`}
          >
            <input
              type="file"
              id="file-upload-input"
              className="hidden"
              onChange={handleFileChange}
              accept=".pdf,.txt,.docx,.xlsx,.pptx,.csv,.mp3,.md"
            />
            <label htmlFor="file-upload-input" className="cursor-pointer space-y-2 block">
              <span className={`text-2xl block transition-transform duration-300 ${dragOver ? "scale-125 -translate-y-1" : ""}`}>📤</span>
              <div className="text-[11px] font-semibold text-slate-300">
                {uploadFile ? uploadFile.name : "Kéo thả file vào đây hoặc Chọn tệp"}
              </div>
              <div className="text-[9px] text-slate-500 font-mono">Hỗ trợ PDF, TXT, DOCX, CSV, MD</div>
            </label>
          </form>

          <div className="flex items-center justify-between gap-3">
            <span className="text-[9px] text-slate-500 font-sans truncate">
              {uploadFile ? "1 file sẵn sàng" : "Chọn file & tag để nạp"}
            </span>
            <button
              onClick={handleUploadSubmit}
              disabled={uploading || !uploadFile}
              className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white font-bold uppercase tracking-wider text-[10px] rounded transition-all disabled:opacity-40 cursor-pointer font-mono"
            >
              {uploading ? "Đang tải..." : "Upload"}
            </button>
          </div>
        </div>
      </aside>

      {/* COLUMN 2: CONVERSATION PLAYGROUND */}
      <main className="flex-1 border border-slate-900 bg-slate-950/20 rounded-xl p-4 flex flex-col min-w-0">
        <div className="pb-3 border-b border-slate-900">
          <h3 className="text-xs font-extrabold uppercase tracking-widest text-slate-300 font-mono">📚 Tri Thức Thư Viện RAG</h3>
          <p className="text-[10px] text-slate-500 font-sans mt-0.5">Thử nghiệm HNSW Vector Index & Reranking</p>
        </div>

        {/* Chat Feed */}
        <div className="flex-1 overflow-y-auto py-4 space-y-4 min-h-0">
          {chatHistory.length === 0 ? (
            <div className="h-full flex flex-col justify-center items-center p-6 text-center max-w-lg mx-auto space-y-4">
              <div className="text-3xl leading-none">🧠</div>
              <div className="space-y-1">
                <h4 className="text-xs font-bold uppercase text-slate-200 tracking-wider font-mono">Định Hướng Tri Thức Hệ Thống</h4>
                <p className="text-xs text-slate-400 leading-relaxed font-sans">
                  Đặt câu hỏi cho AI để trích xuất tri thức, tài liệu định chuẩn quy cách hoặc chính sách Ads từ các nguồn vector pgvector đã nạp.
                </p>
              </div>

              {/* Prompt Suggestions */}
              <div className="w-full text-left space-y-2 pt-3">
                <span className="text-[10px] font-bold text-slate-500 font-mono uppercase tracking-wider block flex items-center gap-1">💡 Câu hỏi gợi ý tuyển chọn:</span>
                <div className="grid grid-cols-1 gap-2">
                  {[
                    "Chính sách quảng cáo Facebook về sản phẩm giảm cân hay sức khỏe là gì?",
                    "Làm thế nào để tối ưu góc viết kịch bản quảng cáo (Winning Angles)?",
                    "Thuật toán Inverse CPA Weighting hoạt động thế nào để đề xuất ngân sách?"
                  ].map((prompt, idx) => (
                    <button
                      key={idx}
                      onClick={() => runChatQuery(prompt)}
                      className="w-full bg-slate-900/40 backdrop-blur-md border border-slate-850 hover:border-slate-700/80 rounded-lg p-3 text-left text-xs text-slate-355 font-sans hover:text-white hover:bg-slate-900/60 hover:shadow-md hover:shadow-black/10 transition-all duration-300 flex justify-between items-center group cursor-pointer"
                    >
                      <span className="pr-4">{prompt}</span>
                      <ArrowRight className="h-3.5 w-3.5 text-slate-500 group-hover:text-blue-400 group-hover:translate-x-1 transition-all shrink-0" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            chatHistory.map((msg, idx) => (
              <div key={idx} className={`flex flex-col gap-1.5 max-w-[85%] ${msg.sender === "user" ? "ml-auto items-end" : "mr-auto items-start"}`}>
                <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest">
                  {msg.sender === "user" ? "CMO Quyết Định" : "🤖 Trí Tuệ Marketing OS"}
                </span>
                <div className={`p-3 rounded-lg text-xs leading-relaxed ${
                  msg.sender === "user" 
                    ? "bg-blue-950/40 text-slate-200 border border-blue-900/30" 
                    : "bg-slate-900/35 text-slate-300 border border-slate-900/80"
                }`}>
                  <p className="whitespace-pre-wrap">{msg.text}</p>
                  
                  {/* Citations list */}
                  {msg.results && msg.results.length > 0 && (
                    <div className="mt-4 border-t border-slate-900/60 pt-3 space-y-2 shrink-0">
                      <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block">Trích dẫn tài liệu nguồn ({msg.results.length})</span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 mt-1">
                        {msg.results.map((citation: RagChunk, cidx: number) => {
                          const pct = Math.round(citation.similarity_score * 100);
                          return (
                            <div
                              key={cidx}
                              onClick={() => {
                                const found = documents.find(d => d.document_id === citation.document_id);
                                if (found) handleOpenReader(found);
                              }}
                              className="bg-slate-950/90 border border-slate-900/80 hover:border-slate-700 p-2.5 rounded-lg hover:bg-slate-900/40 cursor-pointer transition-all duration-300 hover:-translate-y-0.5 hover:shadow-md hover:shadow-black/20"
                            >
                              <div className="flex justify-between items-center text-[9px] font-mono mb-1.5">
                                <span className="text-slate-450 font-semibold">Citation #{cidx + 1}</span>
                                <span className="text-emerald-400 font-extrabold bg-emerald-950/40 border border-emerald-900/30 px-1.5 py-0.2 rounded text-[8px] tracking-wider">
                                  🎯 {pct}% Score
                                </span>
                              </div>
                              <p className="text-[10px] text-slate-400 line-clamp-2 leading-relaxed">&quot;{citation.content_preview}&quot;</p>
                              <div className="flex gap-1 mt-2 flex-wrap">
                                {citation.access_tags && citation.access_tags.map((t: string) => {
                                  const tg = tags.find(at => at.tag_name === t);
                                  return (
                                    <span
                                      key={t}
                                      className="px-1.5 py-0.2 border rounded text-[7px] font-mono uppercase tracking-wider scale-95 font-semibold"
                                      style={{
                                        borderColor: tg?.color || "#6366f1",
                                        color: tg?.color || "#94a3b8",
                                        backgroundColor: tg ? `${tg.color}0d` : "transparent"
                                      }}
                                    >
                                      {t}
                                    </span>
                                  );
                                })}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          {querying && (
            <div className="flex flex-col gap-1.5 max-w-[80%] mr-auto items-start">
              <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest">🤖 Trí Tuệ Marketing OS</span>
              <div className="p-3 bg-slate-900/35 border border-slate-900/80 rounded-lg text-xs text-slate-400 flex items-center gap-2">
                <Loader2 className="h-3 w-3 animate-spin text-blue-500" />
                Đang nhúng truy vấn và tìm kiếm trên cơ sở dữ liệu pgvector...
              </div>
            </div>
          )}
        </div>

        {/* Input area */}
        <div className="border-t border-slate-900 pt-3 space-y-2 shrink-0">
          <div className="bg-slate-950 border border-slate-900 rounded-lg p-2 flex gap-3 items-end">
            <textarea
              placeholder="Nhập câu hỏi hoặc yêu cầu tạo nội dung từ nguồn..."
              value={chatQuery}
              onChange={e => setChatQuery(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  runChatQuery(chatQuery);
                }
              }}
              rows={1}
              className="flex-1 bg-transparent border-none outline-none text-xs text-slate-200 resize-none max-h-24 min-h-[24px] py-1 font-sans"
            />
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => {
                  const limits = [3, 5, 8, 10];
                  const idx = limits.indexOf(activeLimit);
                  setActiveLimit(limits[(idx + 1) % limits.length]);
                  showToast(`🎯 Cấu hình RAG Retrieval: tối đa ${limits[(idx + 1) % limits.length]} chunks`, "info");
                }}
                className="bg-slate-900 hover:bg-slate-800 text-[10px] font-mono font-bold text-slate-400 px-2 py-1.5 border border-slate-800 rounded cursor-pointer"
                title="Click đổi số lượng chunks"
              >
                Limit: {activeLimit} Chunks
              </button>
              <button
                onClick={() => runChatQuery(chatQuery)}
                disabled={querying || !chatQuery.trim()}
                className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 h-8 w-8 rounded flex items-center justify-center text-white transition-all cursor-pointer font-bold"
              >
                →
              </button>
            </div>
          </div>
          
          <div className="flex justify-between items-center px-1">
            <span className="text-[10px] text-slate-500 font-mono">
              {retrievalStats || "Zero-JOIN HNSW Vector engine is ready."}
            </span>
            <div className="flex items-center gap-1.5 font-mono text-[9px]">
              <span className="text-slate-500">Playground Tags:</span>
              <div className="flex gap-1 select-none">
                {tags.map(t => {
                  const isSel = selectedPlaygroundTags.includes(t.tag_name);
                  return (
                    <button
                      key={t.tag_id}
                      onClick={() => {
                        if (isSel) {
                          if (selectedPlaygroundTags.length === 1) return;
                          setSelectedPlaygroundTags(selectedPlaygroundTags.filter(s => s !== t.tag_name));
                        } else {
                          setSelectedPlaygroundTags([...selectedPlaygroundTags, t.tag_name]);
                        }
                      }}
                      className="px-1 border rounded text-[7px] cursor-pointer"
                      style={{
                        borderColor: isSel ? t.color : "rgba(255,255,255,0.05)",
                        color: isSel ? t.color : "#64748b"
                      }}
                    >
                      {t.tag_name}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* COLUMN 3: STUDIO PRESETS */}
      <aside className="w-64 border border-slate-900 bg-slate-950/20 rounded-xl p-4 flex flex-col gap-4 shrink-0">
        <div className="pb-2 border-b border-slate-900">
          <h3 className="text-xs font-extrabold uppercase tracking-widest text-slate-300 font-mono">🛠️ RAG Studio Presets</h3>
        </div>

        {/* Preset Cards banner */}
        <div className="bg-gradient-to-br from-indigo-950/30 to-purple-950/20 border border-indigo-900/30 rounded-lg p-3 space-y-1 relative overflow-hidden shrink-0">
          <div className="absolute top-0 right-0 h-10 w-10 bg-indigo-500/5 blur-lg"></div>
          <h4 className="text-[11px] font-bold text-indigo-300 font-mono">CMO Copywriter Studio</h4>
          <p className="text-[9px] text-slate-400 leading-relaxed font-sans">Chọn các presets để AI tự động trích xuất tri thức từ tài liệu nguồn.</p>
        </div>

        {/* Presets Card grid */}
        <div className="grid grid-cols-2 gap-2 shrink-0">
          {[
            { label: "Tổng quan", icon: "📝", query: "Tạo tóm tắt tổng quan RAG toàn bộ nguồn tài liệu đang có trong workspace" },
            { label: "Bản đồ", icon: "🗺️", query: "Liệt kê bản đồ insights khách hàng và insight chân dung đối tượng mục tiêu" },
            { label: "Cạnh tranh", icon: "⚔️", query: "Tìm kiếm các góc viết quảng cáo cạnh tranh và so sánh với đối thủ cạnh tranh" },
            { label: "Flashcard", icon: "📇", query: "Tạo các flashcard câu hỏi nhanh để học và đào tạo về chính sách quảng cáo" },
            { label: "Quy chuẩn", icon: "⚖️", query: "Trích xuất các quy chuẩn viết kịch bản và luật cấm quảng cáo của nền tảng" },
            { label: "Báo cáo", icon: "📊", query: "Lập báo cáo RAG audit toàn bộ các điểm neo kiến thức và đề xuất tối ưu hóa" }
          ].map((preset, idx) => (
            <button
              key={idx}
              onClick={() => {
                runChatQuery(preset.query);
                // Save to logs
                setStudioLogs(prev => [
                  { title: preset.label + " tài liệu nguồn", time: "Vừa xong", text: preset.query },
                  ...prev.slice(0, 4)
                ]);
              }}
              className="bg-slate-900/35 border border-slate-900 hover:border-slate-850 hover:bg-slate-900/60 rounded-xl p-3 flex flex-col items-center gap-2 transition-all duration-300 text-center group cursor-pointer hover:-translate-y-0.5 hover:shadow-md hover:shadow-indigo-950/10"
            >
              <span className="text-xl leading-none group-hover:scale-125 group-hover:rotate-6 transition-all duration-300">{preset.icon}</span>
              <span className="text-[10px] font-bold text-slate-400 group-hover:text-indigo-400 font-mono tracking-wide transition-colors">{preset.label}</span>
            </button>
          ))}
        </div>

        {/* Logs */}
        <div className="flex-1 flex flex-col min-h-0">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 font-mono pb-1">Đầu ra RAG Studio Logs</span>
          <div className="flex-1 overflow-y-auto space-y-2 pr-1 min-h-0">
            {studioLogs.map((log, idx) => (
              <div
                key={idx}
                onClick={() => runChatQuery(log.text)}
                className="bg-slate-900/20 border border-slate-900 hover:border-slate-800 p-2.5 rounded cursor-pointer transition-all space-y-1"
              >
                <div className="flex justify-between items-center text-[9px] font-mono">
                  <span className="text-slate-300 font-bold flex items-center gap-1">
                    <FileText className="h-2.5 w-2.5 text-indigo-400" />
                    {log.title}
                  </span>
                  <span className="text-slate-600">{log.time}</span>
                </div>
                <p className="text-[8px] text-slate-500 truncate">{log.text}</p>
              </div>
            ))}
          </div>
        </div>
      </aside>

      {/* MODAL: DOCUMENT RAW CHUNKS READER */}
      <Modal
        isOpen={!!readerDoc}
        onClose={() => setReaderDoc(null)}
        title={readerDoc ? readerDoc.file_name : ""}
        subtitle={readerDoc ? `Kích thước: ${formatBytes(readerDoc.file_size_bytes)} | Tổng: ${readerDoc.chunk_count || 0} chunks` : ""}
        headerIcon={readerDoc ? getFileIcon(readerDoc.file_name) : undefined}
        maxWidth="3xl"
        footer={
          readerDoc ? (
            <>
              <button
                onClick={() => {
                  const filename = readerDoc.file_name;
                  setReaderDoc(null);
                  runChatQuery(`Tóm tắt nội dung tài liệu ${filename}`);
                }}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white font-bold uppercase tracking-wider text-[10px] rounded cursor-pointer font-mono"
              >
                📖 Yêu cầu AI Tóm Tắt
              </button>
              <button
                onClick={() => setReaderDoc(null)}
                className="px-3 py-1.5 bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 font-bold uppercase tracking-wider text-[10px] rounded cursor-pointer font-mono"
              >
                Đóng
              </button>
            </>
          ) : null
        }
      >
        {loadingChunks ? (
          <div className="py-20 text-center text-xs text-slate-500 flex flex-col items-center justify-center gap-2 font-mono">
            <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
            Đang truy xuất các khối văn bản thô từ pgvector...
          </div>
        ) : readerChunks.length > 0 ? (
          readerChunks.map((chunk, idx) => (
            <div key={chunk.chunk_id} className="bg-slate-900/35 border border-slate-900 p-3 rounded-lg space-y-1.5 font-mono text-xs">
              <div className="flex justify-between items-center text-[9px] text-slate-500">
                <span>Phân đoạn chunk #{idx + 1}</span>
                <span className="text-emerald-400 font-bold">Matching score: {Math.round(chunk.similarity_score * 100)}%</span>
              </div>
              <p className="text-slate-300 font-sans leading-relaxed whitespace-pre-wrap">{chunk.content_full}</p>
            </div>
          ))
        ) : (
          <div className="py-20 text-center text-xs text-slate-500 font-mono">
            Không tìm thấy chunks nào cho tài liệu này hoặc Celery đang băm vector.
          </div>
        )}
      </Modal>

      {/* MODAL: EDIT TAGS & FILENAME */}
      <Modal
        isOpen={!!editDoc}
        onClose={() => setEditDoc(null)}
        title="🏷️ Chỉnh Sửa Thông Tin Tài Liệu"
        maxWidth="md"
        footer={
          <>
            <button
              onClick={() => setEditDoc(null)}
              className="px-3 py-1.5 bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 font-bold uppercase tracking-wider text-[10px] rounded cursor-pointer font-mono"
            >
              Huỷ
            </button>
            <button
              onClick={handleSaveEdit}
              disabled={savingEdit}
              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white font-bold uppercase tracking-wider text-[10px] rounded cursor-pointer transition-all disabled:opacity-50 font-mono"
            >
              {savingEdit ? "Đang lưu..." : "💾 Lưu Thay Đổi"}
            </button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider font-mono">Tên tài liệu (File Name)</label>
            <input
              type="text"
              value={editDocName}
              onChange={e => setEditDocName(e.target.value)}
              className="w-full bg-slate-950 border border-slate-900 focus:border-slate-800 rounded px-3 py-2 text-xs text-slate-200 outline-none"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider font-mono">Phân Quyền Access Tags Cho AI Agents</label>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {tags.map(t => {
                const isSel = editDocTags.includes(t.tag_name);
                return (
                  <button
                    key={t.tag_id}
                    onClick={() => {
                      if (isSel) {
                        if (editDocTags.length === 1) return;
                        setEditDocTags(editDocTags.filter(ut => ut !== t.tag_name));
                      } else {
                        setEditDocTags([...editDocTags, t.tag_name]);
                      }
                    }}
                    className="flex items-center gap-1 px-2 py-0.5 border rounded text-[10px] font-mono font-semibold uppercase tracking-wider transition-all cursor-pointer"
                    style={{
                      borderColor: isSel ? t.color : "rgba(255,255,255,0.06)",
                      color: isSel ? t.color : "#94a3b8",
                      backgroundColor: isSel ? `${t.color}0a` : "transparent"
                    }}
                  >
                    <span className="h-1 w-1 rounded-full" style={{ backgroundColor: t.color }}></span>
                    {t.tag_name}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
}
