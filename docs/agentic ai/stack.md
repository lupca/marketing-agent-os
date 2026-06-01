
# TÀI LIỆU THIẾT KẾ KIẾN TRÚC: AUTONOMOUS COGNITIVE CODER (ACC)

## 1. Tầm nhìn Kiến trúc (Architectural Vision)

Hệ thống ACC thay thế kỹ thuật Prompt Engineering truyền thống bằng một **Động cơ Suy luận Xác suất (Probabilistic Reasoning Engine)**. Hệ thống được chia làm 3 phân hệ (Layers) tương ứng với 3 trụ cột bạn yêu cầu:

### Layer 1: Episodic Memory (Action-Oriented RAG & Belief Seeding)

* **Vấn đề của RAG cũ:** Dùng Vector DB để nhồi nhét documentation vào Context Window, khiến AI bị loãng thông tin và ảo giác (hallucination).
* **Giải pháp mới (Action-Oriented):** RAG lưu trữ các `[State, Action, Reward, Outcome]`. Đây gọi là "Ký ức từng trải" (Episodic Memory).
* **Belief Seeding:** Khi AI nhận Task mới, RAG không trả về text. Nó Vector hóa Task, query DB và **cấy ghép niềm tin (Beliefs)** cùng **Xác suất tiên nghiệm (Priors)** vào hệ thống.
* *Ví dụ:* Thay vì trả về doc của SQLAlchemy, RAG trả về: *"Niềm tin: Trong dự án này, chiến lược dùng Raw SQL có tỷ lệ thành công 90%, dùng ORM thất bại liên tục do thiếu RAM. Khuyến nghị Action: Raw SQL."*



### Layer 2: Cognitive Engine (Multi-armed Bandits & Bayesian Update)

* **Multi-armed Bandits (MAB):** Khi giải quyết bug, Agent có nhiều "cánh tay" (Chiến lược): *Đọc Log, Viết lại từ đầu, Thêm Try/Catch, Search StackOverflow*. Thuật toán **Thompson Sampling** được sử dụng để cân bằng giữa **Exploitation** (Khai thác chiến lược đang chạy tốt) và **Exploration** (Thử nghiệm chiến lược mới).
* **Reward Function Design (Hàm phần thưởng):** Quyết định việc định hình hành vi AI. `Reward = W1*(Pass_Tests) - W2*(Cyclomatic_Complexity) - W3*(Execution_Time)`. Code pass test nhưng chạy chậm (O(n^2)) vẫn nhận Reward thấp.
* **Bayesian Updates:** Hệ thống duy trì phân phối Beta $(\alpha, \beta)$ cho từng chiến lược. Sau mỗi vòng lặp code và test, định lý Bayes cập nhật lại phân phối này. Nếu một chiến lược liên tục fail ($\beta$ tăng), MAB sẽ tự động bẻ lái AI sang cách khác, **bẻ gãy hoàn toàn "bẫy vòng lặp ảo giác" (Infinite Hallucination Loop) của LLM.**

### Layer 3: Orchestration OS (LangGraph Advanced)

* **State Management:** Quản lý Abstract Syntax Tree (AST), Working Memory, và Lịch sử lỗi thông qua đồ thị tuần hoàn (Cyclic Graph) dùng `TypedDict`.
* **Postgres Checkpointer (Thread-level Persistence):** Tác vụ SWE có thể mất nhiều giờ. `PostgresSaver` lưu snapshot của đồ thị xuống DB sau mỗi Node. Nó cung cấp khả năng:
* **Fault Tolerance:** Server sập, AI vẫn nhớ dòng code đang viết dở khi khởi động lại.
* **Time-Travel Debugging:** Có thể rollback luồng suy nghĩ của AI về 5 bước trước nếu đi vào ngõ cụt.


* **Dynamic Interrupts:** Sử dụng tính năng `interrupt()` mới nhất của LangGraph. Khi Agent quyết định dùng các lệnh nhạy cảm (`git push --force`, `DROP TABLE`), Graph chủ động **đóng băng (suspend)**, giải phóng RAM, và nén State chờ Kỹ sư (Human-in-the-loop) duyệt. Sau khi duyệt, hệ thống gọi `Command(resume=...)` để tiếp tục.

---

# PHÁC THẢO MÃ NGUỒN (AI SKILL BLUEPRINT)

Dưới đây là bộ khung mã nguồn (sử dụng Python hiện đại, Pydantic, numpy và LangGraph v0.2+). Bộ Skill này có thể được đóng gói để AI trực tiếp gọi và vận hành luồng suy nghĩ của nó.

### LƯU Ý, ĐÂY CHỈ LÀ MÃ NGUỒN THAM KHẢO

### Module 1: Định nghĩa Trạng thái & Memory Models

```python
import operator
from typing import Annotated, TypedDict, List, Dict, Any
from pydantic import BaseModel

# Phân phối Beta cho Bayesian Updates
class BetaDistribution(BaseModel):
    alpha: float = 1.0  # Lượt thành công (Success prior)
    beta: float = 1.0   # Lượt thất bại (Failure prior)

# Trạng thái tổng của Đồ thị (Graph State)
class AgentState(TypedDict):
    task: str
    available_actions: List[str]
    action_priors: Dict[str, BetaDistribution] # Niềm tin cấy từ RAG
    chosen_action: str
    generated_code: str
    test_results: Dict[str, Any]
    iteration: int
    # Reducer: Log lịch sử cộng dồn (append-only)
    history: Annotated[List[str], operator.add] 

```

### Module 2: Action-Oriented RAG (Belief Seeder)

```python
class EpisodicMemoryRAG:
    def __init__(self, vector_client):
        self.db = vector_client

    def seed_beliefs(self, task: str, actions: List[str]) -> Dict[str, BetaDistribution]:
        """
        Gieo mầm niềm tin: Trích xuất kinh nghiệm quá khứ biến thành phân phối xác suất.
        """
        past_experiences = self.db.similarity_search(task, top_k=10)
        
        # Mặc định: Phân phối Uniform (chưa biết gì)
        priors = {action: BetaDistribution(alpha=1.0, beta=1.0) for action in actions}
        
        for exp in past_experiences:
            action_used = exp.metadata["action_taken"]
            if action_used in priors:
                # Cộng dồn kinh nghiệm quá khứ vào Priors
                priors[action_used].alpha += exp.metadata.get("success_weight", 0)
                priors[action_used].beta += exp.metadata.get("fail_weight", 0)
                
        return priors

    def store_experience(self, task: str, action: str, reward: float):
        """Upsert kinh nghiệm mới vào Vector DB sau khi hoàn thành Task"""
        pass

```

### Module 3: Decision Engine (Bayesian Multi-Armed Bandits)

```python
import numpy as np

class CognitiveDecisionEngine:
    def thompson_sampling(self, priors: Dict[str, BetaDistribution]) -> str:
        """
        Thuật toán MAB: Rút mẫu ngẫu nhiên từ phân phối Beta.
        Cân bằng hoàn hảo giữa Exploration và Exploitation.
        """
        sampled_theta = {}
        for action, dist in priors.items():
            sampled_theta[action] = np.random.beta(dist.alpha, dist.beta)
        
        # Chọn hành động có giá trị xác suất kỳ vọng cao nhất lượt này
        return max(sampled_theta, key=sampled_theta.get)

    def compute_reward(self, test_metrics: Dict[str, Any]) -> float:
        """
        Reward Function: Ánh xạ kết quả test thành vô hướng [0.0, 1.0].
        """
        if not test_metrics.get("compiles", False): 
            return 0.0 # Lỗi cú pháp
            
        reward = 0.0
        if test_metrics.get("tests_passed"): reward += 0.6
        
        # Thưởng/Phạt dựa trên độ phức tạp và hiệu năng
        complexity = test_metrics.get("cyclomatic_complexity", 10)
        reward += max(0, 0.2 - (complexity * 0.01)) 
        
        exec_time = test_metrics.get("execution_ms", 1000)
        time_penalty = 0.2 * np.exp(-exec_time / 500.0)
        reward += time_penalty
        
        return np.clip(reward, 0.0, 1.0)

    def bayesian_update(self, dist: BetaDistribution, reward: float) -> BetaDistribution:
        """Cập nhật phân phối Posterior dựa trên bằng chứng (Reward)"""
        dist.alpha += reward
        dist.beta += (1.0 - reward)
        return dist

```

### Module 4: LangGraph Orchestrator (State, Postgres, Interrupts)

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import interrupt, Command
from psycopg_pool import ConnectionPool

# --- KHỞI TẠO NODES ---

def node_seed_memory(state: AgentState):
    rag = EpisodicMemoryRAG(vector_client)
    priors = rag.seed_beliefs(state["task"], state["available_actions"])
    return {"action_priors": priors, "iteration": 0, "history": ["[Memory] Seeded Bayesian priors."]}

def node_decide(state: AgentState):
    engine = CognitiveDecisionEngine()
    chosen = engine.thompson_sampling(state["action_priors"])
    return {"chosen_action": chosen, "history": [f"[Decision] Selected strategy via MAB: {chosen}."]}

def node_execute(state: AgentState):
    # 1. DYNAMIC INTERRUPT: Tính năng bảo mật (Human-in-the-loop)
    if state["chosen_action"] in ["drop_database", "force_git_push", "modify_auth"]:
        # Đồ thị sẽ SUSPEND tại đây. Trạng thái RAM xả xuống Postgres.
        human_decision = interrupt({
            "warning": "Phân tích thấy mã nguy hiểm cần quyền.",
            "action": state["chosen_action"]
        })
        # AI sẽ dừng hoạt động cho đến khi bên ngoài gọi graph.invoke(Command(resume="APPROVE"))
        if human_decision != "APPROVE":
            return {"history": ["[Interrupt] Execution aborted by Human."]}

    # 2. LLM sinh code (Dựa trên Action đã chọn)
    prompt = f"Task: {state['task']}\nStrategy to apply: {state['chosen_action']}"
    code = llm_generate(prompt) 
    return {"generated_code": code}

def node_evaluate_and_learn(state: AgentState):
    # 1. Chạy Sandbox lấy Metrics
    metrics = sandbox_run(state["generated_code"])
    
    # 2. Tính Reward & Bayesian Update
    engine = CognitiveDecisionEngine()
    reward = engine.compute_reward(metrics)
    
    current_prior = state["action_priors"][state["chosen_action"]]
    updated_prior = engine.bayesian_update(current_prior, reward)
    
    # Trả về State mới để ghi đè (update)
    new_priors = state["action_priors"].copy()
    new_priors[state["chosen_action"]] = updated_prior
    
    return {
        "test_results": metrics, 
        "action_priors": new_priors,
        "iteration": state["iteration"] + 1,
        "history": [f"[Evaluate] Reward: {reward:.2f}"]
    }

# --- ĐIỀU HƯỚNG CÓ ĐIỀU KIỆN ---
def route_next_step(state: AgentState):
    if state["test_results"].get("tests_passed"):
        return END # Thành công
    if state["iteration"] >= 7:
        return END # Dừng vòng lặp vô hạn
    return "decide" # Trở lại Thompson Sampling để chọn chiến lược khác

# --- ORCHESTRATION BUILDER VỚI POSTGRES CHECKPOINTER ---
def build_agent_os(db_uri: str):
    workflow = StateGraph(AgentState)
    
    workflow.add_node("seed", node_seed_memory)
    workflow.add_node("decide", node_decide)
    workflow.add_node("execute", node_execute)
    workflow.add_node("evaluate", node_evaluate_and_learn)
    
    workflow.add_edge(START, "seed")
    workflow.add_edge("seed", "decide")
    workflow.add_edge("decide", "execute")
    workflow.add_edge("execute", "evaluate")
    workflow.add_conditional_edges("evaluate", route_next_step)
    
    # Thiết lập Thread-level Persistence chuẩn Enterprise
    pool = ConnectionPool(conninfo=db_uri)
    checkpointer = PostgresSaver(pool)
    checkpointer.setup()
    
    # Biên dịch đồ thị
    return workflow.compile(checkpointer=checkpointer)

```

## Tóm tắt Lợi ích Đột phá của Kiến trúc này:

1. **Trí thông minh Thích nghi (Adaptive Intelligence):** Không cần prompt engineer cồng kềnh kiểu *"Nếu gặp lỗi A thì làm B"*. Nếu AI chọn sai, hàm Reward chấm điểm thấp -> $\beta$ tăng -> Xác suất Thompson Sampling giảm -> Ở vòng lặp tiếp theo, hệ thống tự động bẻ lái sang chiến lược khác.
2. **Khả năng chịu lỗi (Resilience):** Nhờ `PostgresSaver`, Agent có thể xử lý các Task mất đến nhiều ngày. Nếu server sập giữa chừng, lần sau bật lại Agent sẽ nối tiếp đúng node đang chạy dựa trên `thread_id`.
3. **An toàn Production:** RAG gieo mầm định kiến (ví dụ: *"Repo này cấm dùng Pandas"*) từ đầu để tránh lỗi kiến trúc. Đồng thời `interrupt()` đảm bảo AI không bao giờ vượt quyền để thực thi các lệnh phá hoại hệ thống.