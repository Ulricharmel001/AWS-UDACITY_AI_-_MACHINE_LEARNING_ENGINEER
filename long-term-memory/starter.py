import logging
import os

from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.hooks import (
    AgentInitializedEvent,
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
travel style). Use any long-term memories provided to personalize
recommendations. If memories conflict with the user's current request, ask
for clarification.

When relevant, suggest options tailored to the user's known preferences.
"""


app = BedrockAgentCoreApp()


class LongTermMemoryHookProvider(HookProvider):
    def __init__(self, memory_client: MemoryClient, memory_id: str):
        self.memory_client = memory_client
        self.memory_id = memory_id
        self._last_user_text = None

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(MessageAddedEvent, self.on_message_added)
        registry.add_callback(AfterInvocationEvent, self.after_invocation)

    def _get_actor_session(self, event):
        agent = getattr(event, "agent", None)
        if not agent:
            return None, None
        state = getattr(agent, "state", {}) or {}
        if isinstance(state, dict):
            return state.get("actor_id"), state.get("session_id")
        return getattr(state, "get", lambda k: None)("actor_id"), getattr(state, "get", lambda k: None)("session_id")

    def on_message_added(self, event: MessageAddedEvent) -> None:
        actor_id, _ = self._get_actor_session(event)
        if not actor_id or not self.memory_id:
            return

        message = getattr(event, "message", {}) or {}
        content = message.get("content", [])
        if not content or not isinstance(content[0], dict):
            return
        user_text = content[0].get("text")
        if not user_text:
            return

        self._last_user_text = user_text

        memories_text = []
        try:
            # Retrieve memories for this actor across strategies
            # Namespace pattern: /strategies/{memoryStrategyId}/actors/{actorId}/
            resp = self.memory_client.retrieve_memories(
                memoryId=self.memory_id,
                namespace=f"/strategies/*/actors/{actor_id}/",
                query=user_text,
                maxResults=10,
            )
            for mem in resp.get("memories", []) if isinstance(resp, dict) else []:
                content_block = mem.get("content") or {}
                if isinstance(content_block, dict):
                    text = content_block.get("text") or mem.get("text") or ""
                else:
                    text = str(content_block)
                if text:
                    memories_text.append(f"- {text}")
        except Exception as exc:
            logger.warning("retrieve_memories failed: %s", exc)
            return

        if not memories_text:
            return

        agent = getattr(event, "agent", None)
        if agent and hasattr(agent, "system_prompt"):
            facts = "\n".join(memories_text)
            agent.system_prompt += f"\n\nLong-term memories for this user:\n{facts}"
            logger.info("Injected %d long-term memories", len(memories_text))

    def after_invocation(self, event: AfterInvocationEvent) -> None:
        actor_id, session_id = self._get_actor_session(event)
        if not actor_id or not session_id or not self.memory_id or not self._last_user_text:
            return

        agent = getattr(event, "agent", None)
        messages = getattr(agent, "messages", []) if agent else []
        assistant_text = None
        for m in reversed(messages):
            if isinstance(m, dict) and m.get("role") == "assistant":
                content = m.get("content", [])
                if content and isinstance(content[0], dict):
                    assistant_text = content[0].get("text")
                elif content:
                    assistant_text = str(content[0])
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
            logger.info("Persisted turn to long-term memory")
        except Exception as exc:
            logger.warning("create_event failed: %s", exc)
        finally:
            self._last_user_text = None


@app.entrypoint
def invoke(payload, context=None):
    if not MEMORY_ID:
        raise ValueError("AGENTCORE_MEMORY_ID is required")

    user_message = payload.get("message", "Hello!")
    actor_id = payload.get("actor_id", "gold-member-001")
    session_id = getattr(context, "session_id", None) or payload.get("session_id") or "default-session"

    memory_client = MemoryClient(region_name=REGION)
    agent = Agent(
        model=MODEL,
        system_prompt=SYSTEM_PROMPT,
        hooks=[LongTermMemoryHookProvider(memory_client, MEMORY_ID)],
        state={"actor_id": actor_id, "session_id": session_id},
    )
    return str(agent(user_message))


if __name__ == "__main__":
    app.run()
