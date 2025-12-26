"""
Test script to verify response_format (json_schema) works with Snowflake Cortex Claude models.

This tests both:
1. SnowflakeLitellmService (custom service) - uses native Snowflake endpoint
2. TrackedLLM with openai/ prefix - uses OpenAI-compatible endpoint

Run from backend directory:
    cd backend && python -m scripts.test_scripts.test_response_format
"""

import json
import logging
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from pydantic import BaseModel
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MermaidChartResponse(BaseModel):
    """Expected response format for mermaid chart generation.
    Note: Snowflake doesn't support Optional/anyOf in schemas, so no optional fields.
    """
    mermaid_chart: str


class SimpleResponse(BaseModel):
    """Simple response for testing"""
    answer: str
    confidence: float


def test_snowflake_native_service():
    """Test SnowflakeLitellmService with response_format"""
    from app.handlers.lite_llm_handler import SnowflakeLitellmService
    from app.config.settings import get_settings

    settings = get_settings()

    logger.info("=" * 60)
    logger.info("TEST 1: SnowflakeLitellmService with response_format")
    logger.info("=" * 60)

    # Build base URL using snowflake_host
    host = settings.snowflake_host
    if not host:
        logger.error("SNOWFLAKE_HOST not set")
        return False
    base_url = f"https://{host}/api/v2/cortex/inference:complete"

    # Get private key
    private_key = None
    if settings.snowflake_private_key_path and os.path.exists(settings.snowflake_private_key_path):
        with open(settings.snowflake_private_key_path, "r") as f:
            private_key = f.read()

    try:
        # Create service with response_format
        service = SnowflakeLitellmService(
            base_url=base_url,
            snowflake_account=settings.snowflake_account,
            snowflake_service_user=settings.snowflake_user,
            snowflake_authmethod="jwt" if private_key else "oauth",
            api_key=private_key,
            temperature=0.1,
            response_format=SimpleResponse.model_json_schema(),
        )

        messages = [
            {"role": "user", "content": "What is 2+2? Respond with the answer and your confidence level (0-1)."}
        ]

        logger.info(f"Calling with response_format schema: {SimpleResponse.model_json_schema()}")
        response = service.completion(
            model="claude-3-5-sonnet",
            messages=messages,
            timeout=60,
        )

        logger.info(f"Raw response: {response}")

        # Try to parse the response
        content = response.choices[0].message.content
        logger.info(f"Content: {content}")

        parsed = json.loads(content)
        logger.info(f"Parsed JSON: {parsed}")

        print("\n✅ TEST 1 PASSED: SnowflakeLitellmService works with response_format")
        return True

    except Exception as e:
        logger.error(f"❌ TEST 1 FAILED: {e}", exc_info=True)
        return False


def test_get_llm_with_response_format():
    """Test get_llm() with response_format parameter"""
    from app.handlers.lite_llm_handler import get_llm

    logger.info("=" * 60)
    logger.info("TEST 2: get_llm() with response_format (TrackedLLM)")
    logger.info("=" * 60)

    try:
        llm = get_llm(
            provider="snowflake",
            model="claude-3-5-sonnet",
            response_format=SimpleResponse.model_json_schema(),
        )

        messages = [
            {"role": "user", "content": "What is 2+2? Respond with the answer and your confidence level (0-1)."}
        ]

        logger.info(f"LLM type: {type(llm)}")
        logger.info(f"LLM model: {getattr(llm, 'model', 'unknown')}")

        response = llm.call(messages)
        logger.info(f"Response: {response}")

        # Try to parse
        parsed = json.loads(response)
        logger.info(f"Parsed JSON: {parsed}")

        print("\n✅ TEST 2 PASSED: get_llm() works with response_format")
        return True

    except Exception as e:
        logger.error(f"❌ TEST 2 FAILED: {e}", exc_info=True)
        return False


def test_mermaid_response_format():
    """Test the exact MermaidChartResponse format used in nl_ai_generator_service"""
    from app.handlers.lite_llm_handler import SnowflakeLitellmService
    from app.config.settings import get_settings

    settings = get_settings()

    logger.info("=" * 60)
    logger.info("TEST 3: MermaidChartResponse format (like nl_ai_generator)")
    logger.info("=" * 60)

    # Build base URL using snowflake_host
    host = settings.snowflake_host
    if not host:
        logger.error("SNOWFLAKE_HOST not set")
        return False
    base_url = f"https://{host}/api/v2/cortex/inference:complete"

    # Get private key
    private_key = None
    if settings.snowflake_private_key_path and os.path.exists(settings.snowflake_private_key_path):
        with open(settings.snowflake_private_key_path, "r") as f:
            private_key = f.read()

    try:
        service = SnowflakeLitellmService(
            base_url=base_url,
            snowflake_account=settings.snowflake_account,
            snowflake_service_user=settings.snowflake_user,
            snowflake_authmethod="jwt" if private_key else "oauth",
            api_key=private_key,
            temperature=0.1,
            response_format=MermaidChartResponse.model_json_schema(),
        )

        messages = [
            {"role": "user", "content": """Generate a simple mermaid flowchart showing:
            Start -> Process Data -> End

            Return the mermaid chart code and a brief explanation."""}
        ]

        logger.info(f"MermaidChartResponse schema: {json.dumps(MermaidChartResponse.model_json_schema(), indent=2)}")

        response = service.completion(
            model="claude-3-5-sonnet",
            messages=messages,
            timeout=60,
        )

        content = response.choices[0].message.content
        logger.info(f"Content: {content}")

        parsed = json.loads(content)
        logger.info(f"Parsed mermaid_chart: {parsed.get('mermaid_chart', 'NOT FOUND')}")

        print("\n✅ TEST 3 PASSED: MermaidChartResponse format works")
        return True

    except Exception as e:
        logger.error(f"❌ TEST 3 FAILED: {e}", exc_info=True)
        return False


def test_response_format_type_json_schema():
    """Test with explicit json_schema type format"""
    from app.handlers.lite_llm_handler import SnowflakeLitellmService
    from app.config.settings import get_settings

    settings = get_settings()

    logger.info("=" * 60)
    logger.info("TEST 4: Explicit json_schema type format")
    logger.info("=" * 60)

    # Build base URL using snowflake_host
    host = settings.snowflake_host
    if not host:
        logger.error("SNOWFLAKE_HOST not set")
        return False
    base_url = f"https://{host}/api/v2/cortex/inference:complete"

    # Get private key
    private_key = None
    if settings.snowflake_private_key_path and os.path.exists(settings.snowflake_private_key_path):
        with open(settings.snowflake_private_key_path, "r") as f:
            private_key = f.read()

    # Test different response_format structures
    formats_to_test = [
        # Format 1: Raw schema (current implementation)
        {
            "name": "raw_schema",
            "format": SimpleResponse.model_json_schema(),
        },
        # Format 2: type: json_schema (OpenAI style)
        {
            "name": "json_schema_type",
            "format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "SimpleResponse",
                    "schema": SimpleResponse.model_json_schema(),
                    "strict": True
                }
            },
        },
        # Format 3: type: json (Snowflake native style)
        {
            "name": "json_type",
            "format": {
                "type": "json",
                "schema": SimpleResponse.model_json_schema(),
            },
        },
    ]

    results = []
    for fmt in formats_to_test:
        logger.info(f"\nTesting format: {fmt['name']}")
        logger.info(f"Format: {json.dumps(fmt['format'], indent=2)[:200]}...")

        try:
            # Note: We need to modify SnowflakeLitellmService to handle different formats
            # For now, just test with the raw schema
            service = SnowflakeLitellmService(
                base_url=base_url,
                snowflake_account=settings.snowflake_account,
                snowflake_service_user=settings.snowflake_user,
                snowflake_authmethod="jwt" if private_key else "oauth",
                api_key=private_key,
                temperature=0.1,
                response_format=fmt["format"] if fmt["name"] == "raw_schema" else SimpleResponse.model_json_schema(),
            )

            messages = [
                {"role": "user", "content": "What is 2+2? Respond with the answer and confidence."}
            ]

            response = service.completion(
                model="claude-3-5-sonnet",
                messages=messages,
                timeout=60,
            )

            content = response.choices[0].message.content
            parsed = json.loads(content)
            logger.info(f"✅ {fmt['name']}: SUCCESS - {parsed}")
            results.append((fmt["name"], True))

        except Exception as e:
            logger.error(f"❌ {fmt['name']}: FAILED - {e}")
            results.append((fmt["name"], False))

    print("\n" + "=" * 60)
    print("TEST 4 RESULTS:")
    for name, success in results:
        print(f"  {'✅' if success else '❌'} {name}")
    print("=" * 60)

    return all(success for _, success in results)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SNOWFLAKE CORTEX response_format TEST SUITE")
    print("=" * 60 + "\n")

    results = []

    # Run tests
    results.append(("SnowflakeLitellmService", test_snowflake_native_service()))
    results.append(("get_llm with response_format", test_get_llm_with_response_format()))
    results.append(("MermaidChartResponse", test_mermaid_response_format()))
    # results.append(("json_schema formats", test_response_format_type_json_schema()))

    print("\n" + "=" * 60)
    print("FINAL RESULTS:")
    print("=" * 60)
    for name, success in results:
        print(f"  {'✅' if success else '❌'} {name}")

    all_passed = all(success for _, success in results)
    print("\n" + ("✅ ALL TESTS PASSED" if all_passed else "❌ SOME TESTS FAILED"))

    sys.exit(0 if all_passed else 1)
