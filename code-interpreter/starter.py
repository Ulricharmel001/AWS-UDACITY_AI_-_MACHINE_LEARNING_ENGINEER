import json
import os

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.tools.code_interpreter_client import code_session
from strands import Agent, tool

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
MODEL = os.environ.get("WANDERBOT_MODEL", "us.amazon.nova-pro-v1:0")

SYSTEM_PROMPT = """\
You are WanderBot, a friendly travel assistant for Horizon Travel.

When asked to calculate costs, totals, conversions, or anything numeric that needs
careful arithmetic, always use the calculate_trip_cost tool. Write a Python
script that does the calculation and prints the final result. Never guess numbers.
"""


app = BedrockAgentCoreApp()


@tool
def calculate_trip_cost(code: str, description: str = "") -> str:
    """Execute Python code in an isolated AgentCore sandbox and return the output."""
    if description:
        code = f"# {description}\n{code}"

    print(f"\nGenerated Code:\n{code}\n")

    with code_session(REGION) as code_client:
        response = code_client.invoke(
            "executeCode",
            {
                "code": code,
                "language": "python",
                "clearContext": True,
            },
        )

    for event in response["stream"]:
        return json.dumps(event["result"])


@app.entrypoint
def invoke(payload, context=None):
    user_message = payload.get("message", "Hello!")
    agent = Agent(
        model=MODEL,
        system_prompt=SYSTEM_PROMPT,
        tools=[calculate_trip_cost],
    )
    return str(agent(user_message))


if __name__ == "__main__":
    app.run()
