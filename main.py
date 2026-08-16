import logfire
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic_ai.messages import ModelMessage

from agent import ToolRegistry, agent
from models import ActionTicket, ChatRequest, WorkflowDeps

# 1. CONFIGURE LOGFIRE (Picks up your .logfire credentials automatically)
logfire.configure()

app = FastAPI(title="PoC HitL Agent Engine")

# 2. INSTRUMENT FASTAPI
logfire.instrument_fastapi(app)


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

    active_ticket = None
    if request.approved_ticket_id:
        active_ticket = ticket_store.pop(request.approved_ticket_id, None)

    deps = WorkflowDeps(active_ticket=active_ticket)

    result = await agent.run(request.user_input, deps=deps, message_history=history)

    # Store all intercepted tickets
    for tkt in deps.pending_tickets:
        ticket_store[tkt.ticket_id] = tkt

    # Serve the FIRST pending action to the frontend (Step 1 first!)
    pending_ticket_data = None
    if deps.pending_tickets:
        first_tkt = deps.pending_tickets[0]
        pending_ticket_data = {
            "ticket_id": first_tkt.ticket_id,
            "tool_name": first_tkt.tool_name,
            "arguments": first_tkt.arguments,
        }

    print(f"\n🧠 [AGENT TURN] Used Tokens: {result.usage.total_tokens}")
    print(f"💬 [AGENT RESPONSE] {result.output}\n")

    session_store[request.session_id] = result.all_messages()

    return {"response": result.output, "pending_ticket": pending_ticket_data}
