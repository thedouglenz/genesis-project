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

### Housekeeping

- Removed project plan and `.env` from git tracking; added both to `.gitignore`
