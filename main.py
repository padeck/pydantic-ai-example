from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic_ai.messages import ModelMessage

from agent import ToolRegistry, agent
from models import ActionTicket, ChatRequest, WorkflowDeps

app = FastAPI(title="PoC HitL Agent Engine")

# In-memory stores
session_store: dict[str, list[ModelMessage]] = {}
ticket_store: dict[str, ActionTicket] = {}


@app.get("/")
async def get_index():
    return FileResponse("index.html")


@app.get("/api/tools")
async def get_tools():
    return {"tools": ToolRegistry.registered_tools}


@app.post("/api/workflow/chat")
async def chat_endpoint(request: ChatRequest):
    history = session_store.get(request.session_id, [])

    # 1. Resolve approved ticket (if supplied by user click)
    active_ticket = None
    if request.approved_ticket_id:
        active_ticket = ticket_store.pop(
            request.approved_ticket_id, None
        )  # One-time use!

    # 2. Inject dependency
    deps = WorkflowDeps(active_ticket=active_ticket)

    # 3. Run Agent
    result = await agent.run(request.user_input, deps=deps, message_history=history)

    # 4. If an action was blocked, store the pending ticket
    pending_ticket_data = None
    if deps.pending_ticket:
        ticket_store[deps.pending_ticket.ticket_id] = deps.pending_ticket
        pending_ticket_data = {
            "ticket_id": deps.pending_ticket.ticket_id,
            "tool_name": deps.pending_ticket.tool_name,
            "arguments": deps.pending_ticket.arguments,
        }

    # Tracing logs
    print(f"\n🧠 [AGENT TURN] Used Tokens: {result.usage.total_tokens}")
    print(f"💬 [AGENT RESPONSE] {result.output}\n")

    session_store[request.session_id] = result.all_messages()

    return {"response": result.output, "pending_ticket": pending_ticket_data}
