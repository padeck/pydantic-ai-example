from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

model = OpenAIModel(
    "qwen3",
    provider=OpenAIProvider(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
    ),
)

agent = Agent(
    model,
    instructions="You are a helpful assistant.",
)

result = agent.run_sync("Explain dependency injection in Python.")

print(result.output)
