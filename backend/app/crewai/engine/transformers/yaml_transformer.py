"""
YAML transformer utility for BlendX Core engine.

Transforms all YAML files in a directory into a single escaped string, suitable for shell usage or embedding in other scripts. Validates YAML and strips comments. Can be run as a script or imported as a module.
"""

#!/usr/bin/env python

import argparse
import logging
import os
import sys
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


def transform_yaml(input_dir: str) -> str:
    """Transform YAML files from a directory into a single escaped string.

    Args:
        input_dir: Path to directory containing YAML files

    Returns:
        A string containing all YAML content with escaped quotes and newlines,
        excluding comment lines that start with #

    Raises:
        ValueError: If a YAML file is invalid
    """
    combined_content = ""

    for filename in sorted(os.listdir(input_dir)):
        if filename.endswith((".yaml", ".yml")):
            file_path = os.path.join(input_dir, filename)

            # Validate YAML (without altering its original form)
            with open(file_path, "r", encoding="utf-8") as f:
                raw_content = f.read()

                try:
                    yaml.safe_load(raw_content)  # validation
                except yaml.YAMLError as e:
                    raise ValueError(f"Invalid file: {filename}\n{e}")

                # Filter out lines that start with #
                filtered_lines = [
                    line
                    for line in raw_content.split("\n")
                    if not line.strip().startswith("#")
                ]
                filtered_content = "\n".join(filtered_lines)
                combined_content += filtered_content + "\n"

    # Escape quotes and newlines for shell usage
    escaped_content = combined_content.replace('"', '\\"')
    escaped_content = escaped_content.replace("\n", "\\n")

    return escaped_content


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Transform YAML files from a directory into a single escaped string"
    )
    parser.add_argument("input_dir", help="Path to directory containing YAML files")
    parser.add_argument(
        "-o", "--output", help="Output file path (if not specified, prints to stdout)"
    )

    args = parser.parse_args()

    try:
        result = transform_yaml(args.input_dir)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result)
            logger.info(f"Output written to {args.output}")
        else:
            # Print to stdout for CLI usage (expected behavior)
            sys.stdout.write(result)

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
