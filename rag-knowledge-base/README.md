# RAG with Bedrock Knowledge Bases

A simple RAG setup using Bedrock Knowledge Bases. A Strands `@tool` wraps `bedrock-agent-runtime.retrieve()` to pull relevant chunks from the KB and ground the agent's answers.

## Files
- `starter.py` - `search_knowledge_base` tool + AgentCore app
- `requirements.txt` - dependencies
- `SOLUTION.md` - solution notes

## How it works
1. User asks a policy/destination question
2. The agent calls `search_knowledge_base(query)`
3. `retrieve()` searches the KB (Titan v2 embeddings) and returns top chunks
4. The agent answers using only those chunks and quotes exact figures

## Setup
1. Upload `travel_policies.txt` and `destination_guides.txt` to S3
2. Create a Bedrock Knowledge Base pointing to that bucket (Titan Text Embeddings v2, S3 Vectors)
3. Sync and copy the KB ID
4. Set `KNOWLEDGE_BASE_ID` and run/deploy

## Run locally
```bash
pip install -r requirements.txt
export KNOWLEDGE_BASE_ID=<your-kb-id>
python starter.py
```
