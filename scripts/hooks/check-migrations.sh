#!/bin/bash
# Pre-commit hook to warn if migrations SQL may need regeneration
#
# This hook runs when files in backend/app/database/models/ or
# backend/alembic/versions/ are modified.

MIGRATIONS_SQL="scripts/sql/migrations.sql"
MIGRATIONS_DIR="scripts/sql/migrations/"

# Check if migrations.sql or migrations/ directory files are also being committed
staged_migrations=$(git diff --cached --name-only | grep -E "^scripts/sql/migrations")

if [ -n "$staged_migrations" ]; then
    # migrations files are staged, all good
    exit 0
fi

# migrations files are NOT staged but model/migration files changed
echo ""
echo "WARNING: Database model or migration files changed but migrations SQL was not updated."
echo ""
echo "   Modified files:"
git diff --cached --name-only | grep -E "^(backend/app/database/models/|backend/alembic/versions/).*\.py$" | sed 's/^/     - /'
echo ""
echo "   To update migrations SQL, run:"
echo "     python scripts/generate/generate_migrations_sql.py"
echo ""
echo "   Then stage the updated files:"
echo "     git add scripts/sql/migrations.sql scripts/sql/migrations/ scripts/sql/migrations_manifest.json"
echo ""
echo "   Continuing with commit anyway..."
echo ""

# Exit 0 to allow commit (warning only, not blocking)
exit 0
