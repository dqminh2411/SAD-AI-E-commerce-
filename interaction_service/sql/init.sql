CREATE TABLE IF NOT EXISTS interaction_events (
  event_id VARCHAR(64) PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  session_id VARCHAR(128) NULL,

  event_type VARCHAR(32) NOT NULL,

  product_id BIGINT NULL,
  query_text TEXT NULL,
  duration_ms BIGINT NULL,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  page VARCHAR(64) NULL,
  product_type VARCHAR(32) NULL,

  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

  neo4j_synced BOOLEAN NOT NULL DEFAULT FALSE,
  neo4j_synced_at TIMESTAMPTZ NULL,
  neo4j_error TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_interaction_events_user_created ON interaction_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_interaction_events_type_created ON interaction_events(event_type, created_at DESC);

\copy interaction_events(
  event_id,
  user_id,
  session_id,
  event_type,
  product_id,
  query_text,
  duration_ms,
  created_at,
  page,
  product_type
)
FROM '/docker-entrypoint-initdb.d/fake_interactions.csv'
WITH (FORMAT csv, HEADER true, NULL '');
