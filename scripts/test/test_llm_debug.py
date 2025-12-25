"""
Debug script to test Snowflake Cortex LLM connectivity
"""
import logging
import sys
sys.path.insert(0, '/Users/mikaelapisani/Projects/blendx-sfguide-mktplace/backend/src')

from app.config.settings import get_settings
from app.handlers.lite_llm_handler import get_llm

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_llm_connection():
    """Test LLM connection with detailed logging"""

    # Get settings
    settings = get_settings()
    logger.info("=" * 80)
    logger.info("Settings loaded:")
    logger.info(f"  Account: {settings.snowflake_account}")
    logger.info(f"  User: {settings.snowflake_user}")
    logger.info(f"  Host: {settings.snowflake_host}")
    logger.info(f"  Auth method: {settings.snowflake_authmethod}")
    logger.info(f"  Private key path: {settings.snowflake_private_key_path}")
    logger.info(f"  Environment: {settings.environment}")
    logger.info("=" * 80)

    try:
        # Test 1: Try with OpenAI-compatible endpoint and short model name
        logger.info("\n" + "=" * 80)
        logger.info("TEST 1: OpenAI-compatible endpoint with claude-3-5-sonnet")
        logger.info("=" * 80)

        llm = get_llm(provider='snowflake', model='claude-3-5-sonnet')
        logger.info("✅ LLM instance created successfully")

        # Try a simple call
        logger.info("Calling LLM with simple message...")
        messages = [{"role": "user", "content": "Say hello in one word"}]
        response = llm.call(messages)
        logger.info(f"✅ Response received: {response}")

        return True

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_llm_connection()
    sys.exit(0 if success else 1)
