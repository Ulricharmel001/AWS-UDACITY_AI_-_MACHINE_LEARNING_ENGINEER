# Long-Term Memory with AgentCore Memory

WanderBot remembers preferences across sessions using AgentCore Memory with SEMANTIC and USER_PREFERENCE strategies.

## Files
- `starter.py` - Agent with `TravelerMemoryHook`
- `create_memory.py` - create memory with strategies
- `requirements.txt` - dependencies
- `SOLUTION.md` - solution notes

## How it works
- `MessageAddedEvent` → `retrieve_memories()` pulls facts/preferences for the `actor_id` and adds them to the user message
- `AfterInvocationEvent` → `create_event()` saves the (USER, ASSISTANT) turn for extraction
- `actor_id` comes from payload, `session_id` from context; both passed via `agent.state`
- Session IDs change per invoke, so long-term memory is scoped to `actor_id`

## Setup
1. Create memory: `python create_memory.py` (or add strategies in console)
2. Add strategies in console: `wanderbot/{actorId}/facts` (SEMANTIC), `wanderbot/{actorId}/preferences` (USER_PREFERENCE)
3. Set `AGENTCORE_MEMORY_ID`
4. Deploy and test across different sessions with same `actor_id`
