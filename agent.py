from pathlib import Path
from typing import ClassVar

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider

from models import WorkflowDeps

model = OllamaModel(
    "qwen3:14b", provider=OllamaProvider(base_url="http://localhost:11434/v1")
)

agent = Agent(
    model,
    deps_type=WorkflowDeps,
    instructions="""
    You are a helpful system automation assistant with access to tools.

    RULES FOR SENSITIVE ACTIONS:
    1. If a tool returns a SYSTEM ERROR about missing human approval, explain to the user that approval is required.
    2. As soon as the user confirms, approves, or clicks approve, you MUST IMMEDIATELY call the tool again to execute the action. Do not ask for confirmation twice.
    """,
)


class ToolRegistry:
    registered_tools: ClassVar[list[dict[str, object]]] = [
        {
            "name": "list_project_files",
            "description": "List files in the project",
            "requires_approval": False,
        },
        {
            "name": "delete_file",
            "description": "Deletes a file",
            "requires_approval": True,
        },
        {
            "name": "send_slack_alert",
            "description": "Sends a notification to Slack",
            "requires_approval": True,
        },
    ]


# 1. Safe tool (No context needed)
@agent.tool_plain
def list_project_files() -> list[str]:
    """List files in the project directory."""
    return [
        str(p) for p in Path(".").rglob("*") if p.is_file() and ".venv" not in p.parts
    ]


# 2. Sensitive tool (With HitL check)
@agent.tool
def delete_file(ctx: RunContext[WorkflowDeps], filename: str) -> str:
    """Deletes a file. Requires human approval."""
    if not ctx.deps.human_approved:
        print("❌ [SECURITY] Blocked 'delete_file'! Human approval required.")
        return "SYSTEM ERROR: Action 'delete_file' requires human approval. Please ask the user to approve. Once approved, call 'delete_file' again."

    print(f"⚙️ [EXECUTING] 'delete_file' with filename: {filename}")
    return f"Success: Deleted '{filename}' (simulated)."


# 3. New sensitive tool (Added in seconds!)
@agent.tool
def send_slack_alert(ctx: RunContext[WorkflowDeps], channel: str, message: str) -> str:
    """Sends an alert message to a Slack channel. Requires human approval."""
    if not ctx.deps.human_approved:
        print("❌ [SECURITY] Blocked 'send_slack_alert'! Human approval required.")
        return "SYSTEM ERROR: Action 'send_slack_alert' requires human approval. Please ask the user to approve. Once approved, call 'send_slack_alert' again."

    print(f"⚙️ [EXECUTING] 'send_slack_alert' to #{channel}")
    return f"Success: Alert posted to #{channel} with text '{message}' (simulated)."
