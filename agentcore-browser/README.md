# AgentCore Browser — WanderBot

Horizon Travel wants **WanderBot** to answer destination questions with live
content from [Wikivoyage](https://en.wikivoyage.org) instead of a stale policy
document. This demo gives a Strands agent access to an Amazon Bedrock
**AgentCore Browser** so it can open `en.wikivoyage.org/wiki/<Destination>` and
summarise what it finds.

## Files

| File | Purpose |
|------|---------|
| `starter.py` | The agent: a Strands `Agent` wired to `AgentCoreBrowser` and served by `BedrockAgentCoreApp`. |
| `requirements.txt` | Python dependencies for local dev and deployment. |

## How it works

- `AgentCoreBrowser(region=...)` starts a **managed headless Chromium** session
  in AgentCore. Cold start is typically a few seconds on the first call.
- The browser tool is added with `tools=[browser.browser]` — pass the inner
  `browser` tool, **not** the `AgentCoreBrowser` instance. Mixing these up is the
  most common bug.
- The system prompt pins browsing to `https://en.wikivoyage.org` only, which
  limits the blast radius of prompt injection.
- The agent is told to **extract specific fields** (neighbourhoods, highlights,
  best time to visit) rather than summarise the whole page — extraction prompts
  are more reliable and use fewer output tokens.
- The endpoint accepts `{"message": "..."}` and returns the agent's reply.

## Configuration

| Variable | Default | Meaning |
|----------|---------|---------|
| `AWS_DEFAULT_REGION` | `us-east-1` | Region for the model and browser. |
| `WANDERBOT_MODEL` | `us.amazon.nova-pro-v1:0` | Bedrock model id. |

Make sure AWS credentials are valid (`aws sts get-caller-identity`) and the
model is enabled in the chosen region before deploying.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python starter.py
```

Then in another terminal:

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"message": "What neighbourhoods should I stay in when visiting Tokyo?"}'
```

## Deploy to AgentCore Runtime

```bash
agentcore configure -e starter.py -n WanderBot -dt container \
  -rf requirements.txt --disable-memory --non-interactive
agentcore deploy
agentcore invoke '{"message": "Give me a brief travel overview of Barcelona."}'
```

While a call is running, open **AWS Console → Amazon Bedrock → AgentCore →
Browser → Sessions** and click into the active session to watch the Live View.

## Example prompts

- `What neighbourhoods should I stay in when visiting Tokyo?`
- `Give me a brief travel overview of Barcelona.`
