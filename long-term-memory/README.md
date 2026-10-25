# Long-Term Memory with AgentCore Memory

Cross-session memory so WanderBot remembers preferences/facts per user across different sessions.

## Files
- `starter.py` - `TravelerMemoryHook` with `MessageAddedEvent` + `AfterInvocationEvent`
- `create_memory.py` - create memory with SEMANTIC and USER_PREFERENCE strategies
- `requirements.txt` - dependencies
- `SOLUTION.md` - detailed solution

## How it works
- **Retrieve** (`MessageAddedEvent`): looks up memories for `actor_id` from both strategy namespaces (`wanderbot/{actorId}/facts`, `wanderbot/{actorId}/preferences`), prepends as `Traveller Context`, skips if message is a `toolResult`
- **Persist** (`AfterInvocationEvent`): saves the last `(USER, ASSISTANT)` pair via `create_event()` so extraction can build long-term memories asynchronously
- **Scope**: `actor_id` is the stable key (loyalty/user id). `session_id` changes each invoke and comes from context/state
- `get_memory_strategies()` resolves namespace templates at runtime

## Setup
1. Create/add strategies in console or `python create_memory.py`
   - SEMANTIC: `wanderbot/{actorId}/facts`
   - USER_PREFERENCE: `wanderbot/{actorId}/preferences`
2. Set `AGENTCORE_MEMORY_ID`

## Run locally
```bash
pip install -r requirements.txt
export AGENTCORE_MEMORY_ID=<memory-id>
python starter.py
```

```bash
# Session 1
curl -X POST http://localhost:8080/invocations -H "Content-Type: application/json" -H "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id: sess-111111111111111111111111111111111" -d '{"message": "I always want window seat and I am lactose intolerant.", "actor_id": "alex-001"}'

# Wait ~30s, then Session 2 (different session id)
curl -X POST http://localhost:8080/invocations -H "Content-Type: application/json" -H "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id: sess-222222222222222222222222222222222" -d '{"message": "Recommend a meal option for my flight.", "actor_id": "alex-001"}'
```
