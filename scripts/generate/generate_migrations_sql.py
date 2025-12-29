#!/usr/bin/env python3
"""
Generate SQL from Alembic migrations for Snowflake Native App and local development.

This script reads all Alembic migration files and generates:
1. Individual SQL files per migration in scripts/sql/migrations/
2. A combined migrations.sql for Native App (uses app_data schema)
3. A local_migrations.sql for local development (uses custom schema)

Each migration file uses idempotent SQL (IF NOT EXISTS, IF EXISTS) to support
incremental upgrades for consumers who already have the app installed.

Usage:
    # For Native App only (default)
    python scripts/generate/generate_migrations_sql.py

    # For local development with custom schema
    python scripts/generate/generate_migrations_sql.py --schema MY_SCHEMA

Output:
    scripts/sql/migrations/              - Directory with individual migration SQL files
    scripts/sql/migrations.sql           - Combined SQL file for Native App
    scripts/sql/migrations_manifest.json - Manifest with migration metadata
    scripts/generated/local_migrations.sql - SQL file for local development (if --schema provided)
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Add backend to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # scripts/generate -> scripts -> project root
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

ALEMBIC_VERSIONS_DIR = BACKEND_DIR / "alembic" / "versions"
SCRIPTS_DIR = SCRIPT_DIR.parent  # scripts/generate -> scripts
OUTPUT_DIR = SCRIPTS_DIR / "sql" / "migrations"
OUTPUT_FILE = SCRIPTS_DIR / "sql" / "migrations.sql"
MANIFEST_FILE = SCRIPTS_DIR / "sql" / "migrations_manifest.json"
LOCAL_MIGRATIONS_FILE = SCRIPTS_DIR / "generated" / "local_migrations.sql"


def parse_migration_file(filepath: Path) -> dict:
    """Parse an Alembic migration file and extract metadata and SQL operations."""
    content = filepath.read_text()

    # Extract revision ID (handles both "revision = '...'" and "revision: str = '...'")
    revision_match = re.search(r"^revision(?::\s*str)?\s*=\s*['\"]([^'\"]+)['\"]", content, re.MULTILINE)
    revision = revision_match.group(1) if revision_match else None

    # Extract down_revision
    down_revision_match = re.search(r"down_revision\s*=\s*(['\"]([^'\"]+)['\"]|None)", content)
    if down_revision_match:
        down_revision_str = down_revision_match.group(1)
        if down_revision_str == "None":
            down_revision = None
        else:
            down_revision = down_revision_str.strip("'\"")
    else:
        down_revision = None

    # Extract message from docstring (first line after triple quotes)
    docstring_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
    if docstring_match:
        docstring_content = docstring_match.group(1).strip()
        message = docstring_content.splitlines()[0].strip() if docstring_content else "Unknown migration"
    else:
        message = "Unknown migration"

    # Create a slug from the message for filename
    slug = re.sub(r'[^a-z0-9]+', '_', message.lower()).strip('_')[:50]

    return {
        "filepath": filepath,
        "revision": revision,
        "down_revision": down_revision,
        "message": message,
        "slug": slug,
        "content": content
    }


def get_ordered_migrations(migrations: list) -> list:
    """Order migrations from oldest to newest based on dependencies."""
    by_revision = {m["revision"]: m for m in migrations}

    # Find root migrations (no down_revision)
    roots = [m for m in migrations if m["down_revision"] is None]
    if not roots:
        print("Warning: No root migration found")
        return migrations

    ordered = []
    visited = set()

    def visit(migration):
        if migration["revision"] in visited:
            return
        if migration["down_revision"]:
            parent = by_revision.get(migration["down_revision"])
            if parent:
                visit(parent)
        ordered.append(migration)
        visited.add(migration["revision"])

    for m in migrations:
        visit(m)

    # Remove duplicates while preserving order
    seen = set()
    ordered_unique = []
    for m in ordered:
        if m["revision"] not in seen:
            ordered_unique.append(m)
            seen.add(m["revision"])

    return ordered_unique


def find_balanced_parens(text: str, start_pos: int) -> int:
    """Find the position of the closing parenthesis that matches the opening one at start_pos."""
    if text[start_pos] != '(':
        return -1

    depth = 0
    for i in range(start_pos, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return i
    return -1


def extract_upgrade_sql(migration: dict, use_idempotent: bool = True) -> list:
    """Extract SQL statements from the upgrade() function of a migration.

    Args:
        migration: Migration dict with content
        use_idempotent: If True, generate idempotent SQL (ADD COLUMN IF NOT EXISTS)
    """
    content = migration["content"]

    # Find the upgrade function body (handles optional return type annotation)
    # Stop at def downgrade or end of file
    upgrade_match = re.search(
        r"def upgrade\(\)(?:\s*->\s*None)?:\s*\n(.*?)(?=\ndef downgrade|\Z)",
        content,
        re.DOTALL
    )
    if not upgrade_match:
        return []

    upgrade_body = upgrade_match.group(1)

    sql_statements = []

    # Handle op.create_table calls
    pos = 0
    while True:
        match = re.search(r"op\.create_table\(\s*['\"]([^'\"]+)['\"]", upgrade_body[pos:])
        if not match:
            break
        table_name = match.group(1)
        start_idx = pos + match.start()
        paren_start = upgrade_body.find('(', start_idx)
        if paren_start == -1:
            break
        paren_end = find_balanced_parens(upgrade_body, paren_start)
        if paren_end == -1:
            break
        full_content = upgrade_body[paren_start + 1:paren_end]
        sql = generate_create_table_sql(table_name, full_content)
        if sql:
            sql_statements.append(sql)
        pos = paren_end + 1

    # Handle op.create_index calls
    for index_match in re.finditer(
        r"op\.create_index\(\s*['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"],\s*(\[[^\]]+\])",
        upgrade_body
    ):
        index_name = index_match.group(1)
        table_name = index_match.group(2)
        columns_list_str = index_match.group(3)
        # Extract columns inside list
        columns = [c.strip().strip("'\"") for c in re.findall(r"['\"]([^'\"]+)['\"]", columns_list_str)]
        sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON app_data.{table_name} ({', '.join(columns)});"
        sql_statements.append(sql)

    # Handle op.add_column calls - use IF NOT EXISTS for idempotent upgrades
    for addcol_match in re.finditer(
        r"op\.add_column\(\s*['\"]([^'\"]+)['\"],\s*sa\.Column\((.*?)\)\s*\)",
        upgrade_body, re.DOTALL
    ):
        table_name = addcol_match.group(1)
        column_content = addcol_match.group(2)
        col_def = parse_column_content(column_content)
        if not col_def:
            continue
        col_name = col_def["name"]
        col_type = map_sqlalchemy_to_snowflake(col_def["type"])
        col_options = col_def["options"]

        nullable = "nullable=False" not in col_options
        unique = "unique=True" in col_options
        default_value = extract_default_value(col_options)

        # Use IF NOT EXISTS for idempotent upgrades
        if_not_exists = "IF NOT EXISTS " if use_idempotent else ""
        parts = [f"ALTER TABLE app_data.{table_name} ADD COLUMN {if_not_exists}{col_name} {col_type}"]
        if not nullable:
            parts.append("NOT NULL")
        if unique:
            parts.append("UNIQUE")
        if default_value is not None:
            parts.append(f"DEFAULT {default_value}")
        sql_statements.append(" ".join(parts) + ";")

    # Handle op.drop_column calls
    for dropcol_match in re.finditer(
        r"op\.drop_column\(\s*['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"]",
        upgrade_body
    ):
        table_name = dropcol_match.group(1)
        col_name = dropcol_match.group(2)
        if_exists = "IF EXISTS " if use_idempotent else ""
        sql = f"ALTER TABLE app_data.{table_name} DROP COLUMN {if_exists}{col_name};"
        sql_statements.append(sql)

    # Handle op.create_foreign_key calls
    for fk_match in re.finditer(
        r"op\.create_foreign_key\(\s*['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"],\s*\[([^\]]+)\],\s*\[([^\]]+)\]",
        upgrade_body, re.DOTALL
    ):
        fk_name = fk_match.group(1)
        source_table = fk_match.group(2)
        referent_table = fk_match.group(3)
        local_cols_str = fk_match.group(4)
        remote_cols_str = fk_match.group(5)
        local_cols = [c.strip().strip("'\"") for c in local_cols_str.split(",")]
        remote_cols = [c.strip().strip("'\"") for c in remote_cols_str.split(",")]
        sql = (f"ALTER TABLE app_data.{source_table} ADD CONSTRAINT {fk_name} FOREIGN KEY ({', '.join(local_cols)}) "
               f"REFERENCES app_data.{referent_table} ({', '.join(remote_cols)});")
        sql_statements.append(sql)

    # Handle op.drop_table calls
    for droptable_match in re.finditer(
        r"op\.drop_table\(\s*['\"]([^'\"]+)['\"]",
        upgrade_body
    ):
        table_name = droptable_match.group(1)
        if_exists = "IF EXISTS " if use_idempotent else ""
        sql = f"DROP TABLE {if_exists}app_data.{table_name};"
        sql_statements.append(sql)

    # Handle op.drop_index calls
    for dropindex_match in re.finditer(
        r"op\.drop_index\(\s*['\"]([^'\"]+)['\"],\s*table_name\s*=\s*['\"]([^'\"]+)['\"]",
        upgrade_body
    ):
        index_name = dropindex_match.group(1)
        table_name = dropindex_match.group(2)
        if_exists = "IF EXISTS " if use_idempotent else ""
        sql = f"DROP INDEX {if_exists}{index_name};"
        sql_statements.append(sql)

    return sql_statements


def extract_column_calls(columns_str: str) -> list:
    """Extract all sa.Column(...) calls handling nested parentheses."""
    columns = []
    pos = 0

    while True:
        match = re.search(r"sa\.Column\(", columns_str[pos:])
        if not match:
            break
        start_idx = pos + match.start()
        paren_start = columns_str.find('(', start_idx)
        if paren_start == -1:
            break
        paren_end = find_balanced_parens(columns_str, paren_start)
        if paren_end == -1:
            break
        col_content = columns_str[paren_start + 1:paren_end]
        columns.append(col_content)
        pos = paren_end + 1

    return columns


def parse_column_content(col_content: str) -> dict:
    """Parse the content of a single sa.Column() call."""
    # First argument is column name (quoted string)
    name_match = re.match(r"\s*['\"]([^'\"]+)['\"]", col_content)
    if not name_match:
        return None

    col_name = name_match.group(1)
    rest = col_content[name_match.end():]

    # Skip comma after name
    rest = rest.lstrip(", \t\n")

    # Find the type (next argument before comma or keyword arg)
    # Types can be: sa.String(36), sa.Text(), VARIANT(), etc.
    type_match = re.match(r"([a-zA-Z_.]+(?:\([^()]*\))?)", rest)
    col_type = type_match.group(1) if type_match else "VARCHAR"

    # Rest contains options
    options = rest[type_match.end():] if type_match else rest

    return {
        "name": col_name,
        "type": col_type,
        "options": options
    }


def extract_default_value(options_str: str):
    """Extract server_default value from options string, properly formatted for SQL."""
    # SQL functions that should not be quoted (Snowflake built-in functions)
    SQL_FUNCTIONS = {
        'CURRENT_TIMESTAMP', 'CURRENT_DATE', 'CURRENT_TIME',
        'SYSDATE', 'GETDATE', 'NOW',
        'UUID_STRING', 'SEQ1', 'SEQ2', 'SEQ4', 'SEQ8',
    }

    # Try to find server_default=sa.text('...') or server_default='...' or server_default=True/False
    default_match = re.search(
        r"server_default\s*=\s*(sa\.text\(\s*['\"]([^'\"]+)['\"]\s*\)|['\"]([^'\"]+)['\"]|True|False|None)",
        options_str, re.IGNORECASE)
    if not default_match:
        return None
    val = default_match.group(2) or default_match.group(3) or default_match.group(0)
    val = val.strip()
    # Handle sa.text('...') case
    if val.startswith("sa.text"):
        inner_match = re.search(r"sa\.text\(\s*['\"]([^'\"]+)['\"]\s*\)", val)
        if inner_match:
            return inner_match.group(1)
        return None
    # Handle True/False/None directly
    if val.lower() == "true":
        return "TRUE"
    if val.lower() == "false":
        return "FALSE"
    if val.lower() == "none":
        return None
    # If val looks like a function call (ends with ()), return as is
    if val.endswith("()"):
        return val
    # If val is a known SQL function (without parentheses), return as-is
    if val.upper() in SQL_FUNCTIONS:
        return val.upper()
    # If val is numeric, return as is
    if re.fullmatch(r"[-+]?\d+(\.\d+)?", val):
        return val
    # Otherwise, quote string literal
    return f"'{val}'"


def generate_create_table_sql(table_name: str, columns_str: str) -> str:
    """Generate CREATE TABLE SQL from parsed column definitions."""
    columns = []
    primary_keys = []
    unique_columns = set()
    foreign_keys = []

    # Extract all sa.Column calls
    col_calls = extract_column_calls(columns_str)

    # Parse PrimaryKeyConstraint and UniqueConstraint
    pk_constraint_match = re.search(r"sa\.PrimaryKeyConstraint\(([^)]+)\)", columns_str)
    unique_constraint_matches = re.findall(r"sa\.UniqueConstraint\(([^)]+)\)", columns_str)
    fk_constraint_matches = re.findall(r"sa\.ForeignKeyConstraint\(\[([^\]]+)\],\s*\[([^\]]+)\]", columns_str)

    for col_content in col_calls:
        parsed = parse_column_content(col_content)
        if not parsed:
            continue

        col_name = parsed["name"]
        col_type_raw = parsed["type"]
        col_options = parsed["options"]

        # Map SQLAlchemy types to Snowflake types
        col_type = map_sqlalchemy_to_snowflake(col_type_raw)

        # Parse options
        nullable = "nullable=False" not in col_options
        is_primary = "primary_key=True" in col_options
        unique = "unique=True" in col_options

        default_value = extract_default_value(col_options)

        # Extract foreign key from inline ForeignKey
        fk_match = re.search(r"sa\.ForeignKey\(['\"]([^'\"]+)['\"]\)", col_options)
        if fk_match:
            foreign_keys.append((col_name, fk_match.group(1)))

        # Build column definition
        col_def = f"    {col_name} {col_type}"
        if not nullable:
            col_def += " NOT NULL"
        if unique:
            unique_columns.add(col_name)
        if default_value is not None:
            col_def += f" DEFAULT {default_value}"

        columns.append(col_def)

        if is_primary:
            primary_keys.append(col_name)

    # Override primary keys if PrimaryKeyConstraint is present
    if pk_constraint_match:
        pk_cols = [k.strip().strip("'\"") for k in pk_constraint_match.group(1).split(",")]
        primary_keys = pk_cols

    # Add unique constraints from UniqueConstraint(...)
    for unique_match in unique_constraint_matches:
        unique_cols = [c.strip().strip("'\"") for c in unique_match.split(",")]
        unique_columns.update(unique_cols)

    # Add foreign keys from ForeignKeyConstraint(...)
    for local_cols_str, remote_cols_str in fk_constraint_matches:
        local_cols = [c.strip().strip("'\"") for c in local_cols_str.split(",")]
        remote_cols = [c.strip().strip("'\"") for c in remote_cols_str.split(",")]
        for lc, rc in zip(local_cols, remote_cols):
            foreign_keys.append((lc, rc))

    if not columns:
        return None

    # Build CREATE TABLE statement
    sql_parts = [f"CREATE TABLE IF NOT EXISTS app_data.{table_name} (\n"]
    sql_parts.append(",\n".join(columns))

    # Add primary key constraint
    if primary_keys:
        sql_parts.append(f",\n    PRIMARY KEY ({', '.join(primary_keys)})")

    # Add unique constraints
    for unique_col in unique_columns:
        # If unique column is also primary key, no need to add UNIQUE separately
        if unique_col not in primary_keys:
            sql_parts.append(f",\n    UNIQUE ({unique_col})")

    # Add foreign key constraints
    for fk_col, fk_ref in foreign_keys:
        if '.' in fk_ref:
            ref_table, ref_col = fk_ref.rsplit(".", 1)
        else:
            ref_table, ref_col = fk_ref, "id"
        sql_parts.append(f",\n    FOREIGN KEY ({fk_col}) REFERENCES app_data.{ref_table}({ref_col})")

    sql_parts.append("\n);")

    return "".join(sql_parts)


def map_sqlalchemy_to_snowflake(sa_type: str) -> str:
    """Map SQLAlchemy type to Snowflake type."""
    sa_type = sa_type.strip()

    # Handle Enum types - Snowflake doesn't have native ENUM, use VARCHAR
    # Pattern: sa.Enum('VAL1', 'VAL2', name='enumname') or Enum('VAL1', 'VAL2', name='enumname')
    if re.match(r"(sa\.)?Enum\(", sa_type):
        return "VARCHAR"

    # Handle snowflake.sqlalchemy custom types (e.g., snowflake.sqlalchemy.custom_types.VARIANT)
    if "snowflake.sqlalchemy" in sa_type:
        # Extract the actual type name (VARIANT, ARRAY, OBJECT, etc.)
        type_match = re.search(r"\.([A-Z]+)(?:\(\))?$", sa_type)
        if type_match:
            return type_match.group(1)
        # Fallback: just extract last part
        return sa_type.split(".")[-1].replace("()", "")

    # Normalize type string for matching
    base_type = sa_type.split('(')[0]

    mappings = {
        "sa.String": "VARCHAR",
        "sa.Text": "TEXT",
        "sa.Integer": "INTEGER",
        "sa.Boolean": "BOOLEAN",
        "sa.DateTime": "TIMESTAMP_NTZ",
        "sa.Float": "FLOAT",
        "sa.Numeric": "NUMBER",
        "sa.Date": "DATE",
        "sa.TIMESTAMP": "TIMESTAMP_NTZ",
        "sa.TIMESTAMP_TZ": "TIMESTAMP_TZ",
        "VARIANT": "VARIANT",
        "BINARY": "BINARY",
        "ARRAY": "ARRAY",
        "OBJECT": "OBJECT",
    }

    # Check for length inside parentheses
    length_match = re.search(r"\((\d+)(?:,\s*\d+)?\)", sa_type)

    if base_type in mappings:
        mapped_type = mappings[base_type]
        if mapped_type == "VARCHAR" and length_match:
            return f"VARCHAR({length_match.group(1)})"
        if mapped_type == "NUMBER" and length_match:
            return f"NUMBER{sa_type[sa_type.find('('):sa_type.find(')')+1]}"
        return mapped_type

    # Special cases for sa.String with specific lengths
    if sa_type.startswith("sa.String(") and length_match:
        return f"VARCHAR({length_match.group(1)})"

    # If type is already a Snowflake type like VARIANT(), BINARY(), etc.
    if sa_type.startswith(("VARIANT", "BINARY", "FLOAT", "NUMBER", "TIMESTAMP", "DATE", "ARRAY", "OBJECT")):
        # Remove trailing parentheses for consistency
        return sa_type.replace("()", "")

    # Default: return as-is but clean up
    return sa_type.replace("sa.", "").replace("()", "")


def generate_individual_migration_sql(migration: dict, index: int) -> str:
    """Generate SQL content for a single migration file."""
    revision = migration["revision"]
    message = migration["message"]

    lines = [
        f"-- =============================================================================",
        f"-- Migration: {revision}",
        f"-- {message}",
        f"-- =============================================================================",
        f"-- This migration is idempotent and can be safely re-run.",
        f"-- It uses IF NOT EXISTS / IF EXISTS clauses for all operations.",
        f"-- =============================================================================",
        "",
    ]

    # Extract SQL statements with idempotent syntax
    sql_statements = extract_upgrade_sql(migration, use_idempotent=True)

    for sql in sql_statements:
        lines.append(sql)
        lines.append("")

    # Add version tracking with idempotent INSERT
    lines.append(f"-- Mark migration as applied (idempotent)")
    lines.append(f"INSERT INTO app_data.alembic_version (version_num)")
    lines.append(f"SELECT '{revision}' WHERE NOT EXISTS (")
    lines.append(f"    SELECT 1 FROM app_data.alembic_version WHERE version_num = '{revision}'")
    lines.append(f");")

    return "\n".join(lines)


def generate_migrations_sql(local_schema: str = None, local_database: str = None, local_role: str = None):
    """Generate migration SQL files - both individual and combined.

    Args:
        local_schema: If provided, also generates local_migrations.sql with this schema name.
        local_database: Database name for local migrations (optional, adds USE DATABASE).
        local_role: Role name for local migrations (optional, adds USE ROLE).
    """
    if not ALEMBIC_VERSIONS_DIR.exists():
        print(f"Error: Alembic versions directory not found: {ALEMBIC_VERSIONS_DIR}")
        sys.exit(1)

    # Find all migration files
    migration_files = list(ALEMBIC_VERSIONS_DIR.glob("*.py"))
    migration_files = [f for f in migration_files if not f.name.startswith("__")]

    if not migration_files:
        print("No migration files found")
        sys.exit(1)

    print(f"Found {len(migration_files)} migration file(s)")

    # Parse all migrations
    migrations = [parse_migration_file(f) for f in migration_files]

    # Order by dependencies
    ordered_migrations = get_ordered_migrations(migrations)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate individual migration files
    migration_manifest = {
        "migrations": [],
        "latest_version": None
    }

    for i, migration in enumerate(ordered_migrations):
        revision = migration["revision"]
        slug = migration["slug"]
        message = migration["message"]

        # Generate filename: use original migration filename with .sql extension
        original_filename = migration["filepath"].stem  # e.g., 20251229_165659_initial
        filename = f"{original_filename}.sql"
        filepath = OUTPUT_DIR / filename

        # Generate SQL content
        sql_content = generate_individual_migration_sql(migration, i)
        filepath.write_text(sql_content)

        # Add to manifest
        migration_manifest["migrations"].append({
            "index": i + 1,
            "revision": revision,
            "filename": filename,
            "message": message,
            "down_revision": migration["down_revision"]
        })

        print(f"  Generated: {filename}")

    # Set latest version
    if ordered_migrations:
        migration_manifest["latest_version"] = ordered_migrations[-1]["revision"]

    # Write manifest
    MANIFEST_FILE.write_text(json.dumps(migration_manifest, indent=2))
    print(f"  Generated: migrations_manifest.json")

    # Generate combined migrations.sql for Native App (uses app_data schema)
    combined_lines = [
        "-- =============================================================================",
        "-- BlendX Database Migrations (Combined) - Native App",
        "-- Auto-generated from Alembic migrations - DO NOT EDIT MANUALLY",
        "-- Generated by: scripts/generate/generate_migrations_sql.py",
        "-- =============================================================================",
        "-- ",
        "-- This file contains ALL migrations combined for initial installation.",
        "-- For incremental upgrades, use the individual files in migrations/ directory.",
        "-- =============================================================================",
        "",
        "-- Alembic version tracking table",
        "CREATE TABLE IF NOT EXISTS app_data.alembic_version (",
        "    version_num VARCHAR(32) PRIMARY KEY",
        ");",
        "",
    ]

    for i, migration in enumerate(ordered_migrations):
        revision = migration["revision"]
        message = migration["message"]

        combined_lines.append(f"-- -----------------------------------------------------------------------------")
        combined_lines.append(f"-- Migration {i + 1}: {revision}")
        combined_lines.append(f"-- {message}")
        combined_lines.append(f"-- -----------------------------------------------------------------------------")
        combined_lines.append("")

        # Extract SQL statements
        sql_statements = extract_upgrade_sql(migration, use_idempotent=True)

        for sql in sql_statements:
            combined_lines.append(sql)
            combined_lines.append("")

        # Add version tracking
        combined_lines.append(f"-- Mark migration as applied")
        combined_lines.append(f"INSERT INTO app_data.alembic_version (version_num)")
        combined_lines.append(f"SELECT '{revision}' WHERE NOT EXISTS (")
        combined_lines.append(f"    SELECT 1 FROM app_data.alembic_version WHERE version_num = '{revision}'")
        combined_lines.append(f");")
        combined_lines.append("")

    # Write combined output file for Native App
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(combined_lines))

    print(f"\nGenerated: {OUTPUT_FILE}")
    print(f"Generated: {OUTPUT_DIR}/")

    # Generate local_migrations.sql if schema is provided
    if local_schema:
        local_migrations_content = "\n".join(combined_lines).replace("app_data.", f"{local_schema}.")

        # Build the USE statements
        use_statements = []
        if local_role:
            use_statements.append(f"USE ROLE {local_role};")
        if local_database:
            use_statements.append(f"USE DATABASE {local_database};")
            use_statements.append(f"USE SCHEMA {local_database}.{local_schema};")

        use_block = "\n".join(use_statements) + "\n\n" if use_statements else ""

        # Build command info for header
        cmd_parts = ["--schema", local_schema]
        if local_database:
            cmd_parts.extend(["--database", local_database])
        if local_role:
            cmd_parts.extend(["--role", local_role])
        cmd_info = " ".join(cmd_parts)

        local_migrations_header = f"""-- =============================================================================
-- BlendX Local Development Migrations
-- Auto-generated from Alembic migrations - DO NOT EDIT MANUALLY
-- Generated by: scripts/generate/generate_migrations_sql.py {cmd_info}
-- =============================================================================
--
-- Database: {local_database or '(not specified)'}
-- Schema: {local_schema}
-- Role: {local_role or '(not specified)'}
--
-- Usage:
--   snow sql -f scripts/generated/local_migrations.sql --connection your_connection
-- =============================================================================

{use_block}"""
        # Replace the header in local migrations
        local_content_lines = local_migrations_content.split("\n")
        # Find where the actual content starts (after the header comments)
        content_start = 0
        for idx, line in enumerate(local_content_lines):
            if line.startswith("-- Alembic version tracking table"):
                content_start = idx
                break

        local_migrations_final = local_migrations_header + "\n".join(local_content_lines[content_start:])

        LOCAL_MIGRATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOCAL_MIGRATIONS_FILE.write_text(local_migrations_final)

        print(f"Generated: {LOCAL_MIGRATIONS_FILE} (schema: {local_schema})")

    print(f"\nMigrations included: {len(ordered_migrations)}")
    for i, m in enumerate(ordered_migrations):
        print(f"  {i + 1}. {m['revision']}: {m['message']}")

    if migration_manifest["latest_version"]:
        print(f"\nLatest version: {migration_manifest['latest_version']}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate SQL from Alembic migrations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--schema',
        help='Schema name for local development (generates local_migrations.sql)'
    )
    parser.add_argument(
        '--database',
        help='Database name for local development (used with --schema)'
    )
    parser.add_argument(
        '--role',
        help='Role name for local development (used with --schema)'
    )

    args = parser.parse_args()
    generate_migrations_sql(
        local_schema=args.schema,
        local_database=args.database,
        local_role=args.role
    )


if __name__ == "__main__":
    main()
