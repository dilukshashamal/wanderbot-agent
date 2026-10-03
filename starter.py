import json
from pathlib import Path
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.hooks import (
    AgentInitializedEvent,
    HookProvider,
    HookRegistry,
    MessageAddedEvent,
)
from strands.models import BedrockModel
from strands_tools import calculator, current_time

app = BedrockAgentCoreApp()
REGION = "us-east-1"
MEMORY_ID = "WanderBot-jIy3mvHQUb"
model = BedrockModel(model_id="us.amazon.nova-2-lite-v1:0")

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"


def _load_dataset(filename: str):
    """Load a JSON dataset file from the datasets directory."""
    file_path = DATASETS_DIR / filename
    if not file_path.exists():
        file_path = Path("datasets") / filename
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


@tool
def search_flights(origin: str, destination: str, date: str | None = None) -> list[dict]:
    """Search for available flights based on origin airport, destination airport, and departure date.

    Args:
        origin: 3-letter IATA airport code (e.g., 'BCN') or origin city name (e.g., 'Barcelona').
        destination: 3-letter IATA airport code (e.g., 'FCO') or destination city name (e.g., 'Rome').
        date: Departure date in YYYY-MM-DD format (e.g., '2026-03-20'). Optional.

    Returns:
        A list of matching flight records with flight number, airline, departure/arrival times, price, and status.
    """
    flights = _load_dataset("flights.json")
    results = []
    origin_clean = origin.strip().lower()
    dest_clean = destination.strip().lower()
    date_clean = date.strip() if date else None

    for flight in flights:
        match_origin = (
            flight.get("origin", "").lower() == origin_clean
            or flight.get("origin_city", "").lower() == origin_clean
        )
        match_destination = (
            flight.get("destination", "").lower() == dest_clean
            or flight.get("destination_city", "").lower() == dest_clean
        )
        match_date = True
        if date_clean:
            match_date = (
                flight.get("date") == date_clean
                or flight.get("departure_date") == date_clean
            )

        if match_origin and match_destination and match_date:
            results.append(flight)

    return results


@tool
def search_hotels(city: str) -> list[dict]:
    """Search for hotel accommodations in a destination city.

    Args:
        city: Destination city name (e.g., 'Rome', 'Barcelona', 'Paris', 'Tokyo') or 3-letter IATA code (e.g., 'FCO', 'BCN').

    Returns:
        A list of hotels with hotel name, star rating, nightly price in USD, amenities, and location address.
    """
    hotels = _load_dataset("hotels.json")
    results = []
    city_clean = city.strip().lower()

    for hotel in hotels:
        if (
            hotel.get("city", "").lower() == city_clean
            or hotel.get("city_code", "").lower() == city_clean
        ):
            results.append(hotel)

    return results


@tool
def get_exchange_rate(to_currency: str, from_currency: str = "USD") -> dict:
    """Get the currency exchange rate between two currencies.

    Args:
        to_currency: 3-letter target currency code (e.g., 'EUR', 'GBP', 'JPY').
        from_currency: 3-letter base currency code (e.g., 'USD'). Defaults to 'USD'.

    Returns:
        A dictionary containing base currency, target currency, and exchange rate relative to the base currency.
    """
    data = _load_dataset("exchange_rates.json")
    rates = data.get("rates", data)

    from_curr = from_currency.strip().upper()
    to_curr = to_currency.strip().upper()

    from_rate = 1.0 if from_curr == "USD" else rates.get(from_curr)
    to_rate = 1.0 if to_curr == "USD" else rates.get(to_curr)

    if from_rate is None:
        return {"error": f"Base currency '{from_curr}' not found in exchange rates."}
    if to_rate is None:
        return {"error": f"Target currency '{to_curr}' not found in exchange rates."}

    rate = round(to_rate / from_rate, 4)
    return {
        "base_currency": from_curr,
        "target_currency": to_curr,
        "exchange_rate": rate,
    }


SYSTEM_PROMPT = """You are WanderBot, the official AI travel assistant for Horizon Travel.
You help travellers search flights, discover hotels, check exchange rates, and plan itineraries.
Follow these guidelines:
- When asked about flight availability or schedules, use the search_flights tool with 3-letter IATA codes (e.g., BCN, FCO) or city names, and dates in YYYY-MM-DD format.
- When asked for hotel recommendations or accommodations, use the search_hotels tool.
- When asked to convert currencies or check exchange rates, use the get_exchange_rate tool.
- If the user asks for relative dates (such as 'today', 'tomorrow', 'next week') or you need the current date/time to resolve queries, call the current_time tool.
- When asked to calculate costs, totals, conversions, split budgets, or any numeric values, always use the calculator tool for accuracy.
"""


class ShortTermMemoryHookProvider(HookProvider):
    def __init__(self, memory_client: MemoryClient, memory_id: str, last_k_turns: int = 5):
        self.memory_client = memory_client
        self.memory_id = memory_id
        self.last_k_turns = last_k_turns

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(AgentInitializedEvent, self.on_agent_initialized)
        registry.add_callback(MessageAddedEvent, self.on_message_added)

    def on_agent_initialized(self, event: AgentInitializedEvent) -> None:
        actor_id = event.agent.state.get("actor_id")
        session_id = event.agent.state.get("session_id")
        if not actor_id or not session_id:
            return

        try:
            turns = self.memory_client.get_last_k_turns(
                memory_id=self.memory_id,
                actor_id=actor_id,
                session_id=session_id,
                k=self.last_k_turns,
            )
            if not turns:
                return

            for turn in reversed(turns):
                for msg in turn:
                    role = msg.get("role", "").lower()
                    text = msg.get("content", {}).get("text", "")
                    if role and text:
                        event.agent.messages.append({
                            "role": role,
                            "content": [{"text": text}],
                        })
        except Exception:
            pass

    def on_message_added(self, event: MessageAddedEvent) -> None:
        actor_id = event.agent.state.get("actor_id")
        session_id = event.agent.state.get("session_id")
        if not actor_id or not session_id:
            return

        content = event.message.get("content", [])
        text = content[0].get("text") if content and isinstance(content[0], dict) else None
        if not text:
            return

        self.memory_client.create_event(
            memory_id=self.memory_id,
            actor_id=actor_id,
            session_id=session_id,
            messages=[(text, event.message.get("role", "").upper())],
        )


@app.entrypoint
async def invoke(payload: dict, context=None):
    user_message = payload.get("message") or payload.get("prompt") or "Hello!"
    session_id = getattr(context, "session_id", None) or payload.get("session_id", "wanderbot-session")
    actor_id = payload.get("actor_id", "wanderbot-user")

    memory_client = MemoryClient(region_name=REGION)

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[calculator, current_time, search_flights, search_hotels, get_exchange_rate],
        hooks=[ShortTermMemoryHookProvider(memory_client, MEMORY_ID)],
        state={"session_id": session_id, "actor_id": actor_id},
    )
    return agent(user_message)


if __name__ == "__main__":
    app.run()