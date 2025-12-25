#!/usr/bin/env python3
"""
Generate local development setup SQL files from templates.

This script generates:
1. local_setup.sql - Full setup including DB, roles, and migrations
2. local_migrations.sql - Only migrations (for updating existing local DB)

Usage:
    python scripts/generate_local_setup.py \
        --database MY_DEV_DB \
        --schema APP_DATA \
        --role MY_DEV_ROLE \
        --user MY_USER \
        --warehouse MY_DEV_WH

If keys/rsa_key.pub exists, a service user will be created automatically
with JWT authentication configured.
"""

import argparse
import re
import sys
from pathlib import Path


class GenerationError(Exception):
    """Raised when file generation fails."""
    pass


def read_migrations_sql() -> str:
    """Read the generated migrations SQL file."""
    migrations_path = Path('scripts/sql/migrations.sql')

    if not migrations_path.exists():
        raise GenerationError(
            f"Migrations SQL file not found: {migrations_path}\n"
            "Run 'python scripts/generate_migrations_sql.py' first to generate it."
        )

    with open(migrations_path, 'r') as f:
        content = f.read()

    # Remove the app_data. prefix since local setup uses USE SCHEMA
    content = content.replace('app_data.', '')

    return content


def read_public_key(key_file: str) -> str:
    """Read public key file and extract the key content (without headers)."""
    with open(key_file, 'r') as f:
        lines = f.readlines()

    # Filter out BEGIN/END lines and join
    key_content = ''.join(
        line.strip() for line in lines
        if 'BEGIN' not in line and 'END' not in line
    )

    return key_content


def generate_service_user_sql(
    service_user: str,
    warehouse: str,
    role: str,
    public_key: str
) -> str:
    """Generate SQL for creating service user with JWT auth."""
    return f"""-- Create service user for JWT authentication (used by backend)
CREATE USER IF NOT EXISTS {service_user}
    TYPE = SERVICE
    DEFAULT_WAREHOUSE = '{warehouse}'
    DEFAULT_ROLE = '{role}'
    COMMENT = 'Service user for local BlendX development with JWT auth';

-- Set the RSA public key for JWT authentication
ALTER USER {service_user} SET RSA_PUBLIC_KEY='{public_key}';

-- Grant the development role to the service user
GRANT ROLE {role} TO USER {service_user};

-- Note: Configure your .env file with:
--   SNOWFLAKE_USER={service_user}
--   SNOWFLAKE_PRIVATE_KEY_PATH=keys/rsa_key.p8"""


def replace_placeholders(content: str, replacements: dict) -> str:
    """Replace {{PLACEHOLDER}} with values."""
    for key, value in replacements.items():
        content = content.replace(f"{{{{{key}}}}}", str(value))
    return content


def validate_no_unresolved_placeholders(content: str, file_name: str) -> None:
    """Fail fast if any {{PLACEHOLDER}} remains unresolved."""
    unresolved = re.findall(r'\{\{([A-Z_][A-Z0-9_]*)\}\}', content)
    if unresolved:
        raise GenerationError(
            f"Unresolved placeholders in {file_name}: {', '.join(set(unresolved))}"
        )


def generate_local_setup(
    database: str,
    schema: str,
    role: str,
    user: str,
    warehouse: str,
    service_user: str = None,
    public_key_file: str = None,
    output_dir: str = '.',
    dry_run: bool = False
) -> None:
    """Generate local_setup.sql and local_migrations.sql files."""

    # Read template
    template_path = Path('templates/local_setup_template.sql')
    if not template_path.exists():
        raise GenerationError(f"Template not found: {template_path}")

    with open(template_path, 'r') as f:
        template_content = f.read()

    # Read migrations SQL
    migrations_sql = read_migrations_sql()

    # Generate service user SQL if provided
    if service_user and public_key_file:
        public_key = read_public_key(public_key_file)
        service_user_sql = generate_service_user_sql(
            service_user, warehouse, role, public_key
        )
    else:
        service_user_sql = "-- Service user not configured. Run with --service-user and --public-key-file to enable."

    # Prepare replacements
    replacements = {
        'DATABASE': database,
        'SCHEMA': schema,
        'ROLE': role,
        'USER': user,
        'WAREHOUSE': warehouse,
        'MIGRATIONS_SQL': migrations_sql,
        'SERVICE_USER_SQL': service_user_sql,
    }

    # Generate local_setup.sql
    setup_content = replace_placeholders(template_content, replacements)
    validate_no_unresolved_placeholders(setup_content, 'local_setup.sql')

    output_path = Path(output_dir) / 'local_setup.sql'
    if dry_run:
        print(f"[DRY-RUN] Would generate {output_path}")
    else:
        with open(output_path, 'w') as f:
            f.write(setup_content)
        print(f"Generated {output_path}")

    # Generate local_migrations.sql (only migrations, for updating existing DB)
    migrations_only_content = f"""-- =============================================================================
-- BlendX Local Migrations
-- =============================================================================
-- Run this script to apply new migrations to an existing local database.
-- Generated by: scripts/generate_local_setup.py
--
-- Usage:
--   snow sql -f local_migrations.sql --connection <your_connection>
-- =============================================================================

USE ROLE {role};
USE WAREHOUSE {warehouse};
USE DATABASE {database};
USE SCHEMA {schema};

-- =============================================================================
-- DATABASE MIGRATIONS
-- =============================================================================
{migrations_sql}
-- =============================================================================

-- Verify migrations
SELECT * FROM alembic_version;
"""

    migrations_output_path = Path(output_dir) / 'local_migrations.sql'
    if dry_run:
        print(f"[DRY-RUN] Would generate {migrations_output_path}")
    else:
        with open(migrations_output_path, 'w') as f:
            f.write(migrations_only_content)
        print(f"Generated {migrations_output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate local development setup SQL files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--database', required=True, help='Snowflake database name')
    parser.add_argument('--schema', required=True, help='Snowflake schema name')
    parser.add_argument('--role', required=True, help='Snowflake role name')
    parser.add_argument('--user', required=True, help='Your Snowflake username')
    parser.add_argument('--warehouse', required=True, help='Snowflake warehouse name')
    parser.add_argument('--service-user', help='Service user name for JWT auth (default: derived from --user)')
    parser.add_argument('--public-key-file', help='Path to RSA public key file (default: keys/rsa_key.pub)')
    parser.add_argument('--no-service-user', action='store_true', help='Skip service user creation even if key exists')
    parser.add_argument('--output-dir', default='.', help='Output directory (default: current directory)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be generated without writing files')

    args = parser.parse_args()

    # Auto-detect public key file - always check keys/rsa_key.pub unless explicitly disabled
    public_key_file = args.public_key_file
    if not public_key_file and not args.no_service_user:
        default_key_path = Path('keys/rsa_key.pub')
        if default_key_path.exists():
            public_key_file = str(default_key_path)
            print(f"Auto-detected public key: {public_key_file}")
        else:
            print("Note: No keys/rsa_key.pub found. Service user will not be created.")
            print("      Generate keys with: openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out keys/rsa_key.p8 -nocrypt")
            print("                          openssl rsa -in keys/rsa_key.p8 -pubout -out keys/rsa_key.pub")

    # Auto-generate service user name: derive from role name (e.g., BLENDX_APP_DEV_ROLE -> BLENDX_APP_DEV_USER)
    service_user = args.service_user
    if public_key_file and not service_user and not args.no_service_user:
        # Derive service user name from role (replace _ROLE suffix with _USER)
        if args.role.endswith('_ROLE'):
            service_user = args.role.replace('_ROLE', '_USER')
        else:
            service_user = f"{args.role}_USER"

    mode = "[DRY-RUN] " if args.dry_run else ""
    print(f"{mode}Generating local setup files with:")
    print(f"  Database:  {args.database}")
    print(f"  Schema:    {args.schema}")
    print(f"  Role:      {args.role}")
    print(f"  User:      {args.user}")
    print(f"  Warehouse: {args.warehouse}")
    if service_user and public_key_file:
        print(f"  Service User: {service_user}")
        print(f"  Public Key:   {public_key_file}")
    else:
        print(f"  Service User: (not configured)")
    print()

    try:
        generate_local_setup(
            database=args.database,
            schema=args.schema,
            role=args.role,
            user=args.user,
            warehouse=args.warehouse,
            service_user=service_user,
            public_key_file=public_key_file,
            output_dir=args.output_dir,
            dry_run=args.dry_run
        )
        print()
        print(f"{mode}Files generated successfully!")
        print()
        print("Next steps:")
        print(f"  1. Run full setup:       snow sql -f local_setup.sql --connection <your_connection>")
        print(f"  2. Or update migrations: snow sql -f local_migrations.sql --connection <your_connection>")

    except GenerationError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"ERROR: File not found: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
