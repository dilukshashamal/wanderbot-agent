from starter import search_flights, search_hotels, get_exchange_rate
from strands_tools import current_time, calculator
from strands import Agent
from strands.models import BedrockModel

def test_all():
    print("Testing search_flights with IATA codes...")
    flights_iata = search_flights(origin="BCN", destination="FCO", date="2026-03-20")
    print(f"  Found {len(flights_iata)} flights:")
    for f in flights_iata:
        print(f"    - {f['airline']} {f['flight_number']}: {f['departure_time']}->{f['arrival_time']} (${f['price']})")
    assert len(flights_iata) >= 3, "Expected at least 3 flights for BCN->FCO on 2026-03-20"

    print("\nTesting search_flights with city names...")
    flights_city = search_flights(origin="Barcelona", destination="Rome", date="2026-03-20")
    print(f"  Found {len(flights_city)} flights")
    assert len(flights_city) == len(flights_iata), "City search should match IATA search count"

    print("\nTesting search_hotels with city name...")
    hotels_rome = search_hotels(city="Rome")
    print(f"  Found {len(hotels_rome)} hotels in Rome:")
    for h in hotels_rome:
        print(f"    - {h['name']} ({h['rating']} stars) - ${h['price_per_night']}/night")
    assert len(hotels_rome) >= 1, "Expected at least 1 hotel in Rome"

    print("\nTesting search_hotels with city code...")
    hotels_bcn = search_hotels(city="BCN")
    print(f"  Found {len(hotels_bcn)} hotels in BCN")
    assert len(hotels_bcn) >= 1, "Expected at least 1 hotel in BCN"

    print("\nTesting get_exchange_rate for EUR...")
    rate_eur = get_exchange_rate(to_currency="EUR")
    print(f"  Exchange rate EUR: {rate_eur}")
    assert rate_eur["exchange_rate"] == 0.92, f"Expected 0.92, got {rate_eur['exchange_rate']}"
    calc_500 = 500 * rate_eur["exchange_rate"]
    print(f"  $500 in EUR = {calc_500} EUR")

    print("\nTesting get_exchange_rate for JPY...")
    rate_jpy = get_exchange_rate(to_currency="JPY")
    print(f"  Exchange rate JPY: {rate_jpy}")
    assert rate_jpy["exchange_rate"] == 155.5, f"Expected 155.5, got {rate_jpy['exchange_rate']}"

    print("\nTesting current_time...")
    t = current_time.current_time()
    print(f"  Current time: {t}")
    assert t is not None

    print("\nTesting Strands Agent tool registration...")
    dummy_model = BedrockModel(model_id="us.amazon.nova-2-lite-v1:0")
    agent = Agent(
        model=dummy_model,
        tools=[calculator, current_time, search_flights, search_hotels, get_exchange_rate],
    )
    print(f"  Registered tool names: {agent.tool_names}")
    assert "calculator" in agent.tool_names
    assert "current_time" in agent.tool_names
    assert "search_flights" in agent.tool_names
    assert "search_hotels" in agent.tool_names
    assert "get_exchange_rate" in agent.tool_names

    print("\nALL LOCAL TOOL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_all()
