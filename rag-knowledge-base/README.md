# RAG with Bedrock Knowledge Bases

Grounds WanderBot answers in Horizon Travel policies and destination guides using Bedrock Knowledge Bases.

## Files
- `starter.py` - `search_knowledge_base` @tool wrapping `bedrock-agent-runtime.retrieve()` + AgentCore app
- `requirements.txt` - dependencies
- `SOLUTION.md` - detailed solution + `strands_tools.retrieve` alternative

## How it works
1. On policy/destination questions, the agent calls `search_knowledge_base(query)`
2. The tool calls `retrieve()` with the KB ID, gets top chunks (Titan v2 embeddings)
3. Chunks are joined with separators and returned to the agent
4. The agent answers only from retrieved text and quotes exact figures/limits
5. If nothing found, it suggests contacting human support

## Setup
1. Upload `travel_policies.txt` and `destination_guides.txt` to S3
2. Create KB (S3 data source) with Titan Text Embeddings v2 + S3 Vectors, sync until Ready
3. Copy the 10-char KB ID

## Run locally
```bash
pip install -r requirements.txt
export KNOWLEDGE_BASE_ID=<kb-id>
export AWS_DEFAULT_REGION=us-east-1
python starter.py
```

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the baggage allowances for business class?"}'
```
