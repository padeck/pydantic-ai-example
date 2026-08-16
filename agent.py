import uuid
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
    You are a system automation assistant.
    When the user asks to delete a file or send a Slack alert, ALWAYS invoke the corresponding tool immediately.
    If the tool returns a SYSTEM ERROR about missing human approval, explain to the user what you tried to do and ask for their confirmation.
    When the user confirms or approves, you MUST immediately call the tool again.
    """,
)


# -------------------------------------------------------------
# Tool Catalog (Clean descriptions for the LLM)
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
            "description": "Deletes a file from the project",
            "requires_approval": True,
        },
        {
            "name": "send_slack_alert",
            "description": "Sends a notification to a Slack channel",
            "requires_approval": True,
        },
    ]


# -------------------------------------------------------------
# Tool Definitions
# -------------------------------------------------------------


@agent.tool_plain
def list_project_files() -> list[str]:
    """List files in the project directory."""
    return [
        str(p) for p in Path(".").rglob("*") if p.is_file() and ".venv" not in p.parts
    ]


@agent.tool
def delete_file(ctx: RunContext[WorkflowDeps], filename: str) -> str:
    """Deletes a file."""
    ticket = ctx.deps.active_ticket

    # 1. Exact parameter match check
    if (
        ticket
        and ticket.tool_name == "delete_file"
        and ticket.arguments.get("filename") == filename
    ):
        print(
            f"✅ [SECURITY] Ticket '{ticket.ticket_id}' verified for delete_file('{filename}'). Executing..."
        )
        return f"Success: Deleted '{filename}' (simulated)."

    # 2. Block and generate ticket
    new_ticket_id = f"tkt_{uuid.uuid4().hex[:6]}"
    ctx.deps.pending_ticket = ActionTicket(
        ticket_id=new_ticket_id,
        tool_name="delete_file",
        arguments={"filename": filename},
    )
    print(
        f"❌ [SECURITY] Blocked delete_file('{filename}')! Issued Ticket: {new_ticket_id}"
    )
    return f"SYSTEM ERROR: Deleting '{filename}' requires human approval. Ask the user for confirmation."


@agent.tool
def send_slack_alert(ctx: RunContext[WorkflowDeps], channel: str, message: str) -> str:
    """Sends a Slack message."""
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
    return f"SYSTEM ERROR: Sending Slack alert to #{channel} requires human approval. Ask the user for confirmation."
