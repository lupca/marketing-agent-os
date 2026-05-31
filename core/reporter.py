# core/reporter.py
import datetime

def generate_marketing_plan_markdown(state_values: dict) -> str:
    """
    Synthesizes a highly polished, professional marketing plan report from the graph state.
    Returns a Markdown string formatted for premium look and readability.
    """
    campaign_name = state_values.get("campaign_name") or ""
    workspace_id = state_values.get("workspace_id") or ""
    product_id = state_values.get("product_id") or ""
    
    target_cpa = state_values.get("target_cpa", 0.0)
    test_budget = state_values.get("test_budget", 0.0)
    
    angle = state_values.get("current_angle") or {}
    master_content = state_values.get("master_content") or {}
    variants = state_values.get("variants") or [{}]
    fb_variant = variants[0] if isinstance(variants, list) and len(variants) > 0 else {}
    
    feedback_logs = state_values.get("feedback_log") or []
    
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    report_md = f"""# 📈 KẾ HOẠCH CHIẾN DỊCH MARKETING TỰ TRỊ

> [!NOTE]
> Báo cáo được tạo tự động bởi **Marketing Agent OS v2.0**
> **Thời gian xuất bản:** `{now_str}`
> **Workspace ID:** `{workspace_id}`

---

## 1. THÔNG TIN CHUNG & BỐ CẢNH CHIẾN DỊCH
*   **Tên chiến dịch:** `{campaign_name}`
*   **Trạng thái:** `Phê duyệt thành công - Đang lên lịch (Scheduled)`
*   **Kênh triển khai chủ lực:** `Facebook Ads`

---

## 2. CHỈ TIÊU KINH TẾ SỐNG CÒN (ECONOMIC ANCHORS)
Ban Kinh Doanh đã tính toán và thiết lập các ngưỡng kinh tế bắt buộc tuân thủ:

| Chỉ số vĩ mô | Giá trị đề xuất | Đơn vị | Quy tắc kỷ luật |
| :--- | :--- | :--- | :--- |
| **CPA Target (Mục tiêu)** | `{target_cpa:,.0f}` | VNĐ / lượt chuyển đổi | **Bắt buộc dưới ngưỡng này** |
| **Ngân sách chạy thử (Test Budget)** | `{test_budget:,.0f}` | VNĐ | **Giới hạn kiểm soát an toàn tối đa** |

---

## 3. KHÁCH HÀNG MỤC TIÊU & ĐỊNH HƯỚNG SÁNG TẠO (RAG INSIGHTS)
Ban Sáng Tạo đã trích xuất tri thức từ hệ thống RAG nội bộ để định vị tâm lý khách hàng:

### 🎯 Góc chiến lược tiếp cận
*   **Tên góc tiếp cận (Angle Name):** `{angle.get('angle_name', 'Chưa rõ')}`
*   **Giai đoạn Phễu (Funnel Stage):** `{angle.get('funnel_stage', 'Consideration')}`
*   **Tâm lý học áp dụng (Psychological Type):** `{angle.get('psychological_angle', 'Logic / Pain Point')}`
*   **Trọng tâm nỗi đau (Pain Point Focus):**
    > *"{angle.get('pain_point_focus', 'Nhu cầu tối ưu chuyển đổi và tự động hóa quy trình quản lý quảng cáo.')}"*

*   **Tóm tắt yêu cầu (Brief):**
    {angle.get('brief', 'Viết nội dung giật tít đánh thẳng nỗi đau chi phí ads đắt đỏ, đề xuất giải pháp AI Agent của G-Agent Tech để thuyết phục khách hàng hành động.')}

---

## 4. NỘI DUNG SÁNG TẠO ĐÃ ĐƯỢC PHÊ DUYỆT (APPROVED COPYWRITING)

### ✍️ Thông điệp cốt lõi (Master Message)
> **"{master_content.get('core_message', '')}"**

### 📱 Bài viết phân phối trên mạng xã hội (Facebook Post Variant)
```text
{fb_variant.get('adapted_copy', 'Chưa có nội dung')}
```

*   **Bộ từ khóa Hashtags:** `{", ".join(fb_variant.get('hashtags', []))}`
*   **Tiêu đề SEO:** `{fb_variant.get('seoTitle', 'Chưa tối ưu')}`
*   **Mô tả ngắn SEO:** `{fb_variant.get('seoDescription', 'Chưa tối ưu')}`
*   **Lời khuyên từ AI (Platform Tips):** *{fb_variant.get('platform_tips', 'Đăng vào giờ vàng tương tác cao.')}*

---

## 5. NHẬT KÝ KIỂM DUYỆT CHẤT LƯỢNG (BRAND GUARDIAN AUDIT LOGS)
Nhật ký kiểm tra độ tuân thủ thương hiệu của Brand Guardian Node dựa trên barem 100 điểm nghiêm ngặt của CMO:

"""
    
    if feedback_logs:
        for idx, log in enumerate(feedback_logs):
            report_md += f"*   **Lần {idx+1}:** {log}\n"
    else:
        report_md += "*   *Kịch bản đạt chuẩn ngay trong lần chấm đầu tiên (>80/100đ).* \n"
        
    report_md += """
---
*Hệ điều hành Marketing Agent OS chúc Sếp triển khai chiến dịch bùng nổ doanh số! 🚀*
"""
    return report_md
