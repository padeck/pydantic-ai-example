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
    instructions="You are a helpful assistant.",
)

result = agent.run_sync("What is dependency injection in Python?")

print(result.output)
