# Code Interpreter

Run Python in an isolated AgentCore sandbox to do accurate trip/cost calculations.

## Files
- `starter.py`
- `requirements.txt`

## Install
```bash
pip install -r requirements.txt
```

## Run locally
```bash
python starter.py
```

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"message": "Calculate the total cost for 3 nights in Tokyo at $150/night plus 10% tax."}'
```

## Deploy to AWS AgentCore
```bash
agentcore configure -e starter.py -n WanderBotCode -dt container -rf requirements.txt
agentcore deploy
agentcore invoke '{"message": "Calculate the total cost for 3 nights in Tokyo at $150/night plus 10% tax."}'
agentcore invoke '{"message": "How many nights between 2025-10-01 and 2025-10-08?"}'
```

## Notes
- Uses `code_session(REGION)` with `clearContext: True` for isolation between calls
- Agent must `print()` the result; the tool returns the streamed result as JSON
- Sandbox has no network; inject values into the code
- Warm-up can take a few seconds on first call
