#!/usr/bin/env python3
"""
Generate application files from templates.
Replaces multiple sed commands with a single Python script.
"""

import argparse
import re
import sys
from pathlib import Path


def replace_placeholders(content: str, replacements: dict) -> str:
    """Replace {{PLACEHOLDER}} with values."""
    for key, value in replacements.items():
        content = content.replace(f"{{{{{key}}}}}", value)
    return content


def generate_manifest(template_path: str, output_path: str, replacements: dict):
    """Generate manifest.yml from template."""
    with open(template_path, 'r') as f:
        content = f.read()

    result = replace_placeholders(content, replacements)

    with open(output_path, 'w') as f:
        f.write(result)

    print(f"Generated {output_path}")


def generate_fullstack(template_path: str, output_path: str, replacements: dict):
    """Generate fullstack.yaml from template."""
    with open(template_path, 'r') as f:
        content = f.read()

    result = replace_placeholders(content, replacements)

    with open(output_path, 'w') as f:
        f.write(result)

    print(f"Generated {output_path}")


def generate_setup_sql(template_path: str, tables_path: str, output_path: str):
    """Generate setup.sql from template with table definitions."""
    with open(tables_path, 'r') as f:
        content = f.read()

    # Remove comments
    lines = [l for l in content.split('\n') if not l.strip().startswith('--')]
    table_defs = '\n'.join(lines)

    # Replace CREATE TABLE IF NOT EXISTS with CREATE OR REPLACE TABLE app_data.
    table_defs = table_defs.replace(
        'CREATE TABLE IF NOT EXISTS ',
        'CREATE OR REPLACE TABLE app_data.'
    )

    # Extract table names and generate grants
    tables = sorted(set(re.findall(r'app_data\.([a-z_]+)', table_defs)))
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

    setup_content = setup_content.replace('-- {{TABLE_DEFINITIONS}}', full_content)

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

    args = parser.parse_args()

    # Ensure output directory exists
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Common replacements
    replacements = {
        'SNOWFLAKE_DATABASE': args.database,
        'SNOWFLAKE_SCHEMA': args.schema,
        'SNOWFLAKE_IMG_REPO': args.img_repo,
        'IMAGE_TAG': args.image_tag,
    }

    print(f"Generating files with:")
    print(f"  Database:  {args.database}")
    print(f"  Schema:    {args.schema}")
    print(f"  Img Repo:  {args.img_repo}")
    print(f"  Image Tag: {args.image_tag}")
    print()

    # Generate manifest.yml
    generate_manifest(
        'templates/manifest_template.yml',
        str(output_dir / 'manifest.yml'),
        replacements
    )

    # Generate fullstack.yaml
    generate_fullstack(
        'templates/fullstack_template.yaml',
        str(output_dir / 'fullstack.yaml'),
        replacements
    )

    # Generate setup.sql
    generate_setup_sql(
        'templates/setup_template.sql',
        'scripts/sql/tables_definitions.sql',
        str(output_dir / 'setup.sql')
    )

    print()
    print("All files generated successfully!")


if __name__ == '__main__':
    main()
