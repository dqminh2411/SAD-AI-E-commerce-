import os

from neo4j import GraphDatabase


_NEO4J_DRIVER = None


def _get_driver():
    global _NEO4J_DRIVER
    if _NEO4J_DRIVER is not None:
        return _NEO4J_DRIVER

    uri = os.getenv('NEO4J_URI', 'bolt://neo4j:7687')
    user = os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', 'password')

    _NEO4J_DRIVER = GraphDatabase.driver(uri, auth=(user, password))
    return _NEO4J_DRIVER


UPSERT_EVENT_CYPHER = """
MERGE (u:User {id: $user_id})
WITH u, $event_type AS et,
     $product_id AS pid,
     $query_text AS qt,
     $event_id AS eid,
     $page AS page,
     $product_type AS pt,
     datetime($created_at) AS ts

// Ensure Product node exists for product-related events.
CALL {
  WITH pid, pt
  WITH pid, pt WHERE pid IS NOT NULL
  MERGE (p:Product {id: pid})
  ON CREATE SET p.product_type = pt
  RETURN p
  UNION
  WITH pid, pt
  WITH pid, pt WHERE pid IS NULL
  RETURN null AS p
}
WITH u, et, pid, qt, eid, page, pt, ts, p

// SEARCHED -> Query
FOREACH (_ IN CASE WHEN et = 'search' AND qt IS NOT NULL AND qt <> '' THEN [1] ELSE [] END |
  MERGE (q:Query {text: qt})
  MERGE (u)-[r:SEARCHED]->(q)
  ON CREATE SET r.cnt = 1, r.last_ts = ts, r.w = 1
  ON MATCH  SET r.cnt = coalesce(r.cnt, 0) + 1,
                r.last_ts = ts,
                r.w = coalesce(r.w, 0) + 1
)

// VIEWED -> Product (w += 1)
FOREACH (_ IN CASE WHEN et = 'view' AND p IS NOT NULL THEN [1] ELSE [] END |
  MERGE (u)-[r:VIEWED]->(p)
  ON CREATE SET r.cnt = 1, r.last_ts = ts, r.w = 1
  ON MATCH  SET r.cnt = coalesce(r.cnt, 0) + 1,
                r.last_ts = ts,
                r.w = coalesce(r.w, 0) + 1
)

// CARTED -> Product (w += 3)
FOREACH (_ IN CASE WHEN et = 'add_to_cart' AND p IS NOT NULL THEN [1] ELSE [] END |
  MERGE (u)-[r:CARTED]->(p)
  ON CREATE SET r.cnt = 1, r.last_ts = ts, r.w = 3
  ON MATCH  SET r.cnt = coalesce(r.cnt, 0) + 1,
                r.last_ts = ts,
                r.w = coalesce(r.w, 0) + 3
)

// PURCHASED -> Product (w += 10)
FOREACH (_ IN CASE WHEN et = 'purchase' AND p IS NOT NULL THEN [1] ELSE [] END |
  MERGE (u)-[r:PURCHASED]->(p)
  ON CREATE SET r.cnt = 1, r.last_ts = ts, r.w = 10
  ON MATCH  SET r.cnt = coalesce(r.cnt, 0) + 1,
                r.last_ts = ts,
                r.w = coalesce(r.w, 0) + 10
)

// CHATTED -> ChatMessage
FOREACH (_ IN CASE WHEN et = 'chat' AND qt IS NOT NULL AND qt <> '' THEN [1] ELSE [] END |
  MERGE (m:ChatMessage {id: eid})
  SET m.text = qt,
      m.page = page,
      m.product_type = pt,
      m.ts = ts
  MERGE (u)-[:CHATTED {ts: ts}]->(m)
);
"""


def upsert_event_to_neo4j(*, event_id: str, user_id: str, session_id: str | None, event_type: str,
                         product_id: int | None, query_text: str | None, created_at_iso: str,
                         page: str | None, product_type: str | None):
    driver = _get_driver()
    with driver.session() as session:
        session.run(
            UPSERT_EVENT_CYPHER,
            user_id=user_id,
            event_type=event_type,
            product_id=product_id,
            query_text=query_text,
            event_id=event_id,
            page=page,
            product_type=product_type,
            created_at=created_at_iso,
        )
