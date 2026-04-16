LOAD CSV WITH HEADERS FROM 'file:///product_nodes.csv' AS row
WITH row
WHERE row.product_id IS NOT NULL AND row.product_id <> ''
MERGE (b:Brand {id: toInteger(row.brand_id)})
SET b.name = row.brand_name
MERGE (p:Product {id: toInteger(row.product_id)})
SET p.product_type = row.product_type,
    p.name = row.name,
    p.base_price = toFloat(row.base_price),
    p.currency = row.currency,
    p.purpose = row.purpose
MERGE (p)-[:BRANDED_BY]->(b);
