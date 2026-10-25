# AgentCore Browser

Gives a Strands agent access to AgentCore's managed headless Chromium browser to pull live info from Wikivoyage.

## Files
- `starter.py` - `BedrockAgentCoreApp` + `Agent` with `AgentCoreBrowser`. Tool passed as `browser.browser`
- `requirements.txt` - dependencies

## How it works
- `AgentCoreBrowser(region=REGION)` creates a managed browser session
- System prompt forces the agent to only browse `https://en.wikivoyage.org` and use `https://en.wikivoyage.org/wiki/<Destination>`
- Agent extracts specific fields (neighbourhoods, highlights, safety) rather than dumping the whole page
- `tools=[browser.browser]` (not the `AgentCoreBrowser` instance)

## Run locally
```bash
pip install -r requirements.txt
python starter.py
```

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"message": "What neighbourhoods should I stay in when visiting Tokyo?"}'
```
