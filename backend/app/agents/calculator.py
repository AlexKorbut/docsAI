"""Calculator: deterministic arithmetic over structured facts.

Numbers are summed in Python, never by the LLM. Starter scope: totals per currency.
TODO: sandboxed code-executor tool for arbitrary calculations (payment schedules,
remaining balances, amortization).
"""

from collections import defaultdict
from decimal import Decimal

from app.agents.state import AgentState, Services


def calculate(state: AgentState, services: Services) -> AgentState:
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for fact in state.get("structured_facts", []):
        if fact.get("amount") is not None:
            totals[fact.get("currency", "RUB")] += Decimal(str(fact["amount"]))
    calculations = [f"Sum of recorded payments: {amount} {cur}" for cur, amount in totals.items()]
    services.audit(state["query_id"], "calculator", {"calculations": calculations})
    return {"calculations": calculations}
