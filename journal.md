# Development Journal

## 2025-02-12

### Project scaffold

Stood up the full project structure — backend (Python/FastAPI) and frontend (React/TypeScript/Vite).

**Backend** (`backend/`):
- Initialized with `uv` and Python 3.12
- FastAPI app with CORS, health endpoint, and router stubs for conversations, auth, and pipeline runs
- Two async SQLAlchemy engines — one read-write for app state, one read-only for the target dataset. This separation keeps the agent from ever mutating customer data.
- Four SQLAlchemy models: conversations, messages, pipeline_runs, pipeline_steps
- Pydantic schemas for API request/response and pipeline outputs (PlanOutput, ExploreOutput, AnswerOutput)
- Abstract Tool base class with four concrete tool stubs (list_tables, show_schema, sample_data, query)
- Abstract PipelineStep base class with three steps (plan, explore, answer) and an orchestrator
- LiteLLM client wrapper stub

**Frontend** (`frontend/`):
- Vite + React + TypeScript
- TanStack Query wired from the start — QueryClientProvider in main.tsx, hooks for conversations CRUD with proper query keys and cache invalidation
- Tailwind CSS via `@tailwindcss/vite` plugin
- Axios client with auth header interceptor
- Component tree: LoginPage, ChatLayout, Sidebar, ChatPane, MessageList, MessageInput, AssistantMessage (renders text, tables, and Recharts charts)
- TypeScript interfaces mirroring the backend Pydantic schemas

**Post-scaffold review** caught two issues, both fixed:
1. `ChartData.data` was typed as `list[dict]` — changed to `list[ChartDataPoint]` with `label: str` and `value: float` to enforce the contract between backend and frontend
2. Pipeline retry endpoint was nested under `/api/conversations/pipeline-runs/:id/retry` instead of the intended `/api/pipeline-runs/:id/retry` — moved to its own router

### Database setup

Created a read-only Postgres role (`company_ro`) on the Neon `company_data` database. Granted CONNECT, USAGE on public schema, and SELECT on all current and future tables. This is the role the agent's tools will use — it can read but never write to the target dataset.

### Target data loaded

Created a `companies` table in `company_data` and loaded 500 rows from `sample_data.csv`. Columns: company_name, industry_vertical, founding_year, arr_thousands, employee_count, churn_rate_percent, yoy_growth_rate_percent. Schema SQL lives in `db/seed_target.sql`. Verified the `company_ro` role can query it — SELECT works, no write access.

### App database setup

Created a read-write role (`genesis_app_rw`) on the `genesis_solution` database for app state. Created all four tables (conversations, messages, pipeline_runs, pipeline_steps) with proper foreign keys and cascading deletes. SQL lives in `db/setup_app_tables.sql`.

### Backend implementation

Implemented the full backend in three waves, working bottom-up through the dependency graph.

**Foundation layer:**
- JWT auth — login endpoint, token creation/validation, FastAPI dependency on all protected routes
- Conversation CRUD — create, list, get (with eager-loaded messages), delete
- All endpoints use async SQLAlchemy sessions against the app database

**Data tools + LLM client:**
- SQL safety module — rejects anything that isn't a SELECT, blocks dangerous keywords, prevents multi-statement injection
- Four tools implemented against the target database: list_tables (information_schema), show_schema, sample_data, query (with 1000-row cap)
- LiteLLM client wrapper with two modes: `chat()` for tool-calling conversations, `chat_json()` for structured output parsed into Pydantic models. Handles markdown code blocks in LLM responses.

**Pipeline:**
- Plan step — analyzes the user question, determines query strategy and expected answer format (scalar/dataset/chart). Includes conversation history and cached schema context for follow-up efficiency.
- Explore step — agentic tool-call loop (max 20 iterations). LLM decides which tools to call, executes them, appends results, and repeats until it has enough data. Produces an ExploreOutput with queries executed, raw data, and schema context for caching.
- Answer step — formats explored data into a structured AnswerOutput with text, optional table, and optional chart data based on the plan's expected answer type.
- Orchestrator — chains plan→explore→answer, creates PipelineRun/PipelineStep records in the database, persists input/output at each step. Retry logic built into the base class.
- SSE streaming — per-conversation event bus using asyncio.Queue. Orchestrator emits events at each step transition. send_message runs the pipeline as a background task so it returns immediately while events stream.
- Pipeline runs endpoints — list runs with steps for a conversation, retry failed runs.

**Testing:** 57 tests, all fully mocked (no real DB or network I/O), run in under 1 second.

### Frontend implementation

Implemented the frontend in three waves, mirroring the backend approach.

**Core chat flow:**
- SSE hook (`useSSE`) — uses `fetch` with ReadableStream instead of EventSource so we can send the Authorization header. Tracks step states, sets completion flag, invalidates the TanStack conversation query when the pipeline finishes so the real assistant message replaces the streaming placeholder.
- ThinkingCollapsible — shows live pipeline progress (Planning → Exploring data → Generating answer) with spinners and checkmarks. Auto-expands while streaming, collapses to "Thought for N steps" when done.
- Optimistic message display — user message appears immediately in the chat before the API returns. A placeholder assistant area shows ThinkingCollapsible while the pipeline runs. When SSE completes and TanStack refetches, the real response (text/table/chart) replaces the placeholder.

**Polish:**
- Conversation titles default to "New conversation" when no title is set
- Logout button in sidebar — clears token, resets auth state
- Loading spinner while conversation data loads
- Dismissible error banner when message send fails
- Delete conversations from sidebar with hover trash icon

TypeScript compiles clean with zero errors.

### End-to-end testing

Ran the full app (backend on :8000, frontend on :5174) and tested the complete flow. Found and fixed four issues:

1. **Tool schema validation** — `ListTablesTool.parameters` was an empty dict `{}`. Anthropic's API requires `{"type": "object", "properties": {}}` even for parameterless tools. The explore step's tool-call loop couldn't start without this.

2. **Decimal serialization** — Postgres numeric columns return Python `Decimal` objects. `json.dumps()` in the explore step's tool result serialization choked on them. Fixed with `default=str` fallback.

3. **Tool messages without tools definition** — After the explore loop finishes its tool calls, the summarization call (`chat_json`) was sending the full message history (containing tool_calls and tool role messages) without a `tools` parameter. Anthropic rejects this. Fixed by passing `tools=tool_defs` through to the summarization call.

4. **Duplicate user messages** — Two sources: (a) `useSendMessage.onSuccess` was invalidating the conversation query, causing TanStack to refetch the server-persisted user message while the optimistic one was still displayed. Removed the premature invalidation — the SSE hook already invalidates on completion. (b) TanStack's default `staleTime: 0` could still trigger refetches during re-renders. Added deduplication in MessageList to skip the optimistic message if the server messages already contain it.

5. **Conversation creation 422** — Frontend was sending `POST /api/conversations` with no body. FastAPI expects a JSON body for `CreateConversationRequest` even though all fields are optional. Fixed by sending `{}`.

**Verified working:**
- Login with admin/admin
- Create conversation (auto-selects)
- Scalar answer: "How many companies are in the dataset?" → "There are 500 companies"
- Chart answer: "Show me average ARR by industry as a bar chart" → text analysis + Recharts bar chart
- Table answer: "List the top 5 companies by ARR" → text + HTML table + bar chart
- Conversation history maintained across follow-up questions
- Delete conversation from sidebar
- Logout redirects to login page

### Feature: conversation naming

The plan step now generates a short conversation name on the first message (when there's no history). Added `conversation_name` to `PlanOutput` and the plan system prompt. The orchestrator updates the conversation title after the plan completes. The SSE hook invalidates the sidebar conversation list so the new name appears without a page refresh.

### Feature: persistent pipeline thinking

Pipeline step data is now persisted on the assistant message as `pipeline_data` (JSONB column). After the pipeline completes, `_run_pipeline` builds a summary from the PipelineStep records — plan reasoning/strategy, explore queries/notes, answer status — and saves it on the message. The ThinkingCollapsible component now has two modes: streaming (live spinners during pipeline execution) and persisted (collapsed "Analyzed in N steps" with expandable step details loaded from the message). Migration in `db/migrations/001_add_pipeline_data.sql`.

### Fix: empty chat bubble race condition

After the explore step completed, there was a long pause with an empty assistant chat bubble before the answer appeared. Root cause: the orchestrator emitted `{"step": "done"}` before `_run_pipeline()` had written the answer content to the database. The frontend's SSE hook saw "done", invalidated the query, and TanStack refetched the message — but it still had null content. Fixed by moving the "done" event emission to `_run_pipeline()` after the content commit. Also added a guard in ChatPane to only clear optimistic state when the refetched data actually contains the assistant response.

### Housekeeping

- Removed project plan and `.env` from git tracking; added both to `.gitignore`
