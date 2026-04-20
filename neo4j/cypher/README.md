- to import data into neo4j, you can use the following command in the terminal (do only once in the first time):
```bash
# start neo4j container
docker compose up -d neo4j
# copy data file into container
docker compose exec -T neo4j cypher-shell -u neo4j -p password -f /scripts/import_interactions_500u.cypher
```