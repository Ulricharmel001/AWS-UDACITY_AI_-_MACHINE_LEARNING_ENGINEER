# Solution: Long-Term Memory (Cross-Session) with AgentCore Memory

Use **AgentCore Memory** with **SEMANTIC** and **USER_PREFERENCE** strategies plus a Strands **HookProvider** to retrieve facts/preferences per `actor_id` (cross-session) and persist every `(USER, ASSISTANT)` turn.

## 1) Add strategies to the memory resource

In Bedrock AgentCore → Memory → edit your memory:
- Add **Semantic** strategy (e.g. `user-facts`) with namespace `wanderbot/{actorId}/facts` (or the template your helper expects)
- Add **User preference** strategy (e.g. `user-preferences`) with namespace `wanderbot/{actorId}/preferences`

Copy the **Memory ID** (e.g. `...`).

## 2) HookProvider wiring

```python
from bedrock_agentcore.memory import MemoryClient
from strands import Agent
from strands.hooks import HookProvider, HookRegistry, MessageAddedEvent, AfterInvocationEvent

def get_namespaces(memory_client: MemoryClient, memory_id: str):
    # return dict mapping strategy_type -> namespace template
    strategies = memory_client.get_memory_strategies(memory_id)
    ns = {}
    for s in strategies:
        st = s.get("strategyType") or s.get("type")
        nss = s.get("namespaces") or []
        if nss:
            ns[st] = nss[0]
    return ns
```

## 3) Retrieve on MessageAddedEvent, save on AfterInvocationEvent

```python
class WanderBotMemoryHook(HookProvider):
    def __init__(self, memory_client: MemoryClient, memory_id: str):
        self.memory_client = memory_client
        self.memory_id = memory_id
        self.namespaces = get_namespaces(memory_client, memory_id)

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(MessageAddedEvent, self._retrieve_travel_context)
        registry.add_callback(AfterInvocationEvent, self._save_interaction)

    def _retrieve_travel_context(self, event: MessageAddedEvent) -> None:
        actor_id = event.agent.state.get("actor_id")
        user_query = event.agent.messages[-1]["content"][0]["text"]

        all_context = []
        for strategy_type, namespace in self.namespaces.items():
            resolved = namespace.format(actorId=actor_id)
            memories = self.memory_client.retrieve_memories(
                memory_id=self.memory_id,
                namespace=resolved,
                query=user_query,
                top_k=5,
            )
            for m in memories:
                text = (m.get("content") or {}).get("text", "").strip()
                if text:
                    all_context.append(f"[{strategy_type}] {text}")

        if all_context:
            event.agent.messages[-1]["content"][0]["text"] = (
                "Traveller Context:\n" + "\n".join(all_context) + f"\n\n{user_query}"
            )

    def _save_interaction(self, event: AfterInvocationEvent) -> None:
        actor_id = event.agent.state.get("actor_id")
        session_id = event.agent.state.get("session_id")
        messages = event.agent.messages
        # find last user + assistant
        user_text = assistant_text = None
        for m in reversed(messages):
            if assistant_text is None and m.get("role") == "assistant":
                c = m.get("content", [])
                assistant_text = c[0].get("text") if c and isinstance(c[0], dict) else str(c[0]) if c else None
            elif user_text is None and m.get("role") == "user":
                c = m.get("content", [])
                user_text = c[0].get("text") if c and isinstance(c[0], dict) else str(c[0]) if c else None
            if user_text and assistant_text:
                break
        if not (actor_id and session_id and user_text and assistant_text):
            return
        self.memory_client.create_event(
            memory_id=self.memory_id,
            actor_id=actor_id,
            session_id=session_id,
            messages=[(user_text, "USER"), (assistant_text, "ASSISTANT")],
        )
```

## 4) Wire into agent

```python
memory_client = MemoryClient(region_name=REGION)
agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    hooks=[WanderBotMemoryHook(memory_client, MEMORY_ID)],
    state={"actor_id": actor_id, "session_id": session_id},
)
```

## Tips

- **Scope by actor_id**: namespaces resolved with `{actorId}` mean preferences/facts follow the user across sessions.
- **Retrieval timing**: inject context on `MessageAddedEvent` so the LLM sees long-term memory before responding.
- **Persistence timing**: save on `AfterInvocationEvent` so you capture the full turn.
- **Extraction is async**: memories may take a moment to appear after `create_event()`.
- **Permissions**: runtime role needs `bedrock-agentcore:*` memory operations as appropriate (`retrieve_memories`, `create_event`, `get_memory_strategies`).
