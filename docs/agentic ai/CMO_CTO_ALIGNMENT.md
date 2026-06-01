# KẾ HOẠCH TRIỂN KHAI TÍNH NĂNG AUTONOMOUS THEO YÊU CẦU CMO

*Tài liệu này là phụ lục kỹ thuật do CTO biên soạn nhằm đáp ứng và hiện thực hóa 3 yêu cầu chiến lược từ CMO đối với hệ thống Autonomous Agentic AI.*

---

## Tổng quan Kỹ thuật (CTO Assessment)

Tôi đã xem xét 3 góp ý của CMO (Chọn mục tiêu, Rút trích Insight, Khống chế ngân sách thử nghiệm). Về mặt kỹ thuật, cả 3 yêu cầu này đều **hoàn toàn khả thi** và ghép nối cực kỳ mượt mà vào kiến trúc Bandit/Bayesian mà team Tech đang xây dựng. Chúng không làm phá vỡ kiến trúc, ngược lại còn giúp thuật toán có "mỏ neo" rõ ràng hơn.

Dưới đây là phương án triển khai kỹ thuật (Technical Implementation) cho từng tính năng.

---

## 1. Tính năng: Cấu hình Mục tiêu Thuật toán (Campaign Objective)

**Yêu cầu CMO:** Thuật toán phải chấm điểm dựa trên mục tiêu cụ thể (Awareness vs. Performance) chứ không đánh giá chung chung.

**Triển khai Kỹ thuật:**
- **Nâng cấp `AgencyState`:** Bổ sung trường `campaign_objective` (Kiểu string hoặc Enum: `BRAND_AWARENESS`, `LEAD_GEN`, `SALES`).
- **Thay đổi tại `scoring_node`:**
  Thuật toán tính toán phần thưởng (Reward Function) sẽ được tham số hóa dựa trên Objective:
  ```python
  def calculate_reward(metrics: dict, objective: str) -> float:
      if objective == "BRAND_AWARENESS":
          # Ưu tiên Impressions cao, CPM thấp, CTR vừa phải
          return (metrics['impressions'] / 1000) * 0.5 - (metrics['cpm'] * 0.3) + (metrics['ctr'] * 0.2)
      elif objective == "LEAD_GEN":
          # Sống còn ở CPA (Cost Per Action / Lead)
          if metrics['cpa'] == 0: return 0 
          return 1.0 / metrics['cpa'] # CPA càng thấp điểm càng cao
  ```
- **UI/UX:** Trên Dashboard khởi tạo chiến dịch, cung cấp một Dropdown cho CMO chọn "Mục tiêu tối ưu". Giá trị này sẽ được inject vào hệ thống ở Node đầu tiên.

---

## 2. Tính năng: "Khám nghiệm tử thi" & Rút trích Bài học (Post-mortem Analysis)

**Yêu cầu CMO:** AI không được "âm thầm khôn lên", phải giải thích bằng ngôn ngữ con người (Insight) tại sao nó lại điều chỉnh trọng số sau mỗi vòng lặp.

**Triển khai Kỹ thuật:**
- **Thêm Node mới: `insight_generator_node`**
  Node này sẽ chạy ngay **sau** `learning_update_node`.
- **Cơ chế hoạt động:**
  Nó sẽ so sánh `current_beliefs` (trước update) và `new_beliefs` (sau update), kết hợp với `metrics_history` mới nhất. Sau đó gọi một LLM Prompt chuyên biệt (Prompt: Analyst) để tổng hợp ra văn bản.
- **Nâng cấp `AgencyState`:** Bổ sung mảng `learning_insights: Annotated[list, operator.add]` để lưu trữ các câu "châm ngôn" đúc kết được qua các vòng.
- **Tích hợp Dashboard:** Ở giao diện Tracking của Dashboard, tạo một Panel riêng tên là "AI Insights". Mỗi khi người dùng bấm nút [Khởi động vòng lặp tiếp theo], panel này sẽ tự động cập nhật một thẻ mới, ví dụ: *"Vòng 4: Đã giảm 15% trọng số của góc nhìn A do CPA tăng đột biến trên tệp khách hàng Z."*

---

## 3. Tính năng: Khống chế Ngân sách Thử nghiệm (Explore Budget Cap)

**Yêu cầu CMO:** Thuật toán Bandit không được phép dùng quá 15% ngân sách cho các nội dung thử nghiệm (Explore), phải giữ 85% tiền an toàn (Exploit).

**Triển khai Kỹ thuật:**
Đây là một bài toán kinh điển của Multi-Armed Bandit. Chúng ta sẽ sử dụng thuật toán **Epsilon-Greedy ($\epsilon$-greedy)** hoặc tinh chỉnh lại Thompson Sampling.

- **Thuật toán $\epsilon$-greedy:**
  Tham số $\epsilon$ (Epsilon) chính là tỷ lệ Explore (Thử nghiệm). 
  - Đặt cấu hình cố định hoặc cho phép CMO chỉnh trên Dashboard: $\epsilon = 0.15$ (15%).
  - Logic tại `action_selector_node`:
    ```python
    import random
    
    epsilon = 0.15 # 15% Explore Budget
    
    if random.random() < epsilon:
        # EXPLORE MODE (15% cơ hội / ngân sách)
        # Chọn ngẫu nhiên một phương án chưa được test nhiều (hoặc dùng UCB để chọn)
        action = select_exploratory_action()
        allocation_tag = "EXPLORE_BUDGET"
    else:
        # EXPLOIT MODE (85% cơ hội / ngân sách)
        # Chọn phương án có Điểm Reward dự kiến cao nhất hiện tại
        action = select_best_known_action()
        allocation_tag = "CORE_BUDGET"
    ```
- **Hành động (Action Output):** Output của Agent không chỉ trả ra "kịch bản nào" mà còn đính kèm nhãn phân bổ (Tag) để đội Ads (hoặc hệ thống API Ads) biết rằng đây là nội dung thuộc nhóm 15% hay 85% để cấu hình ngân sách chạy cho hợp lý.

---

## Kết luận của Tech Team
3 yêu cầu trên rất sắc sảo và hoàn toàn nằm trong khả năng kỹ thuật của kiến trúc hiện tại. Tech team sẽ tiến hành update `AgencyState`, bổ sung các hàm tính toán Reward, và thêm một Node sinh Insight nhỏ. 

Không có xung đột kiến trúc nào. Phiên bản này sẵn sàng để bước vào giai đoạn Coding.