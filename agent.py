import uuid
from collections.abc import Callable
from pathlib import Path

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider

from models import ActionTicket, WorkflowDeps

model = OllamaModel(
    "qwen3:14b", provider=OllamaProvider(base_url="http://localhost:11434/v1")
)

agent = Agent(
    model,
    instructions="""
    You are a helpful system automation assistant.
    You have access to tools to interact with the project.
    Always use the appropriate tools to answer user requests.
    """,
)


# -------------------------------------------------------------
# Self-Registering Tool Catalog (Single Source of Truth)
# -------------------------------------------------------------
class ToolRegistry:
    registered_tools = []

    @classmethod
    def register(cls, requires_approval: bool = False):
        """Decorator that registers a tool with both the Pydantic-AI agent and the UI catalog."""

        def decorator(func: Callable):
            # 1. Extract first line of docstring as the clean description
            description = (
                func.__doc__.strip().split("\n")[0]
                if func.__doc__
                else "No description"
            )

            # 2. Add to metadata catalog for /api/tools
            cls.registered_tools.append(
                {
                    "name": func.__name__,
                    "description": description,
                    "requires_approval": requires_approval,
                }
            )

            # 3. Register directly with the Pydantic-AI agent
            if requires_approval:
                agent.tool(func)
            else:
                agent.tool_plain(func)

            return func

        return decorator


# -------------------------------------------------------------
# Tool Implementations (Fully Automated Registration)
# -------------------------------------------------------------


# 1. Safe Tool: Automatically registered as Safe
@ToolRegistry.register(requires_approval=False)
def list_project_files() -> list[str]:
    """List all valid files currently in the project directory."""
    return [
        str(p) for p in Path(".").rglob("*") if p.is_file() and ".venv" not in p.parts
    ]


# 2. Sensitive Tool: Automatically registered with HitL
@ToolRegistry.register(requires_approval=True)
def delete_file(ctx: RunContext[WorkflowDeps], filename: str) -> str:
    """Deletes a specific file from the project directory.

    Args:
        filename: The exact filename including extension (e.g. 'README.md').
    """
    target_path = Path(filename)
    if not target_path.exists():
        matches = [
            p.name
            for p in Path(".").glob(f"*{filename}*")
            if p.is_file() and ".venv" not in p.parts
        ]
        if matches:
            return f"SYSTEM ERROR: File '{filename}' not found. Did you mean '{matches[0]}'? Please verify with user."
        return f"SYSTEM ERROR: File '{filename}' does not exist in the project."

    ticket = ctx.deps.active_ticket
    if (
        ticket
        and ticket.tool_name == "delete_file"
        and ticket.arguments.get("filename") == filename
    ):
        print(
            f"✅ [SECURITY] Ticket '{ticket.ticket_id}' verified for delete_file('{filename}'). Executing..."
        )
        return f"Success: Deleted '{filename}' (simulated)."

    new_ticket_id = f"tkt_{uuid.uuid4().hex[:6]}"
    ctx.deps.pending_ticket = ActionTicket(
        ticket_id=new_ticket_id,
        tool_name="delete_file",
        arguments={"filename": filename},
    )
    print(
        f"❌ [SECURITY] Blocked delete_file('{filename}')! Issued Ticket: {new_ticket_id}"
    )
    return f"SYSTEM ERROR: Action 'delete_file' on '{filename}' requires human approval. Ask the user for confirmation."


# 3. Sensitive Tool: Automatically registered with HitL
@ToolRegistry.register(requires_approval=True)
def send_slack_alert(ctx: RunContext[WorkflowDeps], channel: str, message: str) -> str:
    """Sends a notification message to a specific Slack channel.

    Args:
        channel: The target channel name without the hash.
        message: The exact notification text to broadcast.
    """
    ticket = ctx.deps.active_ticket
    if (
        ticket
        and ticket.tool_name == "send_slack_alert"
        and ticket.arguments.get("channel") == channel
    ):
        print(
            f"✅ [SECURITY] Ticket '{ticket.ticket_id}' verified for send_slack_alert. Executing..."
        )
        return f"Success: Alert posted to #{channel} with text '{message}' (simulated)."

    new_ticket_id = f"tkt_{uuid.uuid4().hex[:6]}"
    ctx.deps.pending_ticket = ActionTicket(
        ticket_id=new_ticket_id,
        tool_name="send_slack_alert",
        arguments={"channel": channel, "message": message},
    )
    print(
        f"❌ [SECURITY] Blocked send_slack_alert to #{channel}! Issued Ticket: {new_ticket_id}"
    )
    return f"SYSTEM ERROR: Action 'send_slack_alert' to #{channel} requires human approval. Ask the user for confirmation."
