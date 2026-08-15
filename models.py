from dataclasses import dataclass

from pydantic import BaseModel, Field


# The "Hard-Lock" dependency state
@dataclass
class WorkflowDeps:
    human_approved: bool = False


# The structured output the LLM must generate
class WorkflowResponse(BaseModel):
    agent_message: str = Field(description="The message to show the user.")
    requires_approval: bool = Field(
        default=False,
        description="Set to True if you need to execute a dangerous action.",
    )
    planned_action: str | None = Field(
        default=None, description="E.g., 'Delete file main.py'"
    )


# The incoming API request from the frontend
class ChatRequest(BaseModel):
    session_id: str
    user_input: str
    is_approval_click: bool = False
