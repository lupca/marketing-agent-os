# ROLE & CONTEXT
You are an Elite Enterprise AI Systems Architect and Senior Python/LangGraph Backend Engineer.
Your task is to execute a major architectural refactor of the "Marketing Agent OS" project. We are transitioning from a Human-in-the-loop chatbot system to a **Stateless, Autonomous Creative Intelligence Engine** powered by Multi-Armed Bandit logic, OLAP databases, and Event-Driven architecture.

# REFERENCE DOCUMENTS
Before writing any code, you MUST thoroughly read and internalize the following Enterprise Design documents located in `/root/marketing/marketing-agent-os/docs/agentic ai/`:
1. `AUTONOMOUS_REFACTOR_PLAN.md` (Stateless Execution, Content Diversity Pivot)
2. `CMO_CTO_ALIGNMENT.md` (Reward calculation, HITL Insights, 15/85 Creative Diversity Output)
3. `SYSTEM_IMPACT_REPORT.md` (Deprecation of Chat/Negotiator/Triage, OLAP separation, Airflow/Cron orchestration)
4. `RAG_IMPACT_ANALYSIS.md` (SQL-based Cold Start, Preventing RAG Data Poisoning via `pending_insights`)

# STRICT ENTERPRISE ARCHITECTURE RULES (DO NOT VIOLATE)
* **NO ZOMBIE GRAPHS:** You are FORBIDDEN from using `interrupt_before=["waiting_for_metrics"]` or designing long-running graphs. LangGraph is strictly a **Stateless Execution Layer**. It receives inputs (Priors), generates content, and immediately `Terminates` to free RAM.
* **NO RAG POISONING:** AI-generated insights must NEVER be auto-embedded into RAG. They must be saved to a relational SQL table (`pending_insights`) for Human-In-The-Loop (HITL) approval.
* **NO RAG FOR COLD START:** Do not use Semantic RAG searches for determining budget or strategy priors. Use traditional SQL `AVG()` queries on historical campaign metrics.
* **NO BIDDING CONFLICTS:** Do not attempt to force Ad Networks to allocate specific budgets (e.g., 15% Explore). Instead, use the Bandit algorithm to control **Content Generation Output** (e.g., out of 10 variants, 8 use proven Exploit angles, 2 use wildcard Explore angles) and output them as Dynamic Creatives.

# IMPLEMENTATION ROADMAP (IN-PLACE REFACTORING)
Do not create `v1` or `v2` folders. Modify or delete the existing files directly.

## PHASE 1: CLEANUP & DEPRECATION (Direct Deletion)
1. Delete the Chainlit UI ecosystem: `app.py`, `chainlit.md`, `chainlit_schema.sql`, and the `.chainlit/` folder.
2. Delete conversational and human-dependent nodes: `graphs/business/negotiator.py`, `graphs/supervisor/chat.py`, `graphs/supervisor/triage.py`.
3. Scaffold a new `app.py` as a pure FastAPI backend to serve dashboard triggers.

## PHASE 2: DATABASE & OLAP INFRASTRUCTURE
Modify `db/schema.sql` (and create necessary migration scripts):
1. **OLAP Tables:** Create `campaign_analytics` (to store historical metrics) and `ai_insights_pending` (for HITL approval).
2. **Ad Mapper:** Update schema to map internal `Variant_ID` to external `Platform_Ad_ID`.

## PHASE 3: THE STATELESS GRAPH & BANDIT ENGINE
1. **Stateless `AgencyState`:** Update `graphs/supervisor/state.py`. Remove cumulative logic (`operator.add`) for metrics. The state should only hold data for a *single execution run* (e.g., `campaign_objective`, `current_priors`, `generated_variants`).
2. **Backend Orchestration (Python):** Create a service/module outside of LangGraph that:
   - Fetches historical metrics from OLAP.
   - Solves Cold-Start via SQL queries if no data exists.
   - Runs the Epsilon-Greedy / Thompson Sampling math to calculate `current_priors` (Beliefs).
   - Triggers the LangGraph execution, passing these priors in.
3. **Graph Nodes (in `graphs/`):**
   - `scoring_node`: Evaluates angles based on the Backend's Priors.
   - `action_selector_node`: Dictates the creative mix (80% Exploit / 20% Explore) for the Copywriter.
   - `guardian_sandbox_node`: Enforces Brand Safety. Rejects bad variants internally. Writes rejection reasons to RAG (`sandbox_feedback`).
   - `insight_generator_node`: Uses LLM to explain why priors shifted. Saves to `ai_insights_pending` in Postgres (NOT RAG).
   - `publisher_node`: Packages the final variants as Dynamic Creatives for the Ad Network. Ends the Graph.

## PHASE 4: RE-WIRING THE ROUTER
In `graphs/main_router.py`:
1. Strip out all manual approval interrupts.
2. Ensure the flow is completely automated and stateless: `START` -> `scoring` -> `selector` -> `creative_generation` -> `guardian_sandbox` -> `publisher` -> `END`.

# CODING STANDARDS
- Write clean, modular, PEP-8 compliant Python code.
- Avoid "Fat Nodes"; extract JSON parsing and prompt construction to utility functions.
- Assume PostgreSQL + pgvector are already running. Do not hallucinate database structures.

Acknowledge these instructions and execute Phase 1 and Phase 2 immediately.


## PHASE 5: DATA SEEDING & TESTING
2 Once the architecture is refactored, you MUST test the Cold-Start and Context Injection logic.
3 Locate and execute the SQL script at the following path to seed the PostgreSQL database with the "TOPVNSPORT"
   brand identity, customer personas, and products:
4
5 `Target file:` `/root/marketing/marketing-agent-os/docs/agentic ai/brand/seed_topvnsports.sql`
6
7 After seeding, verify that your stateless LangGraph correctly pulls this context from the database to generate
   dynamic creatives without hallucinatory fallback data.

RAG test: /root/marketing/marketing-agent-os/docs/agentic ai/MKT