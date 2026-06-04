# TÀI LIỆU THIẾT KẾ KỸ THUẬT: CMO BUSINESS INTELLIGENCE DASHBOARD
**Chức vụ chịu trách nhiệm:** Chief Technology Officer (CTO)  
**Dành cho:** Toàn bộ đội ngũ Phát triển (Developers)  
**Trạng thái:** Sẵn sàng Triển khai (Approved by CMO)  

---

## 1. Tổng Quan Kiến Trúc Tích Hợp (Architecture Overview)

Đúng như định hướng, để hệ thống gọn nhẹ, chúng ta **không tạo server phân tích riêng** mà sẽ nhúng trực tiếp lớp API Dashboard vào tiến trình FastAPI hiện tại:

```text
+-------------------------------------------------------------+
|                     FASTAPI BACKEND                         |
|  (FastAPI instance running under localhost:8000)            |
+-------------------------------------------------------------+
       |                                              |
       v [API Endpoints]                              v [Frontend Redirect]
+------------------------------+             +------------------------------+
|   GET /api/dashboard/metrics |             |   GET /dashboard             |
|   (Truy vấn số liệu & RAG)   |             |   (Redirect về Next.js)      |
+------------------------------+             +------------------------------+
|  POST /api/dashboard/simulate|
|   (Giả lập hòa vốn & phân bổ)|
+------------------------------+
```

---

## 2. Đặc Tả Thiết Kế CSDL & Giải Thuật Chỉ Số (Database & Algorithms)

Để đáp ứng đầy đủ các yêu cầu chiến lược của CMO, đội ngũ phát triển cần triển khai chính xác các công thức toán học và logic SQL sau vào API:

### A. Tách Biệt Paid CAC và Blended CAC
*   **Paid CAC (Paid Customer Acquisition Cost):**
    $$\text{Paid CAC} = \frac{\sum (\text{Chi phí thực tế của các Variant})}{\text{Tổng số Lead sinh ra từ quảng cáo trả phí}}$$
    *Cách thực hiện trong SQL:*
    ```sql
    SELECT 
        SUM(CAST(metadata->>'metric_spend' AS NUMERIC)) as total_spend,
        SUM(metric_comments + metric_likes * 0.1) as total_leads -- Công thức quy đổi Lead mẫu
    FROM platform_variants
    WHERE publish_status IN ('published', 'scaled');
    ```
*   **Blended CAC (Blended Customer Acquisition Cost):**
    $$\text{Blended CAC} = \frac{\sum (\text{Chi phí thực tế của các Variant})}{\text{Tổng số Lead toàn hệ thống (bao gồm cả Organic)}}$$

### B. Chỉ Số LTV:CAC và Đèn Cảnh Báo Sức Khỏe
*   **LTV (Lifetime Value) mặc định:** `5,000,000 VNĐ` (Lấy từ dữ liệu seeded giá trị trọn đời trung bình của khách hàng mua sản phẩm G-Agent Tech).
*   **Thuật toán hiển thị đèn cảnh báo:**
    *   **LTV / Paid CAC >= 3.0:** Đèn **Xanh lá (Green)** $\rightarrow$ Sức khỏe phễu cực tốt, sẵn sàng vít thêm ngân sách.
    *   **1.5 <= LTV / Paid CAC < 3.0:** Đèn **Vàng (Yellow)** $\rightarrow$ Hiệu năng ở mức an toàn, cần tối ưu nhẹ.
    *   **LTV / Paid CAC < 1.5:** Đèn **Đỏ (Red)** $\rightarrow$ Rủi ro cao, tự động khuyến nghị giảm hoặc dừng ngân sách.

### C. Giải Thuật Phát Hiện Sớm Creative Fatigue (Suy giảm hiệu suất kịch bản)
*   **Logic toán học:** So sánh chỉ số CPA trung bình của một Variant trong 3 ngày gần nhất ($\text{CPA}_{3d}$) so với baseline trung bình 7 ngày trước đó ($\text{CPA}_{7d}$).
*   **Điều kiện kích hoạt cảnh báo Fatigue:**
    $$\text{CPA}_{3d} > 1.15 \times \text{CPA}_{7d}$$
*   *Hành động của UI:* Nếu điều kiện trên thỏa mãn, hiển thị nhãn cảnh báo **`⚠️ Creative Fatigue (Hiệu suất giảm)`** màu cam nhấp nháy bên cạnh Variant tương ứng.

---

## 3. Đặc Tả REST API (API Endpoints Specification)

Dev triển khai 3 endpoints mới trong tệp `app.py`:

### Endpoint 1: Trình Redirect Giao diện
*   **Route:** `GET /dashboard`
*   **Mô tả:** Trả về `RedirectResponse` đẩy người dùng sang cổng 3000 (Next.js Frontend).

### Endpoint 2: Truy vấn Số liệu Chiến dịch & Tri thức
*   **Route:** `GET /api/dashboard/metrics`
*   **Định dạng phản hồi (JSON):**
    ```json
    {
      "paid_cac": 850000,
      "blended_cac": 520000,
      "ltv_cac_ratio": 5.88,
      "ltv_cac_health": "green",
      "cac_payback_months": 2.4,
      "active_campaigns": 3,
      "budget_burn_rate_pct": 42.5,
      "hall_of_fame": [
        {
          "variant_id": "uuid-1",
          "angle_name": "Góc giải phóng thời gian",
          "platform": "facebook",
          "cpa": 720000,
          "ctr": 4.8
        }
      ],
      "hall_of_shame": [
        {
          "variant_id": "uuid-2",
          "failed_copy": "🔥 Mệt mỏi vì ads đắt?...",
          "failed_cpa": 1400000,
          "reason_killed": "CPA thực tế 1.4M vượt mức target 1.05M"
        }
      ],
      "anti_patterns_rag": [
        {
          "id": "rag-1",
          "source_name": "Content_Guidelines.pdf",
          "content": "Tuyệt đối tránh sử dụng các cam kết 100% không căn cứ..."
        }
      ]
    }
    ```

### Endpoint 3: Trình Giả Lập Scenario & AI Budget Advisor
*   **Route:** `POST /api/dashboard/simulate`
*   **Payload gửi lên (JSON):**
    ```json
    {
      "test_budget": 10000000,
      "retail_price": 5000000,
      "cost_price": 1500000,
      "target_margin": 0.3
    }
    ```
*   **Giải thuật AI gợi ý phân bổ ngân sách:**
    *   Hệ thống sẽ lấy CPA lịch sử của Facebook (vd: 800k) và TikTok (vd: 1.2M).
    *   Tính toán tỷ lệ phân bổ tối ưu theo trọng số CPA:
        $$\% \text{ Ngân sách Facebook} = \frac{1 / \text{CPA}_{FB}}{1 / \text{CPA}_{FB} + 1 / \text{CPA}_{TT}}$$
*   **Định dạng phản hồi (JSON):**
    ```json
    {
      "target_cpa": 1050000,
      "break_even_leads": 3,
      "ai_advisor_text": "Dựa trên CPA lịch sử cực tốt của Facebook (800k VNĐ), khuyến nghị phân bổ 60% vào Facebook Ads và 40% vào TikTok Ads để tối ưu hóa tỷ lệ chuyển đổi."
    }
    ```

---

## 4. Đặc Tả Giao Diện UX/UI (Vanilla HTML/CSS/JS Specification)

### A. CSS Glassmorphism Tokens (`data/templates/dashboard.html`)
Mọi thẻ hiển thị (Cards) bắt buộc phải tuân thủ nghiêm ngặt các token CSS sau để đạt được độ premium đồng bộ:
```css
:root {
  --bg-dark: #0f172a;       /* Xám đậm Slate 900 làm nền chính */
  --glass-bg: rgba(30, 41, 59, 0.45); /* Nền kính mờ */
  --glass-border: rgba(255, 255, 255, 0.08); /* Viền kính siêu mảnh */
  --neon-green: #10b981;    /* Xanh ngọc neon an toàn */
  --neon-red: #ef4444;      /* Đỏ hồng neon cảnh báo */
  --neon-orange: #f97316;   /* Cam neon cảnh báo suy thoái */
  --neon-purple: #8b5cf6;   /* Tím neon điểm nhấn */
}

.glass-card {
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-radius: 16px;
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.glass-card:hover {
  transform: translateY(-4px);
  border-color: rgba(139, 92, 246, 0.4); /* Glow tím nhẹ khi hover */
  box-shadow: 0 12px 40px 0 rgba(139, 92, 246, 0.15);
}
```

### B. Bố Cục Trang (Layout Structure Grid)
Trang được chia làm 3 phân khu chính cực kỳ khoa học trên một màn hình:
1.  **Hàng đầu tiên (Top Row - 4 Columns):**
    *   Card 1: Blended CAC vs Paid CAC (2 số hiển thị song song lớn).
    *   Card 2: LTV:CAC Ratio (Đi kèm đèn tròn nhấp nháy chỉ báo Xanh/Vàng/Đỏ).
    *   Card 3: CAC Payback Period (Thống kê thời gian hoàn vốn theo tháng).
    *   Card 4: Budget Burn Rate % (Thanh tiến trình tiến độ tiêu tiền ngân sách).
2.  **Hàng thứ hai (Middle Row - Chia đôi 50/50):**
    *   **Bên trái (Hall of Fame):** Các Winning Angles có CPA thấp.
    *   **Bên phải (Hall of Shame & Anti-patterns):** Các kịch bản bị tắt kèm nhãn cảnh báo RAG tránh lặp lại.
3.  **Hàng thứ ba (Bottom Row - Chia đôi 60/40):**
    *   **Bên trái (60%):** Hai biểu đồ động Chart.js (Biến động CPA so với Target CPA & Phễu rụng leads).
    *   **Bên phải (40%):** Bảng giả lập kịch bản (Scenario Simulator) với thanh trượt mượt mà kèm hộp thoại **AI Budget Advisor** tự động thay đổi chữ khi kéo trượt.

---

## 5. Kế Hoạch Triển Khai Cho Lập Trình Viên (Action Items)

1.  **Bước 1:** Khởi tạo UI trên Next.js (`frontend/src/app/dashboard/page.tsx`).
2.  **Bước 2:** Đăng ký các FastAPI endpoints trong `api/dashboard_routes.py`, kết nối trực tiếp CSDL qua `SessionLocal`.
3.  **Bước 3:** Viết script kiểm thử tự động tích hợp `tests/test_api_dashboard.py` gọi thử các API để đảm bảo kết quả JSON trả về xanh.
4.  **Bước 4:** Khởi động máy chủ, mở trình duyệt truy cập `/dashboard` để nghiệm thu trực quan.
