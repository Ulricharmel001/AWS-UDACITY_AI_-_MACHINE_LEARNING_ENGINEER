# Solution: Bedrock Knowledge Base RAG

The solution is to wrap `bedrock-agent-runtime.retrieve()` in a single Strands `@tool` and pass it to the agent. The tool fetches top chunks from the Bedrock Knowledge Base and returns them joined as grounding context; the LLM is instructed to answer only from that text.

## 1) Add the tool and wire it up

```python
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
(fees, limits, deadlines, percentages) instead of paraphrasing.

If the tool finds nothing relevant, say you don't have that information and
offer to connect the customer with a human agent at 1-800-555-0199.
"""

@tool
def search_knowledge_base(query: str) -> str:
    """
    Search Horizon Travel's knowledge base for travel policies,
    destination guides, baggage rules, and loyalty programme details.
    Use this when a customer asks about policies, destinations, or travel tips.
    """
    resp = _bedrock_runtime.retrieve(
        knowledgeBaseId=KB_ID,
        retrievalQuery={"text": query},
        retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": 5}},
    )
    results = resp.get("retrievalResults", [])
    if not results:
        return f"No information found for: {query}"

    chunks = []
    for r in results:
        text = r.get("content", {}).get("text", "")
        loc = r.get("location", {}).get("s3Location", {}).get("uri", "")
        chunks.append(f"[Source: {loc}]\n{text}" if loc else text)
    return "\n\n---\n\n".join(chunks)

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload, context=None):
    user_message = payload.get("message", "Hello!")
    agent = Agent(model=MODEL, system_prompt=SYSTEM_PROMPT, tools=[search_knowledge_base])
    return str(agent(user_message))

if __name__ == "__main__":
    app.run()
```

## Key points

- **KB ID**: use the 10-character Knowledge Base ID (not ARN or data source ID). Pass via `KNOWLEDGE_BASE_ID` or hardcode as shown.
- **Top-k**: `numberOfResults: 5` is the sweet spot (avoid higher unless chunking is tuned).
- **Citations**: include `s3Location.uri` from results to make grounding visible.
- **Force tool use**: the system prompt must tell the agent to ALWAYS call `search_knowledge_base` for policy/destination questions.
- **Permissions**: the AgentCore Runtime role needs `bedrock:Retrieve` on the KB.
- **Sync first**: if the data source hasn't synced, `retrieve()` returns empty results.

## Alternative: use `strands_tools.retrieve`

If you don't need custom formatting, `strands-tools` ships a built-in `retrieve` tool that reads `KNOWLEDGE_BASE_ID` from env and works out of the box:

```python
import os
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands_tools import retrieve

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload, context=None):
    user_message = payload.get("message", "Hello!")
    agent = Agent(tools=[retrieve])
    return str(agent(user_message))

if __name__ == "__main__":
    app.run()
```

Deploy with: `agentcore deploy --env KNOWLEDGE_BASE_ID=<your-kb-id>`

Both approaches give grounded, citation-friendly answers with no prompt bloat.
