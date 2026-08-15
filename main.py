from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic_ai.messages import ModelMessage

from agent import ToolRegistry, agent
from models import ChatRequest, WorkflowDeps

# 1. Initialize FastAPI FIRST
app = FastAPI(title="Riogentix HitL PoC")

# In-memory database for session history
session_store: dict[str, list[ModelMessage]] = {}


# 2. Routes
@app.get("/")
async def get_index():
    return FileResponse("index.html")


@app.get("/api/tools")
async def get_tools():
    return {"tools": ToolRegistry.registered_tools}


@app.post("/api/workflow/chat")
async def chat_endpoint(request: ChatRequest):
    history = session_store.get(request.session_id, [])
    deps = WorkflowDeps(human_approved=request.is_approval_click)

    result = await agent.run(request.user_input, deps=deps, message_history=history)

    # Tracing & Visibility logs
    print(f"\n🧠 [AGENT TURN] Used Tokens: {result.usage.total_tokens}")
    print(f"💬 [AGENT RESPONSE] {result.output}\n")

    session_store[request.session_id] = result.all_messages()
    return {"response": result.output}
