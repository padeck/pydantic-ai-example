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
    You are a helpful system automation assistant with access to tools.
    Always use your available tools to fulfill user requests.
    
    WORKFLOW RULES:
    1. If a tool execution fails due to missing human approval, inform the user and request confirmation.
    2. When the user confirms, approves, or says yes, you MUST immediately invoke the requested tool. Never ask for confirmation twice in a row.
    """,
)


# -------------------------------------------------------------
# Self-Registering Tool Catalog
# -------------------------------------------------------------
class ToolRegistry:
    registered_tools = []

    @classmethod
    def register(cls, requires_approval: bool = False):
        def decorator(func: Callable):
            description = (
                func.__doc__.strip().split("\n")[0]
                if func.__doc__
                else "No description"
            )
            cls.registered_tools.append(
                {
                    "name": func.__name__,
                    "description": description,
                    "requires_approval": requires_approval,
                }
            )
            if requires_approval:
                agent.tool(func)
            else:
                agent.tool_plain(func)
            return func

        return decorator


# -------------------------------------------------------------
# Tool Definitions with Queue-Safe Interception
# -------------------------------------------------------------


# 1. Safe Tool
@ToolRegistry.register(requires_approval=False)
def list_project_files() -> list[str]:
    """List all valid files currently in the project directory."""
    print("\n🔧 [TOOL INVOKED] list_project_files()")
    files = [
        str(p) for p in Path(".").rglob("*") if p.is_file() and ".venv" not in p.parts
    ]
    print(f"✅ [TOOL SUCCESS] list_project_files -> Found {len(files)} files.\n")
    return files


# 2. Sensitive Tool: File Deletion
@ToolRegistry.register(requires_approval=True)
def delete_file(ctx: RunContext[WorkflowDeps], filename: str) -> str:
    """Deletes a specific file from the project directory.

    Args:
        filename: The exact filename including extension (e.g. 'README.md').
    """
    print(f"\n🔧 [TOOL INVOKED] delete_file(filename='{filename}')")

    target_path = Path(filename)
    if not target_path.exists():
        matches = [
            p.name
            for p in Path(".").glob(f"*{filename}*")
            if p.is_file() and ".venv" not in p.parts
        ]
        if matches:
            print(
                f"⚠️ [TOOL VALIDATION] File '{filename}' not found. Closest match: '{matches[0]}'.\n"
            )
            return f"SYSTEM ERROR: File '{filename}' not found. Did you mean '{matches[0]}'? Please verify with user."
        print(f"⚠️ [TOOL VALIDATION] File '{filename}' does not exist on disk.\n")
        return f"SYSTEM ERROR: File '{filename}' does not exist in the project."

    ticket = ctx.deps.active_ticket

    # Scoped verification
    if (
        ticket
        and ticket.tool_name == "delete_file"
        and ticket.arguments.get("filename") == filename
    ):
        print(
            f"✅ [TOOL SUCCESS] delete_file -> Verified Ticket '{ticket.ticket_id}'. DELETED '{filename}' (simulated).\n"
        )
        return f"Success: Deleted '{filename}' (simulated)."

    # Append to ticket queue (no overwriting!)
    new_ticket_id = f"tkt_{uuid.uuid4().hex[:6]}"
    ctx.deps.pending_tickets.append(
        ActionTicket(
            ticket_id=new_ticket_id,
            tool_name="delete_file",
            arguments={"filename": filename},
        )
    )
    print(
        f"❌ [TOOL BLOCKED] delete_file -> Missing valid ticket for '{filename}'. Issued: {new_ticket_id}\n"
    )
    return f"SYSTEM ERROR: Action 'delete_file' on '{filename}' requires human approval. Ask the user for confirmation."


# 3. Sensitive Tool: Slack Notification
@ToolRegistry.register(requires_approval=True)
def send_slack_alert(ctx: RunContext[WorkflowDeps], channel: str, message: str) -> str:
    """Sends a notification message to a specific Slack channel.

    Args:
        channel: The target channel name without the hash.
        message: The exact notification text to broadcast.
    """
    print(
        f"\n🔧 [TOOL INVOKED] send_slack_alert(channel='{channel}', message='{message}')"
    )

    ticket = ctx.deps.active_ticket

    # Scoped verification
    if (
        ticket
        and ticket.tool_name == "send_slack_alert"
        and ticket.arguments.get("channel") == channel
    ):
        print(
            f"✅ [TOOL SUCCESS] send_slack_alert -> Verified Ticket '{ticket.ticket_id}'. Broadcasted to #{channel}.\n"
        )
        return f"Success: Alert posted to #{channel} with text '{message}' (simulated)."

    # Append to ticket queue (no overwriting!)
    new_ticket_id = f"tkt_{uuid.uuid4().hex[:6]}"
    ctx.deps.pending_tickets.append(
        ActionTicket(
            ticket_id=new_ticket_id,
            tool_name="send_slack_alert",
            arguments={"channel": channel, "message": message},
        )
    )
    print(
        f"❌ [TOOL BLOCKED] send_slack_alert -> Missing valid ticket for #{channel}. Issued: {new_ticket_id}\n"
    )
    return f"SYSTEM ERROR: Action 'send_slack_alert' to #{channel} requires human approval. Ask the user for confirmation."
