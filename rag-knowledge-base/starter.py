import os

import boto3
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool

KB_ID = os.environ.get("KNOWLEDGE_BASE_ID", "wanderbot-kb-2024-06")
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
MODEL = os.environ.get("WANDERBOT_MODEL", "us.amazon.nova-pro-v1:0")

_bedrock_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)

SYSTEM_PROMPT = """\
You are WanderBot, a friendly travel assistant for Horizon Travel.

ALWAYS use search_knowledge_base before answering policy, baggage, insurance,
loyalty, or destination questions. Do not guess.

Answer using only the information returned by the tool. Quote exact figures
(fees, limits, deadlines, percentages) instead of paraphrasing. If multiple
chunks are relevant, synthesize them clearly.

If the tool finds nothing relevant, say you don't have that information and
offer to connect the customer with a human agent at 1-800-555-0199.
"""


@tool
def search_knowledge_base(query: str) -> str:
    """
    Search Horizon Travel's knowledge base for travel policies,
    destination guides, baggage rules, and loyalty programme details.
    Use this when a customer asks about policies, destinations, or travel tips.

    Args:
        query: The question or topic to search for
    Returns:
        Relevant information retrieved from the knowledge base
    """
    resp = _bedrock_runtime.retrieve(
        knowledgeBaseId=KB_ID,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {"numberOfResults": 5}
        },
    )
    results = resp.get("retrievalResults", [])
    if not results:
        return f"No information found for: {query}"

    chunks = []
    for r in results:
        text = r.get("content", {}).get("text", "")
        loc = r.get("location", {}).get("s3Location", {}).get("uri", "")
        if loc:
            chunks.append(f"[Source: {loc}]\n{text}")
        else:
            chunks.append(text)
    return "\n\n---\n\n".join(chunks)


app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context=None):
    user_message = payload.get("message", "Hello!")
    agent = Agent(
        model=MODEL,
        system_prompt=SYSTEM_PROMPT,
        tools=[search_knowledge_base],
    )
    return str(agent(user_message))


if __name__ == "__main__":
    app.run()
