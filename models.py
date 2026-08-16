from dataclasses import dataclass, field

from pydantic import BaseModel


@dataclass
class ActionTicket:
    ticket_id: str
    tool_name: str
    arguments: dict


@dataclass
class WorkflowDeps:
    active_ticket: ActionTicket | None = None
    # A list of pending tickets intercepted in this turn
    pending_tickets: list[ActionTicket] = field(default_factory=list)


class ChatRequest(BaseModel):
    session_id: str
    user_input: str
    approved_ticket_id: str | None = None
