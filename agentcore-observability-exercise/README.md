# AgentCore Native Observability

## Files
- `starter.py`
- `requirements.txt`
- `data/flights.json`
- `data/hotels.json`

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
  -d '{"message": "Find flights from London to Tokyo"}'

curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"message": "Hotels in Tokyo under $200/night"}'
```

## Deploy to AWS AgentCore
```bash
agentcore configure -e starter.py -n WanderBot -dt container -rf requirements.txt --disable-memory
agentcore deploy
```

## Test
```bash
# Session 1
agentcore invoke '{"message": "Find flights from London to Tokyo"}'
agentcore invoke '{"message": "Hotels in Tokyo under $200/night"}'

agentcore stop-session

# Session 2
agentcore invoke '{"message": "Flights from New York to Rome"}'
```

## View traces
CloudWatch → GenAI Observability → Bedrock AgentCore. Look at Sessions, Traces, tool spans (`search_flights`, `search_hotels`), model/tokens, and errors.
