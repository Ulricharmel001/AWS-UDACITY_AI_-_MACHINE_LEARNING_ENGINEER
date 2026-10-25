#!/usr/bin/env python3
"""Drive a multi-turn bug-report conversation with the AgentCore harness and
capture the full transcript, including the [tool call] line and the returned
ticket id. This is evidence for resubmission.

    python run_bug_conversation.py
"""
import json
import sys
import uuid
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.eventstream import EventStream

CONFIG_PATH = Path("agentcore_config.json")


def event_stream(response):
    for value in response.values():
        if isinstance(value, EventStream):
            return value
    raise RuntimeError(f"No event stream in response: {list(response)}")


def invoke(rt, config, session_id, user_text):
    """Send one user message; return (final_text, tool_calls list)."""
    response = rt.invoke_harness(
        harnessArn=config["harness_arn"],
        runtimeSessionId=session_id,
        model={"bedrockModelConfig": {"modelId": config.get("model_id", "us.amazon.nova-pro-v1:0")}},
        tools=[{
            "type": "agentcore_gateway",
            "name": "support_gateway",
            "config": {"agentCoreGateway": {"gatewayArn": config["gateway_arn"]}},
        }],
        messages=[{"role": "user", "content": [{"text": user_text}]}],
    )

    texts = []
    buffer = []
    tool_calls = []
    for event in event_stream(response):
        if "contentBlockStart" in event:
            tool_use = event["contentBlockStart"].get("start", {}).get("toolUse")
            if tool_use:
                name = tool_use.get("name", "?")
                print(f"[tool call] {name}", flush=True)
                tool_calls.append(name)
        elif "contentBlockDelta" in event:
            delta = event["contentBlockDelta"].get("delta", {})
            if "text" in delta:
                print(delta["text"], end="", flush=True)
                buffer.append(delta["text"])
        elif "messageStop" in event:
            if buffer:
                texts.append("".join(buffer))
                buffer = []
    if buffer:
        texts.append("".join(buffer))
    print()
    return texts[-1] if texts else "", tool_calls


def main():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if "harness_arn" not in config:
        sys.exit("No harness in config yet — run create_harness.py first.")

    session_id = f"{uuid.uuid4()}-support-chat"
    rt = boto3.client(
        "bedrock-agentcore",
        region_name=config["region"],
        config=Config(read_timeout=300, retries={"max_attempts": 1}),
    )

    print(f"Connected to harness {config.get('harness_name', '?')} (session {session_id}).\n")

    turns = [
        # First message describes a bug but is missing details.
        "The website keeps crashing every time I try to checkout. I get a white screen.",
        # Provide the description/steps and more detail.
        "I add items to my cart, click Checkout, and the page goes white and freezes. It happens every time.",
        # Provide browser + OS.
        "I'm using Chrome on Windows 11.",
        # Provide device type.
        "I'm on a laptop computer.",
    ]

    for text in turns:
        print(f"you> {text}")
        print("bot> ", end="", flush=True)
        _, calls = invoke(rt, config, session_id, text)
        print("\n")


if __name__ == "__main__":
    main()
