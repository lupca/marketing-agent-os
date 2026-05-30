# TÀI LIỆU THIẾT KẾ KỸ THUẬT: QUẢN LÝ CONTEXT WINDOW VÀ TỐI ƯU TOKENS (CONTEXT MANAGEMENT)

## 1. Mục Tiêu (Objectives)
Tài liệu này xác định quy chuẩn thiết kế để quản lý **Context Window (Cửa sổ Ngữ cảnh)** của các LLM Agent trong hệ thống Marketing Agent OS. 
Mục tiêu là giải quyết triệt để tình trạng lỗi tràn bộ nhớ (Out of Memory / Context Exceeded), đảm bảo độ trễ (Latency) ổn định và giúp AI Agent (Copywriter, Guardian...) không bị "mất tập trung" (Lost in the middle) khi lịch sử hội thoại phình to.

---

## 2. Tiêu Chuẩn Cấu Hình (Configuration Standards)

### 2.1. Giới hạn Context Mặc định (num_ctx)
Tất cả các lệnh gọi LLM tới backend Ollama (Model Qwen2.5 14B hoặc tương đương) bắt buộc phải cấu hình cứng tham số kích thước cửa sổ ngữ cảnh.

*   **Tham số cấu hình:** `num_ctx = 16384` (Tương đương 16K Tokens).
*   **Lý do:** Kích thước 16K là điểm cân bằng hoàn hảo giữa việc giữ được luồng lịch sử dài (cãi nhau nhiều hiệp) và khả năng xử lý của GPU phần cứng nội bộ, tránh làm treo server.

**Mã mẫu cập nhật trong `core/ollama_client.py`:**
```python
# Ví dụ cấu hình (sử dụng langchain_community hoặc HTTP Client)
llm = ChatOllama(
    model="qwen2.5:14b-instruct",
    temperature=0.7,
    num_ctx=16384,  # <-- Bắt buộc cấu hình tham số này
    # các thông số khác...
)
```

---

## 3. Chiến Lược Quản Lý Ngữ Cảnh Tầng Ngắn Hạn (Short-Term Memory Trimming)

**Vấn đề:** Trong `AgencyState`, mảng `messages: Annotated[List[BaseMessage], operator.add]` sẽ liên tục cộng dồn tin nhắn không giới hạn. Nếu không can thiệp, dữ liệu truyền đi sẽ sớm vượt qua mốc 16,384 tokens.

**Giải pháp Kỹ thuật: Message Trimming (Cắt tỉa tin nhắn tự động)**
Trước khi bất kỳ một Node nào (Analyst, Copywriter, Guardian...) thực hiện gọi LLM (`llm.invoke()`), Node đó phải đi qua một bộ lọc cắt tỉa tin nhắn để đảm bảo tổng số lượng Tokens nạp vào LLM không bao giờ vượt qua ngưỡng an toàn.

*   **Ngưỡng an toàn quy định:** Giữ lại tối đa **14,000 tokens** cho lịch sử chat (Để chừa khoảng 2,384 tokens cho System Prompt và Câu trả lời - Generation output).
*   **Thư viện sử dụng:** Sử dụng hàm `trim_messages` của `langchain_core.messages`.

### Hướng dẫn Triển khai Code (Implementation Guide)

**Task:** Xây dựng một hàm tiện ích (Helper utility) và áp dụng vào tất cả các Agent Node.

```python
# Tạo helper trong một file utils (ví dụ: core/utils.py)
from langchain_core.messages import trim_messages
from core.ollama_client import llm # Giả sử llm đã có num_ctx=16384

def get_trimmed_context(messages, max_tokens=14000):
    """
    Giữ lại lịch sử hội thoại gần nhất sao cho tổng số token <= max_tokens.
    Ưu tiên giữ lại SystemMessage (nếu có ở đầu).
    """
    trimmed_messages = trim_messages(
        messages,
        max_tokens=max_tokens,
        strategy="last",          # Cắt bỏ phần cũ, giữ phần mới nhất
        token_counter=llm,        # Dùng bộ đếm token của chính mô hình đang chạy
        include_system=True,      # Luôn luôn giữ lại luật chơi (System Prompt) ban đầu
        allow_partial=False       # Không cắt ngang một tin nhắn (cắt tròn vẹn nguyên message)
    )
    return trimmed_messages
```

**Cách áp dụng vào luồng LangGraph:**
Mỗi Node trước khi tư duy sẽ lọc Context.

```python
# Ví dụ trong file: graphs/creative.py (Node Copywriter)
def copywriter_node(state: AgencyState):
    logger.info("Copywriter Node running...")
    
    raw_messages = state.get("messages", [])
    
    # BẮT BUỘC: Cắt tỉa Context Window trước khi đưa vào LLM
    safe_messages = get_trimmed_context(raw_messages, max_tokens=14000)
    
    # Nạp safe_messages vào Prompt hoặc trực tiếp vào llm.invoke()
    response = llm.invoke(safe_messages)
    
    return {"messages": [response]}
```

---

## 4. Tương tác với Tầng Dài Hạn (Long-Term Memory Integration)

Việc cắt tỉa tin nhắn cũ ở tầng Short-Term (như mục 3) có thể làm LLM "quên" mất các quyết định quan trọng ở đầu cuộc hội thoại (ví dụ: CMO đã chê Angle này 2 ngày trước). 

Để giải quyết vấn đề "mất trí nhớ" do Trimming, hệ thống vận hành theo quy tắc Kiến trúc Kép (Dual-Layer):
1. **Lịch sử bị cắt:** Các tin nhắn dài dằng dặc sẽ bị cắt vứt đi trước khi gọi LLM.
2. **Ký ức được cứu lại (RAG):** Những gì tinh túy nhất, các lời "Chê bai/Feedback" của CMO đã được lưu thành dạng Vector vào bảng `rag_knowledgebase` (Theo tài liệu `LONG_TERM_MEMORY_DESIGN.md`).
3. **Tiêm (Inject) Ký ức vào Prompt:** Trước khi Node Copywriter chạy, nó sẽ tự động dùng Vector Search quét các lỗi sai cũ và nhét chúng vào **System Prompt**. Do `trim_messages` được cấu hình `include_system=True`, các bài học này vĩnh viễn không bị xóa khỏi Context Window của lần gọi API đó.

---

## 5. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
Đội ngũ phát triển hoàn thành tính năng khi:
1.  Tham số `num_ctx=16384` được gán cứng vào tất cả các object khởi tạo LLM.
2.  Hàm `trim_messages` được triển khai tại mọi Node thực thi LLM.
3.  Khi tạo một luồng chat cực dài (copy/paste đoạn text 20,000 chữ vào Chat UI), ứng dụng không bị crash vì lỗi `Context Exceeded`, mà LLM vẫn có khả năng đọc và phản hồi dựa trên phần cuối của đoạn text.
