#!/usr/bin/env python3
"""
Generate application files from templates.
Replaces multiple sed commands with a single Python script.
"""

import argparse
import re
import sys
from pathlib import Path


class GenerationError(Exception):
    """Raised when file generation fails."""
    pass


def replace_placeholders(content: str, replacements: dict) -> str:
    """Replace {{PLACEHOLDER}} with values."""
    for key, value in replacements.items():
        content = content.replace(f"{{{{{key}}}}}", value)
    return content


def validate_no_unresolved_placeholders(content: str, file_name: str) -> None:
    """Fail fast if any {{PLACEHOLDER}} remains unresolved."""
    unresolved = re.findall(r'\{\{([A-Z_][A-Z0-9_]*)\}\}', content)
    if unresolved:
        raise GenerationError(
            f"Unresolved placeholders in {file_name}: {', '.join(set(unresolved))}"
        )


def generate_from_template(
    template_path: str,
    output_path: str,
    replacements: dict,
    dry_run: bool = False
) -> str:
    """Generate a file from template with placeholder replacement."""
    with open(template_path, 'r') as f:
        content = f.read()

    result = replace_placeholders(content, replacements)
    validate_no_unresolved_placeholders(result, output_path)

    if dry_run:
        print(f"[DRY-RUN] Would generate {output_path}")
    else:
        with open(output_path, 'w') as f:
            f.write(result)
        print(f"Generated {output_path}")

    return result


def generate_setup_sql(
    template_path: str,
    tables_path: str,
    output_path: str,
    dry_run: bool = False
) -> None:
    """Generate setup.sql from template with table definitions."""
    with open(tables_path, 'r') as f:
        content = f.read()

    # Remove comments
    lines = [l for l in content.split('\n') if not l.strip().startswith('--')]
    table_defs = '\n'.join(lines)

    # Replace CREATE TABLE IF NOT EXISTS with CREATE OR REPLACE TABLE app_data.
    original_table_defs = table_defs
    table_defs = table_defs.replace(
        'CREATE TABLE IF NOT EXISTS ',
        'CREATE OR REPLACE TABLE app_data.'
    )

    # Validate at least one replacement occurred
    if table_defs == original_table_defs:
        raise GenerationError(
            f"No 'CREATE TABLE IF NOT EXISTS' found in {tables_path}. "
            "Expected at least one table definition."
        )

    # Extract table names (support uppercase, lowercase, numbers)
    tables = sorted(set(re.findall(r'app_data\.([a-zA-Z_][a-zA-Z0-9_]*)', table_defs, re.IGNORECASE)))

    if not tables:
        raise GenerationError(
            f"No table names extracted from {tables_path}. Check the SQL syntax."
        )

    grants = []
    for table in tables:
        grants.append(f"""
    -- Grant permissions for {table} table
    GRANT SELECT ON TABLE app_data.{table} TO APPLICATION ROLE app_user;
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE app_data.{table} TO APPLICATION ROLE app_admin;""")

    full_content = table_defs + '\n'.join(grants)

    # Read template and inject table definitions
    with open(template_path, 'r') as f:
        setup_content = f.read()

    if '{{TABLE_DEFINITIONS}}' not in setup_content:
        raise GenerationError(
            f"Placeholder '{{{{TABLE_DEFINITIONS}}}}' not found in {template_path}"
        )

    setup_content = setup_content.replace('{{TABLE_DEFINITIONS}}', full_content)

    if dry_run:
        print(f"[DRY-RUN] Would generate {output_path} with {len(tables)} tables: {', '.join(tables)}")
    else:
        with open(output_path, 'w') as f:
            f.write(setup_content)
        print(f"Generated {output_path} with {len(tables)} table definitions: {', '.join(tables)}")


def main():
    parser = argparse.ArgumentParser(description='Generate application files from templates')
    parser.add_argument('--database', required=True, help='Snowflake database')
    parser.add_argument('--schema', required=True, help='Snowflake schema')
    parser.add_argument('--img-repo', required=True, help='Image repository name')
    parser.add_argument('--image-tag', required=True, help='Docker image tag (SHA)')
    parser.add_argument('--output-dir', default='app/src', help='Output directory')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be generated without writing files')

    args = parser.parse_args()

    # Ensure output directory exists (unless dry-run)
    output_dir = Path(args.output_dir)
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Common replacements
    replacements = {
        'SNOWFLAKE_DATABASE': args.database,
        'SNOWFLAKE_SCHEMA': args.schema,
        'SNOWFLAKE_IMG_REPO': args.img_repo,
        'IMAGE_TAG': args.image_tag,
    }

    mode = "[DRY-RUN] " if args.dry_run else ""
    print(f"{mode}Generating files with:")
    print(f"  Database:  {args.database}")
    print(f"  Schema:    {args.schema}")
    print(f"  Img Repo:  {args.img_repo}")
    print(f"  Image Tag: {args.image_tag}")
    print()

    try:
        # Generate manifest.yml
        generate_from_template(
            'templates/manifest_template.yml',
            str(output_dir / 'manifest.yml'),
            replacements,
            dry_run=args.dry_run
        )

        # Generate fullstack.yaml
        generate_from_template(
            'templates/fullstack_template.yaml',
            str(output_dir / 'fullstack.yaml'),
            replacements,
            dry_run=args.dry_run
        )

        # Generate setup.sql
        generate_setup_sql(
            'templates/setup_template.sql',
            'scripts/sql/tables_definitions.sql',
            str(output_dir / 'setup.sql'),
            dry_run=args.dry_run
        )

        print()
        print(f"{mode}All files generated successfully!")

    except GenerationError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"ERROR: File not found: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
