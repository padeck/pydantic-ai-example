from pathlib import Path

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider

from models import WorkflowDeps, WorkflowResponse

model = OllamaModel(
    "qwen3:14b",
    provider=OllamaProvider(base_url="http://localhost:11434/v1"),
)

agent = Agent(
    model,
    result_type=WorkflowResponse,
    deps_type=WorkflowDeps,
    system_prompt="""
    You are a helpful, secure system agent.
    You can list files in the project.
    If the user asks you to delete a file, you MUST NOT do it immediately. 
    Instead, set requires_approval=True and wait for the user to confirm.
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
    print(f"\n⚙️ [TOOL CALL] LLM is attempting to execute 'delete_file' on: {filename}")

    if not ctx.deps.human_approved:
        print(
            "❌ [SECURITY] Blocked! No human approval found. Returning SYSTEM ERROR to the LLM.\n"
        )
        return "SYSTEM ERROR: Execution blocked. You do not have human approval to run this."

    print("✅ [SECURITY] Human approval verified! Executing action...\n")
    return f"Success: Deleted '{filename}' (simulated)."
