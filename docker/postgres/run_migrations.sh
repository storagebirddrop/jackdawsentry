#!/bin/bash
# PostgreSQL migration runner script
# This script runs the SQL migrations from the migrations directory

echo "Running PostgreSQL migrations..."

# Find all SQL files in the migrations directory and run them in order
for migration_file in /docker-entrypoint-initdb.d/migrations/*.sql; do
    if [ -f "$migration_file" ]; then
        echo "Running migration: $(basename "$migration_file")"
        psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$migration_file"
    fi
done

echo "Migrations completed successfully!"