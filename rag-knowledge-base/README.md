# RAG Knowledge Base — WanderBot

One Strands tool is the entire RAG integration. `search_knowledge_base` calls
the Bedrock Agent Runtime **`retrieve`** API with the user's query and joins the
returned chunks into a single grounding string that the LLM answers from.

## Files

| File | Purpose |
|------|---------|
| `starter.py` | The `search_knowledge_base` tool + a Strands agent served by `BedrockAgentCoreApp`. |
| `requirements.txt` | Python dependencies. |

## How retrieval works

1. The traveller asks, e.g. *"What's the cancellation fee 48 hours before
   departure?"*
2. The agent calls `search_knowledge_base(query=...)`.
3. Bedrock embeds the query with **Titan Text Embeddings v2**, searches the
   knowledge base's vector store, and returns the top chunks.
4. The tool joins chunk texts with `\n---\n` and returns them to the model.
5. The LLM quotes the exact figure from the retrieved policy — no hallucination,
   no prompt bloat.

If no chunks come back, the tool returns `No information found for: <query>`,
and the system prompt tells the agent to hand off to human support.

## Configuration

| Variable | Default | Meaning |
|----------|---------|---------|
| `KNOWLEDGE_BASE_ID` | `wanderbot-kb-2024-06` | Bedrock Knowledge Base id. Replace with your own. |
| `AWS_DEFAULT_REGION` | `us-east-1` | Region for the KB and model. |
| `WANDERBOT_MODEL` | `us.amazon.nova-pro-v1:0` | Bedrock model id. |

Prerequisites: the knowledge base must exist, be `ACTIVE`, and have a vector
store synced from its S3 data source. AWS credentials must allow
`bedrock:Retrieve` on that knowledge base.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python starter.py
```

In another terminal:

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the cancellation fee 48 hours before departure?"}'
```

## Deploy to AgentCore Runtime

```bash
agentcore configure -e starter.py -n WanderBotRAG -dt container \
  -rf requirements.txt --disable-memory --non-interactive
agentcore deploy
agentcore invoke '{"message": "What is the cancellation fee 48 hours before departure?"}'
```

## Example prompts

- `What's the cancellation fee 48 hours before departure?`
- `How much checked baggage is included in economy?`
- `How many points do I earn per dollar with the loyalty programme?`
