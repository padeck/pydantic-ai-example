from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider

model = OllamaModel(
    "qwen3:14b",
    provider=OllamaProvider(
        base_url="http://localhost:11434/v1",
    ),
)

agent = Agent(
    model,
    instructions="""
    You are a helpful coding assistant.
    You can inspect files in the current project when needed.
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


result = agent.run_sync("What files are in my project? Please list them for me.")

print(result.output)
