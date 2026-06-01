# FRONTEND & BACKEND INTEGRATION PROMPT (UI WIRING & MIGRATION)

**Role:** Act as an Expert Full-Stack Engineer (Next.js + FastAPI).
**Task:** You previously built a beautiful "Enterprise Cyber-Dark" Next.js frontend in the `frontend/` directory. Your task now is twofold: 
1) **Migrate** valuable settings logic from legacy HTML templates into the new React app.
2) **Wire up** the React frontend to our live FastAPI backend, turning it into a fully functional, real-time control center.

## 1. MIGRATION: LEGACY SETTINGS LOGIC
Crucial configuration logic (Model Settings, 3rd-Party Integrations) currently exists in the legacy HTML/JS templates located in `public/` and `data/templates/` (e.g., `settings-models.html`, `settings-integrations.html`).
*   **Extract & Migrate:** Before deleting any legacy files, you MUST read these files to understand the existing settings logic and API payloads.
*   **React Implementation:** Re-implement this settings functionality natively within the Next.js application (e.g., as new tabs within `frontend/src/app/page.tsx` or as new routes like `frontend/src/app/settings/page.tsx`). Ensure the new React components make the correct API calls to the backend to save/load these configurations, preserving the "Cyber-Dark" Tailwind UI style.

## 2. BACKEND PREPARATION (FastAPI Endpoint & WebSocket)
Ensure the backend is ready to accept frontend connections.
*   **Trigger API:** Create or verify the `POST /api/test/trigger-autonomous/{campaign_id}` endpoint in FastAPI. This endpoint must call `trigger_autonomous_generation` from `core.bandit_orchestrator` and return the final state as JSON.
*   **Real-time Telemetry (WebSocket/SSE):** Add a WebSocket endpoint (e.g., `ws://localhost:8000/api/ws/telemetry`) to FastAPI. Hook into Python's `logging` module. Broadcast execution logs over this connection so the frontend receives them in real-time.
*   **CORS:** Ensure `CORSMiddleware` is configured in `app.py` to accept requests from the Next.js development server (`http://localhost:3000`).

## 3. FRONTEND INTEGRATION: GLOBAL ACTION TRIGGER (`frontend/src/app/page.tsx`)
Wire up the `[ ⚡ Execute AI Agent ]` button.
*   **API Call:** Replace the `setTimeout` mock logic with `fetch` or `axios` to send a `POST` request to `http://localhost:8000/api/test/trigger-autonomous/{campaign_id}`.
*   **UI Feedback:** Maintain the `isLoading=true` spinner. On success, trigger a success Toast and set `isLoading=false`. On error, trigger a red error Toast.

## 4. FRONTEND INTEGRATION: REAL-TIME TELEMETRY (Log Monitoring)
Wire up the "Live Node & Telemetry Logs" component in `frontend/src/app/page.tsx`.
*   **WebSocket Client:** Create a React `useEffect` hook to connect to `ws://localhost:8000/api/ws/telemetry`.
*   **State Management:** Store incoming logs in `const [logs, setLogs] = useState([])`. Replace the hardcoded log array with this state.
*   **Rendering:** Map over the `logs` array. Auto-scroll to the bottom as new messages arrive. Keep the existing Tailwind color-coding logic (e.g., `INFO`, `SUCCESS`, `WARN`).

## 5. FRONTEND INTEGRATION: DASHBOARD METRICS & RESULTS
After the `trigger-autonomous` API call returns successfully, update the Dashboard UI.
*   Dynamically render the `generated_variants` and `sandbox_feedbacks` returned by the API payload into the UI, replacing placeholder components.

# EXECUTION INSTRUCTIONS
1. **Migration First:** Begin by migrating the Settings and Integrations logic from `public/` and `data/templates/` into the `frontend/` React app.
2. **Target Directory:** Once migrated, ONLY modify the Next.js application inside `frontend/` and the backend Python files.
3. **Legacy Cleanup:** After successfully porting the settings logic, you may safely delete the obsolete HTML/JS files in `public/` and `data/templates/`.
4. **Preserve Design:** Keep all Tailwind classes, Recharts, and icons intact.

Please acknowledge and begin by executing Phase 1 (Migration), followed by Backend WebSocket creation, and finally Frontend Wiring.