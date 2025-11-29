"""
Test script to check available Snowflake Cortex models
"""
import logging
import sys
sys.path.insert(0, '/Users/mikaelapisani/Projects/blendx-sfguide-mktplace/backend/src')

from backend.src.database.db import get_new_db_session
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def test_models():
    """Test different Cortex models to see which are available"""

    # List of models to test
    models_to_test = [
        'llama3-8b',
        'llama3-70b',
        'mistral-large',
        'mixtral-8x7b',
        'mistral-7b',
        'gemma-7b',
        'reka-flash',
        'snowflake-arctic',
        'jamba-instruct',
        'claude-3-5-sonnet',
        'claude-3-5-sonnet-20240620',
        'claude-3-5-haiku',
        'claude-3-opus',
        'claude-3-sonnet',
        'claude-3-haiku',
    ]

    logger.info("=" * 80)
    logger.info("Testing available Snowflake Cortex models...")
    logger.info("=" * 80)

    available = []
    unavailable = []

    with get_new_db_session() as session:
        for model in models_to_test:
            try:
                query = f"SELECT SNOWFLAKE.CORTEX.COMPLETE('{model}', 'hi')"
                logger.info(f"\nTesting model: {model}")
                result = session.execute(text(query))
                response = result.fetchone()[0]
                logger.info(f"  ✅ {model} - AVAILABLE")
                logger.info(f"     Response: {response[:100]}...")
                available.append(model)
            except Exception as e:
                error_msg = str(e)
                if "does not exist" in error_msg or "not recognized" in error_msg or "invalid" in error_msg:
                    logger.info(f"  ❌ {model} - NOT AVAILABLE")
                    unavailable.append(model)
                else:
                    logger.info(f"  ⚠️  {model} - ERROR: {error_msg[:100]}")

    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY:")
    logger.info("=" * 80)
    logger.info(f"\n✅ Available models ({len(available)}):")
    for model in available:
        logger.info(f"  - {model}")

    logger.info(f"\n❌ Unavailable models ({len(unavailable)}):")
    for model in unavailable:
        logger.info(f"  - {model}")

if __name__ == "__main__":
    test_models()
