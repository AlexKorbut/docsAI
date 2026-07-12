"""Neo4j relationship graph: (Document)-[:MENTIONS]->(Entity), loan -> property -> payments.

Minimal writes for the starter; richer relationship queries are future work.
"""

import logging
from functools import lru_cache

from neo4j import GraphDatabase

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_driver():
    s = get_settings()
    return GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password))


def sync_document(document_id: int, title: str, category: str, entities: list[dict]) -> None:
    """Upsert a document node and its entity mentions. Best-effort: graph is auxiliary."""
    try:
        with get_driver().session() as session:
            session.run(
                "MERGE (d:Document {id: $id}) SET d.title = $title, d.category = $category",
                id=document_id,
                title=title,
                category=category,
            )
            for e in entities:
                session.run(
                    """
                    MERGE (n:Entity {kind: $kind, value: $value})
                    WITH n MATCH (d:Document {id: $id})
                    MERGE (d)-[:MENTIONS]->(n)
                    """,
                    kind=e["kind"],
                    value=e["value"],
                    id=document_id,
                )
    except Exception:
        logger.warning("Neo4j sync failed for document %s; continuing", document_id, exc_info=True)


def delete_document(document_id: int) -> None:
    """Remove a document node and its dangling entity mentions. Best-effort."""
    try:
        with get_driver().session() as session:
            session.run(
                "MATCH (d:Document {id: $id}) DETACH DELETE d",
                id=document_id,
            )
            session.run("MATCH (n:Entity) WHERE NOT (n)--() DELETE n")
    except Exception:
        logger.warning("Neo4j delete failed for document %s", document_id, exc_info=True)


# TODO: relationship queries (loan -> property -> payments traversals) for the Retriever agent.
