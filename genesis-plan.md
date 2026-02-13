# Genesis Computing Take-Home: Project Plan

## Overview

Build a natural language data agent — a web app where users ask questions about a SaaS dataset in plain English and receive structured answers with optional visualizations. The solution should demonstrate agentic AI architecture, clean engineering, and production-readiness.

---

## Strategic Context

Genesis Computing builds autonomous AI data agents for enterprise data workflows. Their interviewers evaluate candidates on:

- **Agent architecture literacy** — understanding tool-call loops, not single-shot LLM calls
- **Scalability thinking** — dynamic schema discovery, not hardcoded prompts per table
- **Frontend data management** — modern patterns like TanStack Query
- **Code quality and clean abstractions** — OOP, structured outputs, separation of concerns
- **Technical decision-making** — ability to articulate trade-offs

This plan is designed to demonstrate all of the above.

---

## Architecture

### High-Level Flow

```
User (React) → FastAPI Backend → Multi-Step Pipeline → LLM (LiteLLM Proxy) → Tools → Response
```

### Two-Database Design

| Database | Purpose | Connection |
|----------|---------|------------|
| `genesis_app` | Solution state: conversations, messages, pipeline runs/steps | Read-write user |
| `genesis_target` | Client data: the SaaS CSV loaded into Postgres | **Read-only user** |

Both hosted on **Neon** (same project, two databases). This separation demonstrates enterprise thinking — the target database represents a customer's data store that our agent connects to but never owns.

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + TypeScript, TanStack Query, Recharts, Tailwind CSS |
| Backend | Python, FastAPI, SQLAlchemy, Pydantic |
| LLM | LiteLLM Proxy (provided) |
| Database | PostgreSQL (Neon) |
| Deployment | Vercel (frontend), Railway (backend) |

---

## Backend Architecture (Python / FastAPI)

### OOP Class Structure

#### Tool Definitions

Four tools the LLM can invoke during exploration:

```
class Tool (abstract):
    name: str
    description: str
    parameters: dict (JSON schema)
    execute(params) → ToolResult

class ListTablesTool(Tool):
    """Returns all available tables in the target database."""
    Output: { tables: ["companies", ...] }

class ShowSchemaTool(Tool):
    """Returns column names, types, and constraints for a table."""
    Input: { table: str }
    Output: { table: str, columns: [{ name, type, nullable }] }

class SampleDataTool(Tool):
    """Returns sample rows to help the LLM understand data formats and value ranges."""
    Input: { table: str, limit: int = 5 }
    Output: { table: str, rows: [...], columns: [...] }

class QueryTool(Tool):
    """Executes a read-only SQL query against the target database."""
    Input: { sql: str }
    Output: { columns: [...], rows: [...], row_count: int }
    Safety: SQL injection validation, read-only user, SELECT-only enforcement
```

#### Pipeline Steps

Each step is a class with defined inputs, outputs, a system prompt, and an execute method.

```
class PipelineStep (abstract):
    name: str
    input_schema: Pydantic model
    output_schema: Pydantic model
    system_prompt: str (dynamically generated)
    max_retries: int = 10
    execute(input) → output
    validate_output(raw) → parsed output or retry
```

**Step 1 — Plan**

- Input: user question, conversation history, (optional) cached schema context from prior turns
- System prompt: Reason about the question. Determine what data exploration is needed. Identify the expected answer format.
- Output schema:
  ```
  PlanOutput {
    reasoning: str
    query_strategy: str
    expected_answer_type: "scalar" | "dataset" | "chart"
    suggested_chart_type?: "bar" | "line" | "pie" | "scatter"
    tables_to_explore: list[str]
  }
  ```

**Step 2 — Explore**

- Input: PlanOutput + available tools
- System prompt: Execute the plan by calling tools. You may call tools multiple times. Gather all data needed to answer the question.
- This is the **agentic tool-call loop** step. The LLM calls tools iteratively until it determines it has enough data.
- Output schema:
  ```
  ExploreOutput {
    queries_executed: list[{ sql: str, result_summary: str }]
    raw_data: any (the final query result to be used for the answer)
    exploration_notes: str
    schema_context: dict (cached for future turns in the conversation)
  }
  ```

**Step 3 — Answer**

- Input: PlanOutput + ExploreOutput + original question
- System prompt: Format the explored data into a clear, well-presented answer. Choose the appropriate format based on the plan.
- Output schema:
  ```
  AnswerOutput {
    text_answer: str
    table_data?: { columns: list[str], rows: list[list[any]] }
    chart_data?: {
      type: "bar" | "line" | "pie" | "scatter"
      title: str
      x_axis: str
      y_axis: str
      data: list[{ label: str, value: float }]
    }
  }
  ```

#### Pipeline Orchestrator

```
class Pipeline:
    steps: list[PipelineStep]
    conversation_id: str
    message_id: str

    async run(user_question) → AnswerOutput:
        - For each step:
            - Load input (from prior step output or initial context)
            - Execute step with retry logic
            - Persist step input/output to pipeline_steps table
            - Stream progress via SSE
            - If step fails after max retries, persist error and abort
        - Return final AnswerOutput
```

### Structured Output & Retry Logic

Every LLM call enforces structured output:

1. System prompt specifies the exact JSON schema expected
2. LLM responds
3. Parse response against Pydantic model
4. If validation fails → re-prompt with the validation error appended, asking the LLM to fix its output
5. Retry up to `max_retries` (default 10)
6. If all retries exhausted → persist failure, return graceful error to user

### SQL Safety

- Target database connection uses a **read-only Postgres user**
- SQL parsing layer rejects anything that isn't SELECT (blocks INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE)
- Parameterized query construction where possible
- SQL injection pattern detection
- Query result size limits to prevent memory issues

### Schema Caching Optimization

After the first question in a conversation, the LLM has already discovered schemas via `list_tables`, `show_schema`, and `sample_data`. Store this in the `ExploreOutput.schema_context` field and include it in subsequent turns' context. This avoids redundant tool calls and reduces latency — and demonstrates awareness of token efficiency.

In the follow-up interview, this enables the talking point: *"In production with hundreds of tables, you wouldn't dump all schemas into context — you'd use RAG to retrieve relevant ones based on the user's question."*

---

## Database Schema (App Database)

```sql
-- Conversations
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Messages within conversations
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    role VARCHAR(20) NOT NULL, -- 'user' | 'assistant'
    content TEXT, -- the displayed message text
    table_data JSONB, -- optional table result
    chart_data JSONB, -- optional chart result
    created_at TIMESTAMP DEFAULT NOW()
);

-- Pipeline execution runs (one per user message)
CREATE TABLE pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES messages(id),
    status VARCHAR(20) DEFAULT 'running', -- running | completed | failed
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Individual step executions within a pipeline run
CREATE TABLE pipeline_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID REFERENCES pipeline_runs(id),
    step_name VARCHAR(50) NOT NULL, -- 'plan' | 'explore' | 'answer'
    step_order INT NOT NULL,
    input_json JSONB,
    output_json JSONB,
    status VARCHAR(20) DEFAULT 'pending', -- pending | running | completed | failed
    attempts INT DEFAULT 0,
    error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

---

## API Endpoints

```
POST   /api/conversations                    → Create new conversation
GET    /api/conversations                    → List conversations
GET    /api/conversations/:id                → Get conversation with messages
DELETE /api/conversations/:id                → Delete conversation

POST   /api/conversations/:id/messages       → Send a user message (triggers pipeline)
GET    /api/conversations/:id/stream         → SSE endpoint for pipeline progress

GET    /api/conversations/:id/pipeline-runs  → Get pipeline runs for debugging/retry
POST   /api/pipeline-runs/:id/retry          → Retry a failed pipeline run

POST   /api/auth/login                       → Simple auth (single username/password)
```

---

## Frontend Architecture (React + TypeScript)

### Key Components

```
App
├── LoginPage (simple auth gate)
├── ChatLayout
│   ├── Sidebar
│   │   ├── NewConversationButton
│   │   └── ConversationList (clickable, shows titles)
│   └── ChatPane
│       ├── MessageList
│       │   ├── UserMessage
│       │   └── AssistantMessage
│       │       ├── TextAnswer
│       │       ├── TableResult (rendered HTML table)
│       │       ├── ChartResult (Recharts component)
│       │       └── ThinkingCollapsible (expandable step progress)
│       └── MessageInput
```

### TanStack Query Usage

- `useQuery(['conversations'])` — fetch conversation list
- `useQuery(['conversation', id])` — fetch conversation messages
- `useMutation` — send message, create conversation
- Invalidate `['conversation', id]` after message mutation completes

### SSE Integration

When a message is sent:
1. `useMutation` POSTs the user message
2. Open an EventSource to `/api/conversations/:id/stream`
3. Render incoming step events in a collapsible "Thinking" area:
   - `{ step: "plan", status: "running" }`
   - `{ step: "plan", status: "completed", summary: "..." }`
   - `{ step: "explore", status: "running", tool_call: "list_tables" }`
   - `{ step: "explore", status: "running", tool_call: "query", sql: "SELECT ..." }`
   - `{ step: "answer", status: "completed" }`
4. On final event, invalidate the conversation query to fetch the persisted assistant message with full answer/table/chart data

### Chart Rendering

Use **Recharts** for chart rendering. The `chart_data` from the LLM response maps directly to Recharts components:

- `type: "bar"` → `<BarChart>`
- `type: "line"` → `<LineChart>`
- `type: "pie"` → `<PieChart>`
- `type: "scatter"` → `<ScatterChart>`

The chart schema is simple and deterministic — no LLM-generated code execution needed for visualizations.

---

## Authentication

Simple hardcoded auth — not the focus of this project:

- Single username/password combination stored as environment variables
- Login returns a session token (JWT or simple token)
- Token required on all API requests
- No registration flow

---

## Deployment

| Component | Platform | Why |
|-----------|----------|-----|
| Frontend | Vercel | Zero-config React deployment, fast |
| Backend | Railway | Easy Python/FastAPI deployment, supports env vars |
| Database | Neon | Serverless Postgres, free tier, supports multiple databases |

### Environment Variables

```
# Backend
DATABASE_APP_URL=postgres://...@neon/genesis_app
DATABASE_TARGET_URL=postgres://...readonly@neon/genesis_target
LITELLM_PROXY_URL=https://litellm-production-f079.up.railway.app/
LITELLM_API_KEY=...
AUTH_USERNAME=...
AUTH_PASSWORD=...
JWT_SECRET=...

# Frontend
VITE_API_URL=https://...railway.app
```

---

## Commit Strategy

Maintain clean, logical commit history showing iteration:

1. `init: project scaffold, FastAPI + React setup`
2. `db: Neon setup, SQLAlchemy models, migrations`
3. `tools: implement data tools (list_tables, show_schema, sample_data, query)`
4. `pipeline: step classes with structured output and retry logic`
5. `api: conversation and message endpoints`
6. `sse: streaming pipeline progress`
7. `frontend: chat UI with TanStack Query`
8. `frontend: chart rendering with Recharts`
9. `security: read-only user, SQL validation, auth`
10. `deploy: Railway + Vercel + Neon configuration`
11. `polish: error handling, edge cases, README`

---

## README Outline (max 500 words)

1. **Architecture overview** — multi-step agentic pipeline, two-database design, why
2. **AI tools used** — Claude for architecture decisions, Claude Code / Cursor for implementation, how they accelerated development
3. **Key design decisions** — structured outputs with retry, tool-call loop for exploration, schema caching, chart data vs code execution trade-off
4. **Challenges** — structured output reliability, SSE coordination, balancing agentic flexibility with deterministic schemas
5. **What I'd improve** — RAG for schema discovery at scale, multi-agent orchestration, support for joins across data sources, caching layer

---

## Loom Video Outline (max 5 minutes)

1. **Demo the app** (2 min) — ask 3-4 questions showing different answer types (scalar, table, chart), show conversation persistence, show the thinking/progress collapsible
2. **Architecture walkthrough** (2 min) — the three-step pipeline, tool-call loop, structured outputs, two-database design
3. **Design decisions** (1 min) — why this architecture scales, what you'd do differently in production (RAG, multi-agent), connection to enterprise data workflows

---

## Interview Preparation — Anticipated Follow-Up Questions

| Question | Your Answer |
|----------|-------------|
| "How would you scale to hundreds of tables?" | "Replace schema caching with RAG — embed table metadata as vectors, retrieve relevant schemas based on the user's question. I've built this at Firebrand." |
| "How does the agent decide what to do?" | "Walk through the tool-call loop in Step 2 — LLM sees available tools, decides which to call, gets results, decides next action." |
| "What if the SQL is wrong?" | "Retry logic — the error goes back to the LLM with context, it corrects and tries again. Plus read-only user and SQL validation as guardrails." |
| "Why structured output instead of freeform?" | "Each pipeline step has guaranteed I/O schemas. This makes steps composable, testable, and persistent. Failures are recoverable because step state is saved." |
| "Why two databases?" | "Separation of concerns — the target data is a customer's database we connect to, not something we own. In production this would be Snowflake or Databricks." |
| "What would you add with more time?" | "RAG for schema discovery, multi-data-source support, conversation branching, admin dashboard for pipeline observability." |
