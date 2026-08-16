from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class ActionTicket:
    ticket_id: str
    tool_name: str
    arguments: dict


@dataclass
class WorkflowDeps:
    # The ticket approved by the human for THIS execution turn
    active_ticket: ActionTicket | None = None
    # Generated if a tool call gets intercepted during this turn
    pending_ticket: ActionTicket | None = None


class ChatRequest(BaseModel):
    session_id: str
    user_input: str
    approved_ticket_id: str | None = None  # Specific Ticket ID being approved
