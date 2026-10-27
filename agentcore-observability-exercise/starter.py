import json
import os
from pathlib import Path

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.models import BedrockModel

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
MODEL_ID = os.environ.get("MODEL_ID", "us.amazon.nova-2-lite-v1:0")

DATA_DIR = Path(__file__).parent / "data"

app = BedrockAgentCoreApp()
model = BedrockModel(model_id=MODEL_ID)

SYSTEM_PROMPT = """\
You are WanderBot, a friendly travel assistant for Horizon Travel.

Use the search_flights tool when asked about flights between cities.
Use the search_hotels tool when asked about hotels in a city.
Keep your answers short and practical.
"""


@tool
def search_flights(origin: str, destination: str) -> str:
    """Search available flights between two cities."""
    flights = json.loads((DATA_DIR / "flights.json").read_text())
    matches = [
        f
        for f in flights
        if f.get("origin", "").upper() == origin.upper()
        and f.get("destination", "").upper() == destination.upper()
        and f.get("status") != "CANCELLED"
    ]
    if not matches:
        return f"No flights found from {origin} to {destination}."
    return json.dumps(matches[:5], indent=2)


@tool
def search_hotels(city: str, max_price: float = 500.0) -> str:
    """Search available hotels in a city with an optional maximum price."""
    hotels = json.loads((DATA_DIR / "hotels.json").read_text())
    matches = [
        h
        for h in hotels
        if h.get("location", "").lower() == city.lower()
        and h.get("available", True)
        and h.get("price_per_night_usd", 0) <= max_price
    ]
    if not matches:
        return f"No hotels found in {city} under ${max_price}/night."
    return json.dumps(matches[:5], indent=2)


@app.entrypoint
async def invoke(payload: dict, context=None) -> dict:
    user_message = payload.get("message", "Hello!")
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[search_flights, search_hotels],
    )
    return agent(user_message)


if __name__ == "__main__":
    app.run()
