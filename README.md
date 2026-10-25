# AWS Bedrock AgentCore Demos

This repo contains hands-on demos for building agents with Amazon Bedrock AgentCore and the Strands SDK.

## Demos

| Folder | What it covers | Key files |
|---|---|---|
| `short-term-memery/` | Short-term/session memory with AgentCore Memory hooks. Remembers turns within the same session via `get_last_k_turns` + `create_event`. | `agent.py`, `test_memory.sh` |
| `agentcore-browser/` | Web browsing with AgentCore Browser. Agent navigates to Wikivoyage and extracts specific info from destination pages. | `starter.py` |
| `rag-knowledge-base/` | RAG with Bedrock Knowledge Bases. `@tool` wraps `bedrock-agent-runtime.retrieve()` to ground answers in policy/destination docs. | `starter.py`, `SOLUTION.md` |
| `long-term-memory/` | Cross-session long-term memory with SEMANTIC and USER_PREFERENCE strategies. Uses hooks to retrieve by `actor_id` and persist turns. | `starter.py`, `create_memory.py`, `SOLUTION.md` |
| `demo1-invoke-api/` | Bedrock InvokeModel API (Nova) - summarization and streaming. | `meeting_summarizer.py`, `meeting_summarizer_stream.py` |
| `demo2-converse-api/` | Bedrock Converse API - chat with history and tool calling. | `simple_travel_chat.py`, `restaurants_booking_assistant.py` |
| `demo3-chaining--critique/` | Prompt chaining, routing, critique/refinement. | `content_pipeline.py`, `email_refiner.py` |
| `agentcore-project-submission/` | Full project submission (flows, harness, gateway). | See its `README.md` |

## Core ideas

- **Tools**: Extend agents with `@tool` (search, KB retrieve, browser actions)
- **Memory**: Short-term (session) vs long-term (cross-session) via AgentCore Memory + Strands hooks
- **RAG**: Ground answers in your data with Bedrock Knowledge Bases
- **Runtime**: Deploy agents to AgentCore Runtime with `agentcore configure/deploy/invoke`

## Prerequisites

- AWS credentials configured
- Access to Bedrock models (e.g. Nova)
- Python 3.10+
- `boto3`, `strands-agents`, `bedrock-agentcore`
