from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel
from strands_tools import calculator

app = BedrockAgentCoreApp()
model = BedrockModel(model_id="us.amazon.nova-2-lite-v1:0")

SYSTEM_PROMPT = """You are WanderBot, the official AI travel assistant for Horizon Travel...
When asked to calculate costs, points, durations, or any numeric value,
always use the calculator tool for accuracy."""


@app.entrypoint
async def invoke(payload: dict, context=None):
    user_message = payload.get("message") or payload.get("prompt") or "Hello!"
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[calculator],
    )
    return agent(user_message)


if __name__ == "__main__":
    app.run()