import logging
import os

from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.hooks import (
    AgentInitializedEvent,
    HookProvider,
    HookRegistry,
    MessageAddedEvent,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", "WanderBotMemory-55evwoEyGp")
MODEL = "us.amazon.nova-lite-v1:0"

SYSTEM_PROMPT = """\
You are WanderBot, a friendly travel assistant.

You help users find hotels and plan trips. Use the search_hotels tool when
the user asks about accommodation. Remember what the user already told you
(destination, dates, budget, preferences) and use it in follow-up turns.
"""

app = BedrockAgentCoreApp()


@tool
def search_hotels(city: str, check_in: str, check_out: str) -> str:
    """Search for hotels in a city for the given dates.

    Args:
        city: The city to search in.
        check_in: Check-in date (YYYY-MM-DD).
        check_out: Check-out date (YYYY-MM-DD).
    """
    return (
        f"Found 3 hotels in {city} for {check_in} to {check_out}: "
        "Harbour View Inn ($180/night), City Central Hotel ($140/night), "
        "The Grand Meridian ($250/night)."
    )


class ShortTermMemoryHookProvider(HookProvider):
    def __init__(self, memory_client: MemoryClient, memory_id: str, last_k_turns: int = 5):
        self.memory_client = memory_client
        self.memory_id = memory_id
        self.last_k_turns = last_k_turns

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(AgentInitializedEvent, self.on_agent_initialized)
        registry.add_callback(MessageAddedEvent, self.on_message_added)

    def on_agent_initialized(self, event: AgentInitializedEvent) -> None:
        """Load the last k turns and prepend them to the system prompt."""
        actor_id = event.agent.state.get("actor_id")
        session_id = event.agent.state.get("session_id")
        if not actor_id or not session_id:
            return

        try:
            recent_turns = self.memory_client.get_last_k_turns(
                memory_id=self.memory_id,
                actor_id=actor_id,
                session_id=session_id,
                k=self.last_k_turns,
            )
        except Exception as exc:
            logger.error("Memory load error: %s", exc)
            return

        if not recent_turns:
            return

        context_messages = []
        for turn in recent_turns:
            for message in turn:
                role = message.get("role", "")
                content = message.get("content", {})
                text = content.get("text", "") if isinstance(content, dict) else str(content)
                context_messages.append(f"{role}: {text}")

        context = "\n".join(context_messages)
        event.agent.system_prompt += f"\n\nRecent conversation:\n{context}"
        logger.info("Loaded %d conversation turns", len(recent_turns))

    def on_message_added(self, event: MessageAddedEvent) -> None:
        actor_id = event.agent.state.get("actor_id")
        session_id = event.agent.state.get("session_id")
        if not actor_id or not session_id:
            return

        content = event.message.get("content", [])
        text = content[0].get("text") if content and isinstance(content[0], dict) else None
        if not text:
            return

        try:
            self.memory_client.create_event(
                memory_id=self.memory_id,
                actor_id=actor_id,
                session_id=session_id,
                messages=[(text, event.message.get("role", "").upper())],
            )
        except Exception as exc:
            logger.error("Memory save error: %s", exc)


@app.entrypoint
async def invoke(payload, context=None):
    user_message = payload.get("message", "Hello!")
    session_id = context.session_id
    actor_id = payload.get("actor_id", "wanderbot-user")

    if not MEMORY_ID:
        raise ValueError(
            "MEMORY_ID is empty. Create a memory resource with "
            "`agentcore memory create` and set AGENTCORE_MEMORY_ID."
        )

    memory_client = MemoryClient(region_name=REGION)

    agent = Agent(
        model=MODEL,
        system_prompt=SYSTEM_PROMPT,
        tools=[search_hotels],
        hooks=[ShortTermMemoryHookProvider(memory_client, MEMORY_ID)],
        state={"session_id": session_id, "actor_id": actor_id},
    )
    return agent(user_message)


if __name__ == "__main__":
    app.run()
