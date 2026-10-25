# Long-Term Agent Memory (AgentCore Memory)

Horizon Travel's Gold-tier members expect WanderBot to remember their preferences across every visit (window seats, dietary needs, travel style) without repeating themselves. This demo uses **Amazon Bedrock AgentCore Memory** with **SEMANTIC** and **USER_PREFERENCE** strategies, wired into a Strands agent via a **HookProvider**.

## Learning outcomes

- Add `SEMANTIC` and `USER_PREFERENCE` strategies to an AgentCore Memory resource and resolve their namespace templates at runtime
- Retrieve per-user memories with `retrieve_memories()` inside a `MessageAddedEvent` callback
- Persist a `(USER, ASSISTANT)` exchange with `create_event()` inside an `AfterInvocationEvent` callback
- Wire a custom `HookProvider` onto a Strands Agent using `agent.state` to pass `actor_id` and `session_id`

## How it works

1. **Create memory resource** (one-time, CLI/SDK) with:
   - `SemanticStrategy` — namespaces like `/strategies/{memoryStrategyId}/actors/{actorId}/`
   - `UserPreferenceStrategy` — namespaces like `/strategies/{memoryStrategyId}/actors/{actorId}/`
2. **On `MessageAddedEvent`**: read `actor_id` from `agent.state`, call `memory_client.retrieve_memories(memory_id, namespace, query=user_text, ...)` for both strategy namespaces (resolved) and prepend retrieved facts/preferences to the agent's context/system prompt or inject as a short "Long-term memory" section.
3. **On `AfterInvocationEvent`**: extract the last user message and assistant response, call `memory_client.create_event(memory_id, actor_id, session_id, messages=[(user_text, "USER"), (assistant_text, "ASSISTANT")])` so the memory system can extract and write long-term memories in the background.
4. **State passing**: set `agent.state = {"actor_id": "...", "session_id": "..."}` so hooks can scope retrieval/writes to the right user/session.

## Files

| File | Purpose |
|------|---------|
| `starter.py` | AgentCore entrypoint + Strands Agent + `LongTermMemoryHookProvider`. |
| `requirements.txt` | Dependencies. |
| `create_memory.py` | One-time script to create the memory resource with SEMANTIC and USER_PREFERENCE strategies (prints MEMORY_ID). |

## Environment

| Variable | Default | Notes |
|----------|---------|-------|
| `AGENTCORE_MEMORY_ID` | (required) | Memory resource ID from creation. |
| `AWS_DEFAULT_REGION` | `us-east-1` | AWS region. |
| `WANDERBOT_MODEL` | `us.amazon.nova-pro-v1:0` | Bedrock model. |

## Create the memory resource

```bash
python create_memory.py
# -> prints MEMORY_ID; export AGENTCORE_MEMORY_ID=...
```

## Run locally

```bash
pip install -r requirements.txt
export AGENTCORE_MEMORY_ID=<your-memory-id>
python starter.py
```

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id: sess-123456789012345678901234567890123" \
  -d '{"message": "I prefer window seats and vegetarian meals", "actor_id": "gold-member-001"}'

curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id: sess-abc..." \
  -d '{"message": "Book me a flight to Rome", "actor_id": "gold-member-001"}'
```

The second call (different/new session) should recall window seats and vegetarian meals via long-term memory.

## Deploy to AgentCore Runtime

```bash
agentcore configure -e starter.py -n WanderBotLTM -dt container -rf requirements.txt --disable-memory --non-interactive
agentcore deploy
agentcore invoke '{"message": "I prefer aisle seats", "actor_id": "gold-member-001"}'
```

## Notes

- Use `retrieve_memories()` (not just STM `get_last_k_turns`) for cross-session long-term facts/preferences.
- `create_event()` after each turn lets AgentCore extract memories asynchronously per the strategies.
- Always resolve namespace templates using the strategy's `memoryStrategyId`/namespaces.
