# Hive Builder Platform: Core Architecture & Specification

## 🚀 Overview
The Hive Builder Platform is a high-performance, cost-optimized wrapper around the **Hive Agent Framework**. It provides a scalable client-server architecture designed to build, deploy, and manage outcome-driven AI agents. 

The core mission of this platform is two-fold:
1. **Crash-Resistant Execution:** Provide a stable, asynchronous environment for complex, multi-step agent reasoning loops.
2. **Aggressive Cost Optimization:** Slash LLM API costs through semantic caching, dynamic model routing, and eventual fine-tuning via reinforcement learning.

---

##  The 5-Layer Conceptual Architecture

The backend is strictly decoupled into five specific layers to prevent context bloat and manage latency.

### Layer 1: The Versioned Schema Registry (Storage)
* **Role:** The platform's memory and rulebook.
* **Tech:** PostgreSQL (v15+).
* **Function:** Stores `SKILL.md` configurations, system prompts, tool schemas, and agent definitions as JSONB. Implements immutable versioning (e.g., `data-processor-v1`, `v2`) so active agents do not break mid-task.

### Layer 2: The "Queen" Adapter (Compiler)
* **Role:** Translates human intent into machine-executable blueprints.
* **Tech:** FastAPI (Python 3.12), Pydantic v2.
* **Function:** Fetches rules from Layer 1, compiles context, and leverages Hive's native "Queen Bee" to dynamically generate Directed Acyclic Graphs (DAGs) for execution. Enforces strict schema validation to prevent malformed LLM outputs.

### Layer 3: Optimization Middleware (Cache Engine)
* **Role:** The cost-saving interceptor.
* **Tech:** Redis (v7+) / pgvector.
* **Function:** Performs Semantic Hashing. Generates a composite cache key based on **[Semantic Intent + Data Hash + Skill Version]**. If a match >95% is found, it intercepts the request and serves the cached response instantly, skipping the LLM API call entirely.

### Layer 4: Model Routing Engine (Traffic Cop)
* **Role:** Dynamic intelligence distribution.
* **Tech:** Custom Python Middleware.
* **Function:** Evaluates the compiled JSON prompt for complexity.
  * **Tier 1 (Heavy Reasoning):** Routes to frontier models (e.g., GPT-4o, Claude 3.5 Sonnet).
  * **Tier 2 (Simple Tasks/Extraction):** Routes to fast, cheap models (e.g., Llama 3, Haiku, or Groq-hosted open-source models).

### Layer 5: Deployment & Telemetry Bridge (Execution & Evolution)
* **Role:** Asynchronous task execution and data harvesting.
* **Tech:** Celery, Redis (Broker), ClickHouse, WebSockets.
* **Function:** Drops tasks into an async queue to free the UI. Hive takes over inside a Celery worker, managing state and tool execution. Emits real-time agent "thoughts" back to the client via WebSockets. Asynchronously logs all traces (prompts, completions, latency, costs) to ClickHouse for future RLHF training (e.g., OpenPipe ART).

---

##  Architectural Execution Flow

1. **User Request:** Client (Next.js) sends a goal and data payload to the API Gateway.
2. **Compilation:** Layer 2 (Adapter) fetches the `SKILL.md` from PostgreSQL and compiles a strict JSON payload.
3. **Cache Check:** Layer 3 (Middleware) hashes the payload. On hit, return data. On miss, proceed.
4. **Routing:** Layer 4 (Router) tags the payload with the target model tier and drops it into the Celery Queue (Redis).
5. **Async Handoff:** FastAPI returns a `202 Accepted` and a Task ID to the UI.
6. **Execution (Hive):** A Celery worker consumes the task. The Hive framework takes over, running the node graph, calling tools, and managing conversational state.
7. **Streaming:** Hive streams intermediate progress back to Next.js via WebSockets.
8. **Telemetry:** The final output and exact execution trace are saved to ClickHouse.

---

##  Security & Schema Standards (Mandatory)

To prevent cascading failures and prompt injection, this platform adheres to strict modern LLM security protocols:

* **Token-Level Constrained Generation:** Do not rely on prompt-based "JSON Mode". All structured data generation must use **Pydantic v2 schemas** coupled with the LLM API's Native Structured Outputs (e.g., OpenAI `response_format` with `strict: true`).
* **Prompt Injection Defense:** * Treat all user input as untrusted.
  * Implement **Spotlighting**: Wrap untrusted data in unpredictable XML tags (e.g., `<ticket_data_8x9a>`) before compiling.
  * Use **Instruction Hierarchy**: Ensure critical agent system prompts are isolated in the `System`/`Developer` role, and user data remains strictly in the `User` role.

---

##  Technology Stack

**Frontend:**
* Next.js 15 (React 19, App Router)
* TypeScript
* Tailwind CSS
* React Flow (for visual graph rendering)

**Backend:**
* Python 3.12
* FastAPI (Asynchronous API Gateway)
* Pydantic v2 (Strict Schema Enforcement)
* Celery (Background Task Worker)
* Hive Agent Framework (Runtime & Orchestration)

**Infrastructure (Dockerized):**
* PostgreSQL 15 (Primary Database)
* Redis 7 (Caching & Message Broker)
* ClickHouse (High-Volume Telemetry & Traces)

**AI Integrations:**
* Primary LLM Interface: `openai` Python package (configured with custom `base_url` to support Groq for high-speed LPU inference and OpenAI for heavy reasoning).

---

##  Development Phasing

* **Phase 0: Scaffolding.** Monorepo setup, Docker networking, strict CORS, and database connectivity.
* **Phase 1: Dumb Pipeline.** Synchronous LLM execution to prove Layer 1 (DB) to Layer 2 (LLM) handoff.
* **Phase 2: Asynchronous Heartbeat.** Implementing Celery, Redis Queues, and WebSockets for long-running Hive tasks.
* **Phase 3: Intelligence & Routing.** Adding Semantic Caching (Layer 3) and the Model Router (Layer 4).
* **Phase 4: Telemetry.** ClickHouse ingestion for execution traces to fuel v2 model fine-tuning.

---

##  Instructions for AI Coding Agents

If you are an AI assistant reading this repository context:
1. **Never write synchronous LLM calls in the main FastAPI thread** (except in Phase 1 test endpoints). All complex agent executions must be routed through Celery.
2. **Prioritize Typing:** Always use strict Python type hints and Pydantic models. Ensure inputs from Next.js match the expected Pydantic schema exactly.
3. **Assume Network Fragility:** Implement exponential backoff for all LLM API calls within the background workers.
4. **Follow Progressive Disclosure:** Keep system prompts modular. Do not dump the entire `SKILL.md` registry into a single context window; only load the node-specific context required for the immediate execution step.