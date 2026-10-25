import logging
import os

from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.hooks import (
    AfterInvocationEvent,
    HookProvider,
    HookRegistry,
    MessageAddedEvent,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID")
MODEL = os.environ.get("WANDERBOT_MODEL", "us.amazon.nova-pro-v1:0")

SYSTEM_PROMPT = """\
You are WanderBot, a friendly travel assistant for Horizon Travel.

You remember the user's preferences across sessions (window/aisle, dietary needs,
travel style, traveling with children). Use any long-term memories provided to
personalize recommendations. If memories conflict with the user's current request,
ask for clarification.

When relevant, suggest options tailored to the user's known preferences.
"""


app = BedrockAgentCoreApp()

memory_client = MemoryClient(region_name=REGION)


def get_namespaces(memory_client: MemoryClient, memory_id: str):
    namespaces = {}
    try:
        strategies = memory_client.get_memory_strategies(memory_id)
        for strategy in strategies:
            strategy_type = strategy.get("strategyType") or strategy.get("type")
            nss = strategy.get("namespaces") or []
            if strategy_type and nss:
                namespaces[strategy_type] = nss[0]
    except Exception as exc:
        logger.warning("Failed to get memory strategies: %s", exc)
    return namespaces


class TravelerMemoryHook(HookProvider):
    def __init__(self, memory_client: MemoryClient, memory_id: str):
        self.memory_client = memory_client
        self.memory_id = memory_id
        self.namespaces = get_namespaces(memory_client, memory_id)
        self._last_user_text = None

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(MessageAddedEvent, self._retrieve_travel_context)
        registry.add_callback(AfterInvocationEvent, self._save_interaction)

    def _get_actor_session(self, event):
        agent = getattr(event, "agent", None)
        if not agent:
            return None, None
        state = getattr(agent, "state", {}) or {}
        if isinstance(state, dict):
            return state.get("actor_id"), state.get("session_id")
        get = getattr(state, "get", None)
        if callable(get):
            return get("actor_id"), get("session_id")
        return getattr(state, "actor_id", None), getattr(state, "session_id", None)

    def _retrieve_travel_context(self, event: MessageAddedEvent) -> None:
        agent = getattr(event, "agent", None)
        if not agent or not self.memory_id:
            return

        actor_id, _ = self._get_actor_session(event)
        if not actor_id:
            return

        messages = getattr(agent, "messages", []) or []
        if not messages:
            return

        last_message = messages[-1]
        if not isinstance(last_message, dict):
            return

        content = last_message.get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("toolResult") is not None:
                    return

        if not content or not isinstance(content[0], dict):
            return

        user_query = content[0].get("text")
        if not user_query or not isinstance(user_query, str):
            return

        self._last_user_text = user_query

        all_context = []
        for strategy_type, namespace in self.namespaces.items():
            try:
                resolved_ns = namespace.format(actorId=actor_id)
                resp = self.memory_client.retrieve_memories(
                    memory_id=self.memory_id,
                    namespace=resolved_ns,
                    query=user_query,
                    top_k=5,
                )
                memories = resp.get("memories", []) if isinstance(resp, dict) else []
                for mem in memories:
                    content_block = mem.get("content") or {}
                    if isinstance(content_block, dict):
                        text = content_block.get("text") or mem.get("text") or ""
                    else:
                        text = str(content_block)
                    text = text.strip()
                    if text:
                        all_context.append(f"[{strategy_type}] {text}")
            except Exception as exc:
                logger.warning("retrieve_memories failed for %s: %s", strategy_type, exc)
                continue

        if not all_context:
            return

        context_block = "Traveller Context:\n" + "\n".join(all_context) + f"\n\n{user_query}"
        content[0]["text"] = context_block
        logger.info("Injected %d long-term memories for actor_id=%s", len(all_context), actor_id)

    def _save_interaction(self, event: AfterInvocationEvent) -> None:
        actor_id, session_id = self._get_actor_session(event)
        if not actor_id or not session_id or not self.memory_id or not self._last_user_text:
            return

        agent = getattr(event, "agent", None)
        messages = getattr(agent, "messages", []) if agent else []
        assistant_text = None

        for m in reversed(messages):
            if isinstance(m, dict) and m.get("role") == "assistant":
                content = m.get("content", [])
                if isinstance(content, list) and content and isinstance(content[0], dict):
                    assistant_text = content[0].get("text")
                elif isinstance(content, list) and content:
                    assistant_text = str(content[0])
                elif isinstance(content, str):
                    assistant_text = content
                break

        if not assistant_text:
            return

        try:
            self.memory_client.create_event(
                memory_id=self.memory_id,
                actor_id=actor_id,
                session_id=session_id,
                messages=[
                    (self._last_user_text, "USER"),
                    (assistant_text, "ASSISTANT"),
                ],
            )
            logger.info("Persisted turn to long-term memory for actor_id=%s", actor_id)
        except Exception as exc:
            logger.warning("create_event failed: %s", exc)
        finally:
            self._last_user_text = None


@app.entrypoint
async def invoke(payload: dict, context=None) -> dict:
    if not MEMORY_ID:
        raise ValueError("AGENTCORE_MEMORY_ID is required")

    user_message = payload.get("message", "Hello!")
    session_id = getattr(context, "session_id", None)
    actor_id = payload.get("actor_id", "wanderbot-user")

    memory_hook = TravelerMemoryHook(
        memory_client=memory_client,
        memory_id=MEMORY_ID,
    )

    agent = Agent(
        model=MODEL,
        system_prompt=SYSTEM_PROMPT,
        tools=[],
        state={"session_id": session_id, "actor_id": actor_id},
        hooks=[memory_hook],
    )
    return agent(user_message)


if __name__ == "__main__":
    app.run()
