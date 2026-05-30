# KẾ HOẠCH REFACTOR MÃ NGUỒN: TIÊU CHUẨN CLEAN CODE VÀ MAINTAINABILITY (v2.1)

## 1. Báo cáo Hiện trạng (Tech Lead Assessment)

Sau khi review mã nguồn các module cốt lõi (như `core/ollama_client.py` và `graphs/creative.py`), tôi đánh giá hệ thống hiện tại đang gặp phải tình trạng **"Scripting Code"** (code chạy được nhưng chưa đạt chuẩn phần mềm Enterprise). 

Dưới đây là các vi phạm nghiêm trọng (Code Smells) theo tiêu chuẩn **Clean Code**, **DRY** (Don't Repeat Yourself) và **SRP** (Single Responsibility Principle):

1. **Fat Nodes (Các hàm Node quá cồng kềnh):** 
   - Trong `graphs/creative.py`, các hàm như `copywriter_node` dài hàng trăm dòng. Chúng ôm đồm quá nhiều trách nhiệm: Lấy dữ liệu State -> Lắp ghép Prompt bằng String Format -> Gọi API LLM -> Parse JSON -> Fallback dữ liệu cứng -> Cắt Context -> Ghi Log -> Trả về State.
2. **Vi phạm quy tắc DRY (Lặp code diện rộng):**
   - Đoạn code `import json_repair` nằm bên trong khối `try/except` bị lặp lại sao chép/dán y hệt ở 3 Node (Strategist, Copywriter, Guardian).
   - Đoạn code lấy tin nhắn và cắt Context (`raw_messages = state.get...`, `safe_messages = get_trimmed_context...`) bị viết lặp đi lặp lại ở cuối mỗi Node.
3. **Quản lý Thư viện / Re-inventing the Wheel:**
   - Trong `core/ollama_client.py`, dự án đã import `ChatOllama` từ thư viện `langchain_community`, nhưng lại tự dùng thư viện `requests` thô (raw HTTP calls) để gọi API generate và embedding. Việc này làm lãng phí các tính năng tối ưu có sẵn của Langchain (như Tool Calling, Structured Output, Retry logic).
4. **Hardcode (Magic Strings & Magic Numbers):**
   - Các con số như `14000`, `16384`, `1050000.0`, `80` (điểm đỗ Guardian) rải rác khắp nơi thay vì được gom vào một tệp `config.py` chung.
   - Fallback JSON được gắn cứng hẳn vào trong hàm. Nếu muốn sửa mẫu mặc định, Dev phải đọc hàng trăm dòng code.
5. **Import cục bộ bên trong hàm:** 
   - Việc `import json_repair` hay `import re` đặt bên trong thân hàm làm giảm hiệu năng khi hàm được gọi nhiều lần và vi phạm PEP8.

---

## 2. Kế hoạch Refactor (Refactoring Plan)

Để giải quyết tình trạng này, đội Dev sẽ thực hiện Refactor theo 4 Giai đoạn sau:

### Giai đoạn 1: Chuẩn hóa `core/ollama_client.py` (Tận dụng LangChain)
*   **Hành động:** Loại bỏ hoàn toàn thư viện `requests` tự chế trong `generate_text` và `get_embedding`.
*   **Triển khai:** 
    *   Sử dụng `ChatOllama.invoke()` cho LLM thay vì gọi HTTP Post. Cấu hình cứng `num_ctx=16384` vào Model Instance ngay lúc khởi tạo.
    *   Sử dụng `OllamaEmbeddings` từ `langchain_community.embeddings` để lấy vector.
    *   **Mục tiêu:** Giảm 50% số dòng code trong file này, giao việc xử lý timeout và retry cho LangChain đảm nhiệm.

### Giai đoạn 2: Tách lớp Xử lý JSON (JSON Extraction Layer)
*   **Hành động:** Chấm dứt việc lặp lại khối `try/except json_repair.loads(...)` ở mọi Node.
*   **Triển khai:**
    *   Tạo file mới `core/utils.py`.
    *   Viết một hàm chuẩn: `parse_llm_json(response_str: str, fallback_data: dict) -> dict`. Hàm này sẽ chịu trách nhiệm import `json_repair`, dọn dẹp chuỗi, và trả về dict. Nếu lỗi, trả về `fallback_data`.
    *   Di dời toàn bộ Fallback Data cứng trong `creative.py` ra một tệp riêng như `reference/prompt/fallbacks.py`.

### Giai đoạn 3: "Giảm béo" cho LangGraph Nodes (SRP & Decorators)
*   **Hành động:** Chia nhỏ `copywriter_node`, `strategist_node` để chúng chỉ tập trung vào việc **điều hướng Graph**, không xử lý logic hạ tầng.
*   **Triển khai:**
    *   **Extract Prompting:** Dùng `PromptTemplate` của LangChain thay cho hàm `str.format()` thuần túy. Tạo một hàm riêng `build_copywriter_prompt(state)` bên ngoài Node.
    *   **Gom nhóm Logging & Trimming:** Viết một hàm Helper (hoặc Python Decorator) để tự động gọi `get_trimmed_context` và `log_decision` trước khi Node trả về giá trị (Return). 
    *   *Kỳ vọng:* Mỗi hàm Node trong `graphs/creative.py` chỉ nên dài tối đa 20 - 30 dòng code (Clean Code rule).

### Giai đoạn 4: Quản lý Cấu hình Tập trung (Configuration Management)
*   **Hành động:** Xóa bỏ "Magic Numbers" và "Magic Strings".
*   **Triển khai:**
    *   Tạo file `config/settings.py`.
    *   Chuyển các hằng số: `MAX_CONTEXT_TOKENS = 14000`, `LLM_CTX_WINDOW = 16384`, `GUARDIAN_PASS_SCORE = 80` vào file này.
    *   Các Node chỉ import hằng số này để kiểm tra điều kiện IF.

---

## 3. Ví dụ Code Sau Refactor (Expected Outcome)

*Mô phỏng hàm Node sau khi đã "giảm béo" và tách lớp:*

```python
# graphs/creative.py (Sau Refactor)
from core.utils import parse_llm_json, trim_and_log
from core.ollama_client import generate_structured_json
from reference.prompt.fallbacks import STRATEGIST_FALLBACK
from config.settings import MAX_CONTEXT_TOKENS

def strategist_node(state: AgencyState) -> dict:
    logger.info("Executing Strategist Node...")
    
    # 1. Chuẩn bị Dữ liệu (Delegated to external builder)
    final_prompt = build_strategist_prompt(state)
    
    # 2. Gọi AI & Parse JSON an toàn (Delegated to core util)
    response_str = generate_structured_json(final_prompt)
    angle_data = parse_llm_json(response_str, fallback=STRATEGIST_FALLBACK)
    
    # 3. Trả về kết quả, Decorator/Helper sẽ tự động trim_messages và ghi Audit Log
    return trim_and_log(
        state=state,
        new_state_data={"current_angle": angle_data, "sop_stage": "creative_generation"},
        message=f"🧠 [Strategist] Angle đề xuất: {angle_data.get('angle_name')}",
        log_action="Formulate Marketing Angle"
    )
```

## 4. Hành động Tiếp theo (Next Steps)
Đội Dev cần đọc kỹ tài liệu này. 
Chúng ta sẽ bắt đầu từ **Giai đoạn 2 (Tách lớp JSON)** và **Giai đoạn 3 (Giảm béo Node)** vì nó giải quyết trực tiếp sự lặp lặp và rườm rà hiện tại, giúp code dễ bảo trì ngay lập tức.