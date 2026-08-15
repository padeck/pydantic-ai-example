from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider


@dataclass
class WorkflowDeps:
    human_approved: bool = False


class ChatRequest(BaseModel):
    session_id: str
    user_input: str
    is_approval_click: bool = False


model = OllamaModel(
    "qwen3:14b",
    provider=OllamaProvider(base_url="http://localhost:11434/v1"),
)

# We omit result_type/deps_type here to avoid version errors.
# We use 'instructions' exactly as you did in your initial code.
agent = Agent(
    model,
    instructions="""
    You are a helpful coding assistant.
    If the user asks you to delete a file, you MUST NOT do it immediately. 
    You must ask for their permission first. 
    If your tool returns an error about missing approval, politely ask the user to approve the action.
    """,
)


@agent.tool_plain
def list_project_files() -> list[str]:
    """Return the files in the current project directory."""
    return [
        str(path)
        for path in Path(".").rglob("*")
        if path.is_file() and ".venv" not in path.parts and ".git" not in path.parts
    ]


@agent.tool
def delete_file(ctx: RunContext[WorkflowDeps], filename: str) -> str:
    """Deletes a file. Fails without human approval."""
    # THE HARD-LOCK: We check the injected state, bypassing the LLM entirely.
    if not ctx.deps.human_approved:
        return "SYSTEM ERROR: Execution blocked. You do not have human approval to run this."

    return f"Success: Deleted '{filename}' (simulated)."


app = FastAPI(title="Riogentix HitL PoC")

# In-memory store for session history
session_store: dict[str, list[ModelMessage]] = {}


@app.post("/api/workflow/chat")
async def chat_endpoint(request: ChatRequest):
    # Load history
    history = session_store.get(request.session_id, [])

    # Inject our dependency state based on the frontend request
    deps = WorkflowDeps(human_approved=request.is_approval_click)

    # Run the agent
    result = await agent.run(request.user_input, deps=deps, message_history=history)

    print(f"\n🧠 [AGENT TURN] Used Tokens: {result.usage().total_tokens}")
    print(f"💬 [AGENT RESPONSE] {result.output}\n")

    # Save the updated history (works in both older and newer versions)
    session_store[request.session_id] = result.all_messages()

    return {"response": result.output}
