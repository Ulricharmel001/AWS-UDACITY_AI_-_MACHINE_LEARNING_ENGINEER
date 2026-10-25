# Short-Term Memory (Session Memory)

WanderBot remembers conversation turns within the same session using AgentCore Memory and Strands hooks.

## Files
- `agent.py` - Agent with `ShortTermMemoryHookProvider` that loads/saves turns via `get_last_k_turns` and `create_event`
- `requirements.txt` - dependencies
- `test_memory.sh` - quick test script

## How it works
1. On `AgentInitializedEvent`, the hook reads last k turns for the `(actor_id, session_id)` and prepends them to the system prompt
2. On `MessageAddedEvent`, the hook saves each message to memory with `create_event()`
3. Both calls must share the same `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id` header (or `--session-id` with CLI)

## Run locally
```bash
pip install -r requirements.txt
export AGENTCORE_MEMORY_ID=<your-memory-id>
python agent.py
```

```bash
./test_memory.sh
```

## Notes
- Session ID must be 33+ characters and stay the same across turns to recall context
- Without a session ID, the hook skips loading/saving
