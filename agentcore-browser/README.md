# AgentCore Browser

WanderBot uses Amazon Bedrock AgentCore Browser to read live content from Wikivoyage and answer destination questions.

## Files
- `starter.py` - Agent with `AgentCoreBrowser`, browser tool passed as `browser.browser`
- `requirements.txt` - dependencies

## How it works
1. `AgentCoreBrowser(region=...)` starts a managed headless Chromium session
2. The agent uses the browser tool to navigate to `https://en.wikivoyage.org/wiki/<Destination>`
3. The system prompt restricts browsing to `en.wikivoyage.org` only
4. The agent extracts specific info (neighbourhoods, highlights, etc.) instead of summarizing the whole page

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
