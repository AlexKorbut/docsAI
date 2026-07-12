"""Automatic document categorization: loan / utilities / medical / property / other."""

from app.config import get_settings
from app.llm.anthropic_client import LLMClient

CATEGORIES = ["loan", "utilities", "medical", "property", "other"]

SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": CATEGORIES},
        "title": {"type": "string"},
    },
    "required": ["category", "title"],
    "additionalProperties": False,
}

SYSTEM = """Classify the family document (often in Russian) into exactly one category:
loan (кредит), utilities (ЖКХ), medical (медицина), property (собственность/недвижимость),
or other. Also produce a short human-readable title for it (in the document's language)."""


def categorize(markdown: str, llm: LLMClient) -> tuple[str, str]:
    data = llm.complete_json(
        model=get_settings().extraction_model,
        system=SYSTEM,
        prompt=f"Document:\n\n{markdown[:8000]}",
        schema=SCHEMA,
    )
    return data["category"], data["title"]
