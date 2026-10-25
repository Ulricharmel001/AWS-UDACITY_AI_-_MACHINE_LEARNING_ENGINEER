#!/usr/bin/env python3
"""Run the three non-bug routing cases (FAQ covered, FAQ not covered, other
request) as separate harness conversations, one case per fresh session, and
print the responses. Evidence for the 'Platform Question' and 'Other Request'
rubric items.
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
                print(f"[tool call] {tool_use.get('name', '?')}", flush=True)
                tool_calls.append(tool_use.get("name"))
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


def run_case(label, message):
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    session_id = f"{uuid.uuid4()}-support-chat"
    rt = boto3.client(
        "bedrock-agentcore",
        region_name=config["region"],
        config=Config(read_timeout=300, retries={"max_attempts": 1}),
    )
    print("=" * 70)
    print(f"CASE: {label}")
    print("=" * 70)
    print(f"you> {message}")
    print("bot> ", end="", flush=True)
    invoke(rt, config, session_id, message)
    print()


if __name__ == "__main__":
    cases = [
        ("FAQ COVERED - return policy", "What is your return policy?"),
        ("FAQ COVERED - order tracking", "How do I track my order?"),
        ("FAQ NOT COVERED - cryptocurrency", "Can I use cryptocurrency to pay for my order?"),
        ("OTHER REQUEST - laptop recommendation", "Can you recommend a good laptop for video editing?"),
    ]
    for label, msg in cases:
        run_case(label, msg)
