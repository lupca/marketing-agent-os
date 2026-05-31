# Thiết Kế Chức Năng: Market Intelligence & Tích Hợp SerpApi

**Phiên bản:** 2.0 (Final Implementation Plan - Approved by CTO)
**Người viết:** Tech Lead & CTO
**Cập nhật:** 31/05/2026

## 1. Mục tiêu (Objectives)
Nâng cấp Marketing Agent OS thành "Cỗ máy săn tin thị trường". Tự động cào dữ liệu kịch bản và phản hồi của người dùng từ YouTube/Google qua SerpApi, qua đó hỗ trợ phòng Creative (LangGraph) viết kịch bản đánh trúng Search Intent và điểm đau (Pain-point) của khách hàng.

## 2. Giải Pháp Kỹ Thuật (Technical Stack)
* **Search & Comment API:** Dùng `SerpApi` endpoint `youtube` để lấy danh sách thứ hạng và Top 50 Comments (Sentiment Analysis).
* **Transcript API:** Dùng `SerpApi` endpoint `youtube_video_transcript` để lấy toàn bộ text lời thoại.
* **Chống cá nhân hóa:** Fix cứng param `location`, `hl`, `gl` khi gọi API.
* **Context Lớn:** Model tổng hợp cuối cùng (Synthesis) khi gom 10+ transcript bắt buộc dùng model có Context Window lớn (Gemini 1.5 Pro).

## 3. Kiến Trúc Lưu Trữ (Dual-Storage & RAG Schema)
Tuyệt đối KHÔNG tạo bảng mới để giữ DB sạch gọn.
1.  **Cold Storage (Raw Data):** Raw JSON từ SerpApi được lưu vào bucket `market-intel-raw` (MinIO/S3) làm tài nguyên đối chiếu vĩ mô sau này.
2.  **Hot Storage (RAG pgvector):**
    * Sử dụng bảng `rag_chunks` hiện có.
    * Các dữ liệu đã được LLM "làm sạch" (Hooks, Pain-points) sẽ được định dạng Markdown ảo.
    * Lưu các thuộc tính phân tích sâu (ví dụ: `hook_type`, `sentiment`) vào cột `metadata` (JSONB) của bảng `rag_chunks`.
    * Bắt buộc gắn `access_tags = ["market_intel"]` để hệ thống phân quyền với tài liệu nội bộ.

## 4. Tái Cấu Trúc Service Layer (RAG Ingestion Refactor)
Để Agent có thể tự động bơm dữ liệu cào được vào RAG mà không phải viết lại code, hệ thống áp dụng pattern **Service Layer**:
* Rút ruột logic băm vector ngầm từ `api/rag_routes.py` (hàm `upload_document`) thành một Service độc lập: `core/document_service.py -> process_and_store_document()`.
* Hàm này xử lý trọn gói: *Lưu tạm -> Upload MinIO -> Ghi DB `rag_documents` -> Kick Celery worker băm vector chèn vào `rag_chunks`*.
* Bất kỳ đâu (API Controller, Cron Job, LangGraph Agent) đều import Service này để dùng chung 1 luồng chuẩn.

## 5. Luồng Vận Hành (Hybrid Workflow)
* **Luồng Chính (Biz-First - Bảo vệ Dòng tiền):**
    `Analyst Node` (Check CPA/Tồn kho) -> `Intelligence Node` (Kéo SerpApi) -> `Creative Node` (Tổng hợp kịch bản).
* **Luồng Radar (Market-First - Bắt trend):**
    Celery Beat (Cron) chạy lúc 8h sáng hàng ngày -> Agent chạy ngầm quét 5 kênh YouTube đối thủ -> Nếu phát hiện Trend/Gap, tự đối chiếu tồn kho -> Ghi log vào DB và hiển thị Alert lên Widget thông báo trên Chainlit UI cho CMO duyệt.

## 6. Search Playbook (Intelligence Agent Prompt)
* **Footprinting:** Sử dụng `site:`, `intitle:`.
* **Chain-of-Search:** Tìm rộng -> Định vị đối thủ lớn -> Đào sâu Transcript video Viral.
* **Cross-border:** Quét trend nước ngoài (Mỹ, Trung Quốc) dự báo sóng thị trường Việt Nam.


------------

  BIÊN BẢN TỔNG HỢP: NÂNG CẤP HỆ THỐNG MARKET INTELLIGENCE V3.0
  (Ngày chốt: 31/05/2026)

  1. Mục Tiêu Cốt Lõi (Đã được CMO phê duyệt)
  Nâng cấp Marketing Agent OS từ hệ thống nội bộ thành một cỗ máy tình báo thị trường tự động. Sử dụng API để theo
  dõi đối thủ, phân tích tâm lý khách hàng (sentiment), và tự động hóa việc viết kịch bản quảng cáo tối ưu.

  2. Các Quyết Định Chiến Lược (Strategic Decisions)

   * Luồng Vận Hành Kép (Hybrid Workflow):
       * Luồng Chính (Biz-First): Bảo vệ dòng tiền. Lệnh xuất phát từ dữ liệu Kinh doanh (Tồn kho, Target CPA) → Đi
         tìm Trend phù hợp → Creative viết kịch bản. (Chống việc đu trend lãng phí).
       * Luồng Phụ (Market-First/Radar): Định kỳ 8h sáng, Agent chạy ngầm "shadowing" (theo đuôi) 5 kênh đối thủ. Nếu
         phát hiện thị trường có nhu cầu (Gap) mà ta có hàng sẵn, hệ thống sẽ bắn Cảnh báo (Alert) lên Chainlit UI
         cho CMO duyệt chạy chiến dịch.

   * Chiến Lược Lưu Trữ Kép (Dual-Storage Strategy):
       * Cold Storage (Data Lake): Toàn bộ dữ liệu "thô" (Raw JSON) cào được từ thị trường phải được lưu lại toàn vẹn
         vào MinIO/S3 để phục vụ phân tích vĩ mô sau này. Không được vứt bỏ data rác.
       * Hot Storage (RAG Index): Chỉ những dữ liệu đã qua "Bộ lọc Tinh hoa" (LLM Pre-processing) mới được phép đưa
         vào RAG (pgvector) để Creative Agent sử dụng.

  3. Các Quyết Định Kỹ Thuật (Technical Decisions)

   * Bộ Lọc Tinh Hoa (LLM Pre-processing): Trước khi đưa dữ liệu cào được vào RAG, phải dùng LLM để:
       1. Lọc bỏ video rác (không có Call-to-action).
       2. Bóc tách riêng "Hook" (3-5 giây đầu).
       3. Phân tích "Sentiment" từ Top 50 Comments để tìm Pain-point (điểm đau) của khách hàng.
   * Tổng hợp Kịch bản (Synthesis): Khi Agent gom 10+ kịch bản đối thủ lại để phân tích, bắt buộc phải đổi sang dùng
     Model có Context Window lớn (Ví dụ: Gemini 1.5 Pro) để tránh bị tràn bộ nhớ/quên dữ kiện.
   * Search Playbook: Áp dụng System Prompt chuyên biệt cho Agent đi tìm kiếm, trang bị các kỹ năng như Footprinting
     (toán tử tìm kiếm sâu) và Cross-border (đổi IP sang Mỹ/Trung Quốc để đón đầu trend).

  4. Các Quyết Định Tái Cấu Trúc Hệ Thống (System Refactoring)

   * Chuẩn Hóa API: 100% sử dụng hệ sinh thái của SerpApi.
       * Sử dụng endpoint youtube để lấy thứ hạng và comment.
       * Sử dụng endpoint youtube_video_transcript để lấy kịch bản thoại
   * Database Schema: Giữ nguyên bảng rag_chunks hiện tại, không tạo bảng mới. Các siêu dữ liệu (Metadata) như loại
     Hook, điểm Sentiment sẽ được nhét dưới dạng JSONB. Bắt buộc gắn tag access_tags = ["market_intel"].
   * Tái Cấu Trúc Service Layer (RAG Ingestion): Tách toàn bộ logic xử lý nhúng vector (MinIO → DB → Celery) từ API
     Route upload_document ra thành một hàm Service dùng chung (process_and_store_document). Việc này giúp
     Intelligence Agent có thể tự động nạp dữ liệu cào được vào RAG bằng chính luồng chuẩn mà người dùng đang sử
     dụng.


The API endpoint is https://serpapi.com/search?engine=youtube

Đây là hướng dẫn nhanh cách sử dụng [YouTube Video Transcript API](https://serpapi.com/youtube-video-transcript) dành cho developer:

### 1. Endpoint & Method

* **GET** `https://serpapi.com/search.json`

### 2. Các tham số bắt buộc (Required)

* `engine`: Luôn đặt là `youtube_video_transcript`
* `v`: ID của video YouTube (Ví dụ: `Gk8gB5VACZw` từ URL `youtube.com/watch?v=Gk8gB5VACZw`)
* `api_key`: Mã API key cá nhân của bạn trên SerpApi.

### 3. Tham số tùy chọn (Optional)

* `language_code`: Mã ngôn ngữ của bản dịch (Mặc định là `en`).
* `type`: Đặt là `asr` nếu muốn lấy phụ đề tự động (Auto-generated).

---

### 4. Code mẫu nhanh (cURL & Python)

**cURL:**

```bash
curl -X GET "https://serpapi.com/search.json?engine=youtube_video_transcript&v=Gk8gB5VACZw&api_key=YOUR_API_KEY"

```

**Python:**

```python
from serpapi import GoogleSearch

search = GoogleSearch({
    "engine": "youtube_video_transcript",
    "v": "Gk8gB5VACZw",
    "api_key": "YOUR_API_KEY"
})

results = search.get_dict()
transcript = results.get("transcript", [])

```

### 5. Dữ liệu trả về (JSON Response)

Kết quả sẽ trả về một Object chứa mảng `transcript` với đầy đủ mốc thời gian (`start_ms`, `end_ms`) và nội dung chữ (`snippet`):

```json
{
  "transcript": [
    {
      "start_ms": 240,
      "end_ms": 7040,
      "snippet": "hello everyone and welcome...",
      "start_time_text": "0:00"
    }
  ],
  "chapters": [ ... ] // Nếu video có chia chương
}

```

Dưới đây là phiên bản siêu gọn (Cheat Sheet) để bạn copy-paste và chạy ngay:

### 1. HTTP Request

* **Method:** `GET`
* **URL:** `https://serpapi.com/search.json`
* **Query Params:**
* `engine=youtube_video_transcript`
* `v=ID_VIDEO` (Ví dụ: `Gk8gB5VACZw`)
* `api_key=MÃ_API_CỦA_BẠN`



---

### 2. Mẫu Code 1 Dòng

**cURL:**

```bash
curl "https://serpapi.com/search.json?engine=youtube_video_transcript&v=Gk8gB5VACZw&api_key=YOUR_API_KEY"

```

**Python (Sử dụng `requests` gốc, không cần cài thư viện ngoài):**

```python
import requests

res = requests.get("https://serpapi.com/search.json", params={
    "engine": "youtube_video_transcript", "v": "Gk8gB5VACZw", "api_key": "YOUR_API_KEY"
}).json()

print(res.get("transcript"))

```

---

### 3. Cấu trúc Response rút gọn

```json
{
  "transcript": [
    {
      "start_ms": 240,
      "end_ms": 7040,
      "snippet": "Nội dung chữ hiển thị ở đây...",
      "start_time_text": "0:00"
    }
  ]
}

```