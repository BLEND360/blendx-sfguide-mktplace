#!/usr/bin/env python3
"""Test script to verify environment variables are loading correctly."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from settings import get_settings, ENV_FILE

print("=" * 60)
print("ENVIRONMENT VARIABLE LOADING TEST")
print("=" * 60)
print(f"\n.env file path: {ENV_FILE}")
print(f".env file exists: {ENV_FILE.exists()}")
print("\n" + "=" * 60)

settings = get_settings()

print("\nLoaded Settings:")
print("-" * 60)
print(f"Environment: {settings.environment}")
print(f"Snowflake User: {settings.snowflake_user}")
print(f"Snowflake Account: {settings.snowflake_account}")
print(f"Snowflake Host: {settings.snowflake_host}")
print(f"Snowflake Database: {settings.snowflake_database}")
print(f"Snowflake Schema: {settings.snowflake_schema}")
print(f"Snowflake Warehouse: {settings.snowflake_warehouse}")
print(f"Snowflake Role: {settings.snowflake_role}")
print(f"Snowflake Auth Method: {settings.snowflake_authmethod}")
print(f"Snowflake Private Key Path: {settings.snowflake_private_key_path}")
print("=" * 60)

if not settings.snowflake_user:
    print("\n⚠️  WARNING: snowflake_user is empty!")
    print("The .env file may not be loading correctly.")
else:
    print("\n✅ Settings loaded successfully!")
