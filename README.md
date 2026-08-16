# 🛡️ Zero-Trust Human-in-the-Loop (HitL) AI Agent Engine

> **A Production-Ready Prototype for Stateful, Scoped, and Extensible AI Workflow Automation.**  
> Built with **Python 3.12**, **FastAPI**, **Pydantic-AI**, **Ollama (Qwen 14B)**, and a lightweight **Tailwind CSS** client.

---

## 📌 Executive Summary

Modern enterprise AI platforms face a fundamental architectural challenge:
* **LLMs are non-deterministic:** They can hallucinate, suffer from prompt injections, execute actions out of order, or tamper with parameters.
* **Enterprise backends require determinism & auditability:** Mutating database records, deleting files, or broadcasting customer notifications must be strictly authorized and bound to exact parameters.

This project implements a **Zero-Trust Human-in-the-Loop (HitL) Architecture**. Rather than relying on fragile prompt rules (*"Please ask before deleting"*), this engine enforces security at the **Python runtime level** using **Scoped Action Tickets**, **Dependency Injection**, and a **FIFO Multi-Tool Execution Queue**.

---

## 🏗️ Architecture & Component Breakdown

The codebase is organized into four modular, decoupled components:

* `models.py`: Data contracts, Pydantic schemas, and Dependency definitions (`ActionTicket`, `WorkflowDeps`).
* `agent.py`: Self-registering Tool Catalog, Pydantic-AI agent configuration, and local Ollama LLM provider.
* `main.py`: FastAPI async server, Session State Store, Ticket Lifecycle Manager, and REST endpoints.
* `index.html`: Zero-build dark-mode console with live Action Authorization Cards, dynamic tool discovery, and Markdown parsing.

```text
                        ┌────────────────────────────────────────────────────────┐
                        │                   FastAPI (main.py)                    │
                        │                                                        │
[Client (index.html)] ──┼──► POST /api/workflow/chat                             │
   (UI / Chat / HitL)   │       │                                                │
                        │       ├──► 1. Rehydrate Session History (session_store)│
                        │       ├──► 2. Resolve & Consume Ticket (One-Time Use)  │
                        │       ├──► 3. Inject Dependency: WorkflowDeps(ticket)  │
                        │       └──► 4. Asynchronously Execute Agent (agent.py)  │
                        │               │                                        │
                        │               ├──► [Pydantic-AI / Ollama Qwen]         │
                        │               │       │                                │
                        │               │       ├── Safe Tool? ──────────────────┼──► [Execute & Log]
                        │               │       └── Sensitive Tool?              │
                        │               │               │                        │
                        │               │       [Python Scoped Verification]     │
                        │               │         ├── Valid Ticket & Exact Args? ┼──► [Execute & Audit Log]
                        │               │         └── Unauthorized / Mismatch? ──┼──► [HARD BLOCK & Issue Ticket]
                        │               │                                        │
                        │       ◄───────┴── 5. Save History & Enqueue Tickets    │
                        │                                                        │
                        │   ◄── 6. Return JSON (Response + Next Pending Ticket)  │
                        └────────────────────────────────────────────────────────┘
```

---

## 🔍 Deep Dive: Core Architectural Pillars

---

### 1. Scoped Action Tickets (Preventing Blanket Approval Attacks)

#### The Vulnerability in Basic HitL Systems:
A common anti-pattern is using a global boolean flag (`is_approval_click = True`). If an LLM hallucinates or gets manipulated, a global boolean gives it a blanket VIP pass to execute *any* tool (e.g. user thought they approved deleting `temp.txt`, but the LLM deletes `prod.db` or posts to Slack).

#### The Solution:
Every intercepted action issues an immutable **`ActionTicket`** locking both the **Tool Name** and the **Exact Arguments**:

```python
@dataclass
class ActionTicket:
    ticket_id: str      # e.g. "tkt_f28efc"
    tool_name: str      # e.g. "delete_file"
    arguments: dict     # e.g. {"filename": "README.md"}
```

#### Inside the Tool (Python Validation):
```python
# The tool only executes if BOTH tool name AND arguments match exactly
if ticket and ticket.tool_name == "delete_file" and ticket.arguments.get("filename") == filename:
    print(f"✅ [TOOL SUCCESS] delete_file -> Verified Ticket '{ticket.ticket_id}'. DELETED '{filename}'")
    return f"Success: Deleted '{filename}' (simulated)."
```

* **One-Time Token (Replay Protection):** In `main.py`, tickets are consumed via `ticket_store.pop(ticket_id)`, meaning a ticket is permanently destroyed upon use.

---

### 2. Single Source of Truth (`ToolRegistry` Decorator)

To prevent **dual-maintenance drift** (where metadata in a catalog doesn't match the Python implementation), tools are **self-registering**:

```python
@ToolRegistry.register(requires_approval=True)
def delete_file(ctx: RunContext[WorkflowDeps], filename: str) -> str:
    """Deletes a specific file from the project directory.
    
    Args:
        filename: The exact filename including extension (e.g. 'README.md').
    """
    ...
```

* **Automated Introspection:** The `@ToolRegistry.register` decorator automatically reads `func.__name__` and the docstring `func.__doc__` to populate `/api/tools` for the UI.
* **Zero Duplication:** It is physically impossible for a tool to be displayed in the UI without an active backend implementation.

---

### 3. FIFO Multi-Tool Execution Queue (Compound Prompts)

When a user submits a compound prompt (*"Delete README.md AND send a Slack alert to #general"*):
1. **Turn 1:** Both tools are intercepted during the agent run.
2. `pending_tickets: list[ActionTicket]` queues both `tkt_01` (delete) and `tkt_02` (slack).
3. FastAPI serves the **first pending action** (`delete_file`) to the UI.
4. When the user approves Step 1, the agent executes `delete_file`, and the UI automatically updates to prompt for Step 2 (`send_slack_alert`).
5. **Partial Execution Safety:** If the user approves Step 1 but rejects Step 2, Python guarantees that Step 2 is **never executed**.

---

### 4. High-Visibility Observability & Tracing

Every tool transition logs structured, unmissable events to the console:
* `🔧 [TOOL INVOKED]`: Logged the moment Python enters a function.
* `✅ [TOOL SUCCESS]`: Logged when an action successfully verifies its ticket and executes.
* `❌ [TOOL BLOCKED]`: Logged when security intercepts an unapproved action.

---

## 🔄 The Lifecycle of a Request (Step-by-Step Trace)

```text
Turn 1: User asks to delete a file
─────────────────────────────────────────────────────────────────────────────
Client          ──► POST /api/workflow/chat { input: "Delete README.md", approved_ticket_id: null }
FastAPI         ──► deps = WorkflowDeps(active_ticket=None)
Agent           ──► LLM attempts calling delete_file(filename="README.md")
delete_file()   ──► Python checks: No active ticket found!
                    Logs: "❌ [TOOL BLOCKED] delete_file -> Issued: tkt_f28efc"
                    Returns: "SYSTEM ERROR: Action requires approval. Ask user to confirm."
FastAPI         ──► Stores tkt_f28efc in ticket_store & returns pending_ticket
Client          ──► Pops up Glowing Action Card:
                    [ Action Authorization Required: delete_file | Target: {"filename":"README.md"} ]


Turn 2: User clicks "Approve & Execute"
─────────────────────────────────────────────────────────────────────────────
Client          ──► POST /api/workflow/chat { input: "Confirmed...", approved_ticket_id: "tkt_f28efc" }
FastAPI         ──► active_ticket = ticket_store.pop("tkt_f28efc")  (One-Time Token consumed)
                ──► deps = WorkflowDeps(active_ticket=active_ticket)
Agent           ──► LLM calls delete_file(filename="README.md")
delete_file()   ──► Python checks: Ticket ID matches AND filename matches!
                    Logs: "✅ [TOOL SUCCESS] delete_file -> Verified Ticket 'tkt_f28efc'. DELETED 'README.md'"
                    Returns: "Success: Deleted 'README.md' (simulated)."
FastAPI         ──► Stores turn in session_store
Client          ──► Displays success response and hides the Action Card.
```

---

## 🚀 Getting Started Locally

### 1. Prerequisites
* Python **3.12+**
* [uv](https://github.com/astral-sh/uv) (Fast Python package manager)
* [Ollama](https://ollama.ai/) running locally with the `qwen3:14b` model:
  ```bash
  ollama run qwen3:14b
  ```

### 2. Installation
```bash
uv pip install fastapi uvicorn pydantic-ai
```

### 3. Running the Server
```bash
uv run uvicorn main:app --reload
```

### 4. Accessing the Console
Open your browser and navigate to:
* **Interactive Web Console:** `http://localhost:8000`
* **Interactive Swagger API Docs:** `http://localhost:8000/docs`

