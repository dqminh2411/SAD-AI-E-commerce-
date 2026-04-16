LOAD CSV WITH HEADERS FROM 'file:///fake_interactions.csv' AS row
WITH row, datetime(row.created_at) AS ts
MERGE (u:User {id: row.user_id})
WITH row, ts, u,
     CASE WHEN row.product_id IS NULL OR row.product_id = '' THEN null ELSE toInteger(row.product_id) END AS pid
OPTIONAL MATCH (p:Product {id: pid})
WITH row, ts, u, p

// SEARCHED -> Query
FOREACH (_ IN CASE WHEN row.event_type = 'search' AND row.query_text IS NOT NULL AND row.query_text <> '' THEN [1] ELSE [] END |
  MERGE (q:Query {text: row.query_text})
  MERGE (u)-[r:SEARCHED]->(q)
  ON CREATE SET r.cnt = 1, r.last_ts = ts, r.w = 1
  ON MATCH  SET r.cnt = coalesce(r.cnt, 0) + 1,
                r.last_ts = ts,
                r.w = coalesce(r.w, 0) + 1
)

// VIEWED -> Product (w += 1)
FOREACH (_ IN CASE WHEN row.event_type = 'view' AND p IS NOT NULL THEN [1] ELSE [] END |
  MERGE (u)-[r:VIEWED]->(p)
  ON CREATE SET r.cnt = 1, r.last_ts = ts, r.w = 1
  ON MATCH  SET r.cnt = coalesce(r.cnt, 0) + 1,
                r.last_ts = ts,
                r.w = coalesce(r.w, 0) + 1
)

// CARTED -> Product (w += 3)
FOREACH (_ IN CASE WHEN row.event_type = 'add_to_cart' AND p IS NOT NULL THEN [1] ELSE [] END |
  MERGE (u)-[r:CARTED]->(p)
  ON CREATE SET r.cnt = 1, r.last_ts = ts, r.w = 3
  ON MATCH  SET r.cnt = coalesce(r.cnt, 0) + 1,
                r.last_ts = ts,
                r.w = coalesce(r.w, 0) + 3
)

// PURCHASED -> Product (w += 10)
FOREACH (_ IN CASE WHEN row.event_type = 'purchase' AND p IS NOT NULL THEN [1] ELSE [] END |
  MERGE (u)-[r:PURCHASED]->(p)
  ON CREATE SET r.cnt = 1, r.last_ts = ts, r.w = 10
  ON MATCH  SET r.cnt = coalesce(r.cnt, 0) + 1,
                r.last_ts = ts,
                r.w = coalesce(r.w, 0) + 10
)

// CHATTED -> ChatMessage
FOREACH (_ IN CASE WHEN row.event_type = 'chat' AND row.query_text IS NOT NULL AND row.query_text <> '' THEN [1] ELSE [] END |
  MERGE (m:ChatMessage {id: row.event_id})
  SET m.text = row.query_text,
      m.page = row.page,
      m.product_type = row.product_type,
      m.ts = ts
  MERGE (u)-[:CHATTED {ts: ts}]->(m)
);
