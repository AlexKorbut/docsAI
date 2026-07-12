"""LLM entity extraction: dates, amounts, names, addresses, contract numbers, payments."""

from app.config import get_settings
from app.llm.anthropic_client import LLMClient
from app.schemas import ExtractedEntity, ExtractedPayment

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": [
                            "date",
                            "amount",
                            "person",
                            "address",
                            "contract_number",
                            "doctor",
                            "diagnosis",
                            "medication",
                            "clinic",
                            "appliance",
                        ],
                    },
                    "value": {"type": "string"},
                    "normalized": {"type": ["string", "null"]},
                },
                "required": ["kind", "value", "normalized"],
                "additionalProperties": False,
            },
        },
        "payments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    "currency": {"type": "string"},
                    "due_date": {"type": ["string", "null"], "format": "date"},
                    "description": {"type": ["string", "null"]},
                },
                "required": ["amount", "currency", "due_date", "description"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["entities", "payments"],
    "additionalProperties": False,
}

SYSTEM = """You extract structured facts from family documents (loans, utilities,
medical records, property, household paperwork), often in Russian. Extract entities
exactly as written, with a normalized form where applicable (ISO dates, plain decimal
amounts). For medical documents also extract doctors, diagnoses, medications, and
clinics; for household documents — appliances/devices (warranties, manuals). Extract
every payment obligation (amount + due date) into `payments`. Never invent values
that are not present in the document."""


def extract(markdown: str, llm: LLMClient) -> tuple[list[ExtractedEntity], list[ExtractedPayment]]:
    data = llm.complete_json(
        model=get_settings().extraction_model,
        system=SYSTEM,
        prompt=f"Document:\n\n{markdown[:30000]}",
        schema=EXTRACTION_SCHEMA,
    )
    entities = [ExtractedEntity(**e) for e in data.get("entities", [])]
    payments = [ExtractedPayment(**p) for p in data.get("payments", [])]
    return entities, payments
