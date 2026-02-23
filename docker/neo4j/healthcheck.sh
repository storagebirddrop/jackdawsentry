#!/bin/bash
# Neo4j healthcheck script - avoids password exposure in docker healthcheck
# Usage: docker/neo4j/healthcheck.sh

# Exit immediately if command fails
set -e

# Check if NEO4J_PASSWORD is set
if [ -z "$NEO4J_PASSWORD" ]; then
    echo "Error: NEO4J_PASSWORD environment variable not set"
    exit 1
fi

# Run cypher-shell with password from environment variable
cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "RETURN 1"

echo "Neo4j healthcheck passed"
