# Natural Language Query Assistant

This is my submission for the Genesis Computing Take Home Assignment. It is a full stack application testable at [https://genesis-project-production.up.railway.app/](https://genesis-project-production.up.railway.app/) that demonstrates the ability to start and carry out conversations about a dataset. I've loaded the provided sasmple data into a PostgreSQL database to simulate a customer's SQL database. I built my solution to persist it's own data into another database (just placed on the same server) allowing my solution to store conversations, messages, pipeline runs/steps. The customer database has a RO user to the client data.

### Which AI tools used and how

- Claude: plan/capture my upfront requirements. _How:_ I already had an ongoing conversation about my fitness for this role and I synthesized the take home assignment doc into that same chat and that lead into a discussion of what I would like to do in my solution.
- Claude Code: Full implementation. _How:_ I presented a plan. With some task decomposition from the plan doc, we (myself and one team lead Claude agent) were able to do parallel work with multiple Claude Code sessions to iterate while keeping the commit history clean and easy to follow.

### Interesting challenges encountered

How do I want to optimize various things and what is the time tradeoff. Example:

- In a multi-step pipeline, you can skip steps. i.e., don't need an "explore" step if the user just follows up with "Thanks", or "make that a bar chart instead".
- SSE with auth headers: The browser's native EventSource API can't send Authorization headers. I used the Fetch API with ReadableStream to get SSE behavior while still passing the JWT token.

### Design decisions

- Three-step pipeline (Plan, Explore, Answer): The explore step is an agentic tool-call loop. The LLM iteratively calls tools (list_tables, show_schema, sample_data, query) until it has enough data to answer. The plan and answer steps use strict Pydantic schemas with retry logic: if the LLM output fails validation, the error is fed back for self-correction.
-  The target database connection uses a read-only Postgres role (no INSERT/UPDATE/DELETE permissions). On top of that, a Python validation layer rejects non-SELECT queries, blocks dangerous keywords, prevents multiple statements, and checks for SQL injection patterns. Belt and suspenders.
- **Pipeline state persistence:** Every pipeline run and each of its steps (plan, explore, answer) are persisted with their full input/output JSON, status, and error details. This gives observability into what the LLM did at each stage and makes debugging straightforward.

For a more in-depth look at the process, see [journal.md](journal.md).

### What I'd improve with more time

- Code execution sandbox: Instead of relying on the LLM to format query results into chart data, I'd have it generate reusable scripts (e.g., TypeScript) that execute SQL and transform the raw data directly. The LLM is a lossy middleman for large result sets — generating and storing executable code would be more reliable and reusable.
- RAG for schema discovery. Currently, schema discovered during exploration is cached and included in the system prompt for subsequent turns. At scale with hundreds of tables, I'd embed table/column metadata as vectors and retrieve only the relevant schemas based on the user's question.

