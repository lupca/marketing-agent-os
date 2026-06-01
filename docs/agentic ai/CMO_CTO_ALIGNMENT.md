# KẾ HOẠCH TRIỂN KHAI TÍNH NĂNG THEO YÊU CẦU CMO (BẢN ENTERPRISE)

*Tài liệu này là phụ lục kỹ thuật do CTO biên soạn, đã được cập nhật sau vòng thẩm định Enterprise Architecture. Tài liệu định hướng cách đáp ứng yêu cầu của CMO mà không vi phạm nguyên tắc quản trị rủi ro hệ thống.*

---

## 1. Tính năng: Cấu hình Mục tiêu Thuật toán (Campaign Objective) - GIỮ NGUYÊN

**Yêu cầu CMO:** Thuật toán phải chấm điểm dựa trên mục tiêu cụ thể (Awareness vs. Performance).
**Giải pháp Kỹ thuật:**
- **Thực thi ngoài Graph:** Hàm `calculate_reward` sẽ được Backend Python (Cronjob) chạy trước khi gọi LangGraph.
- Backend lấy số liệu từ OLAP, tính toán Reward theo công thức:
  ```python
  def calculate_reward(metrics: dict, objective: str) -> float:
      if objective == "BRAND_AWARENESS":
          return (metrics['impressions'] / 1000) * 0.5 - (metrics['cpm'] * 0.3) + (metrics['ctr'] * 0.2)
      elif objective == "LEAD_GEN":
          if metrics['cpa'] == 0: return 0 
          return 1.0 / metrics['cpa']
  ```
- Kết quả trọng số (Priors) được bơm trực tiếp vào `AgencyState` của LangGraph.

---

## 2. Tính năng: "Khám nghiệm tử thi" (Post-mortem Analysis) - CÓ HITL

**Yêu cầu CMO:** AI phải giải thích bằng ngôn ngữ con người (Insight) tại sao nó lại điều chỉnh trọng số.
**Giải pháp Kỹ thuật (Chống Data Poisoning):**
- Vẫn duy trì việc dùng LLM để sinh Insight (như *"Vòng 4: CPA tăng do tệp GenZ không thích video dài"*).
- **QUAN TRỌNG:** Tuyệt đối không tự động băm vector vào RAG.
- LLM sinh ra Insight sẽ được lưu vào Database OLAP ở bảng `pending_insights`.
- **Human-in-the-Loop (HITL):** CMO hoặc Quản lý sẽ thấy danh sách này trên Dashboard. Chỉ khi có người bấm nút **[Phê duyệt & Lưu vào Bộ nhớ]**, hệ thống mới đẩy đoạn text đó vào `rag_chunks`. 
- Hành động này bẻ gãy hoàn toàn vòng lặp "tự đầu độc tri thức" của LLM.

---

## 3. Tính năng: Đa dạng hóa Sáng tạo (Creative Diversity) - THAY THẾ BUDGET CAP

**Yêu cầu CMO cũ:** Khống chế 15% ngân sách cho thử nghiệm, 85% an toàn.
**Góc nhìn Enterprise:** Ép nền tảng AdTech chạy theo ngân sách cứng sẽ phá vỡ Machine Learning (Learning Phase) của Meta/Google, làm CPA tăng vọt.

**Giải pháp Kỹ thuật Mới (Creative Intelligence Pivot):**
- Chuyển khái niệm tỷ lệ 15/85 từ **Ngân sách** sang **Sản lượng Nội dung (Content Output)**.
- Thuật toán Bandit ($\epsilon$-greedy) vẫn chạy, nhưng không xuất ra "Allocation Tag" cho Ads, mà xuất ra chỉ thị cho Agent.
- **Ví dụ thực thi:** Nếu Graph được yêu cầu đẻ ra 10 biến thể quảng cáo (10 Dynamic Creatives):
  - 8 biến thể (80% Exploit): Agent sẽ viết dựa chặt chẽ trên các góc độ (Angles) đang có điểm Reward cao nhất hiện tại.
  - 2 biến thể (20% Explore): Agent được phép thỏa sức sáng tạo, áp dụng các góc độ tâm lý mới hoàn toàn (Curiosity, FOMO) chưa từng được test.
- Toàn bộ 10 biến thể này được đẩy thẳng lên Meta/Google Ads. Hệ thống AI đấu thầu của Meta sẽ **tự động quyết định dồn bao nhiêu tiền** cho biến thể nào hiệu quả. Nhiệm vụ của LangGraph chỉ là nhà máy sản xuất nguyên liệu thô (Creative) chất lượng cao.