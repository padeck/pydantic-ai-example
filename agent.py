import uuid
from pathlib import Path

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider

from models import ActionTicket, WorkflowDeps

model = OllamaModel(
    "qwen3:14b", provider=OllamaProvider(base_url="http://localhost:11434/v1")
)

# 1. Global instructions stay clean and generic
agent = Agent(
    model,
    instructions="""
    You are a helpful system automation assistant.
    You have access to tools to interact with the project.
    Always use the appropriate tools to answer user requests.
    """,
)


# -------------------------------------------------------------
# Tool Metadata Catalog (For the /api/tools endpoint)
# -------------------------------------------------------------
class ToolRegistry:
    registered_tools = [
        {
            "name": "list_project_files",
            "description": "List files in the project",
            "requires_approval": False,
        },
        {
            "name": "delete_file",
            "description": "Deletes a specific file from the project",
            "requires_approval": True,
        },
        {
            "name": "send_slack_alert",
            "description": "Sends a notification to a Slack channel",
            "requires_approval": True,
        },
    ]


# -------------------------------------------------------------
# Self-Describing Tool Definitions
# -------------------------------------------------------------


# 1. Safe Tool: File Listing
@agent.tool_plain
def list_project_files() -> list[str]:
    """List all valid files currently in the project directory."""
    return [
        str(p) for p in Path(".").rglob("*") if p.is_file() and ".venv" not in p.parts
    ]


# 2. Sensitive Tool: File Deletion
@agent.tool
def delete_file(ctx: RunContext[WorkflowDeps], filename: str) -> str:
    """Deletes a file from the project directory.

    Args:
        filename: The exact, case-sensitive filename including its extension (e.g. 'README.md', 'main.py').
                  Do not guess or omit extensions. If you don't know the exact filename, inspect the project files first.
    """
    # Existence & Disambiguation Check
    target_path = Path(filename)
    if not target_path.exists():
        matches = [
            p.name
            for p in Path(".").glob(f"*{filename}*")
            if p.is_file() and ".venv" not in p.parts
        ]
        if matches:
            return f"SYSTEM ERROR: File '{filename}' not found. Did you mean '{matches[0]}'? Please check with list_project_files or ask the user."
        return f"SYSTEM ERROR: File '{filename}' does not exist in the project."

    ticket = ctx.deps.active_ticket

    # Scoped Ticket Check
    if (
        ticket
        and ticket.tool_name == "delete_file"
        and ticket.arguments.get("filename") == filename
    ):
        print(
            f"✅ [SECURITY] Ticket '{ticket.ticket_id}' verified for delete_file('{filename}'). Executing..."
        )
        return f"Success: Deleted '{filename}' (simulated)."

    # Block and Issue Ticket
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


# 3. Sensitive Tool: Slack Notification
@agent.tool
def send_slack_alert(ctx: RunContext[WorkflowDeps], channel: str, message: str) -> str:
    """Sends a notification message to a specific Slack channel.

    Args:
        channel: The target channel name without the hash (e.g. 'releases', 'general', 'alerts').
        message: The exact notification text to broadcast to the channel.
    """
    ticket = ctx.deps.active_ticket

    # Scoped Ticket Check
    if (
        ticket
        and ticket.tool_name == "send_slack_alert"
        and ticket.arguments.get("channel") == channel
    ):
        print(
            f"✅ [SECURITY] Ticket '{ticket.ticket_id}' verified for send_slack_alert. Executing..."
        )
        return f"Success: Alert posted to #{channel} with text '{message}' (simulated)."

    # Block and Issue Ticket
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
