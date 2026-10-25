import os
import time

from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager
from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies import (
    SemanticStrategy,
    UserPreferenceStrategy,
)

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
MEMORY_NAME = os.environ.get("MEMORY_NAME", "WanderBotLTM")


def main():
    memory_manager = MemoryManager(region_name=REGION)
    print(f"Creating memory resource '{MEMORY_NAME}' with SEMANTIC and USER_PREFERENCE strategies...")

    memory = memory_manager.get_or_create_memory(
        name=MEMORY_NAME,
        description="Horizon Travel WanderBot long-term memory",
        strategies=[
            SemanticStrategy(
                name="semanticLongTermMemory",
                namespaces=["/strategies/{memoryStrategyId}/actors/{actorId}/"],
            ),
            UserPreferenceStrategy(
                name="userPreferenceLongTermMemory",
                namespaces=["/strategies/{memoryStrategyId}/actors/{actorId}/"],
            ),
        ],
    )

    memory_id = memory.get("id") or memory.get("memoryId")
    print(f"MEMORY_ID={memory_id}")
    print("Set: export AGENTCORE_MEMORY_ID=" + str(memory_id))
    print("It may take a few minutes for strategies to be ACTIVE.")


if __name__ == "__main__":
    main()
