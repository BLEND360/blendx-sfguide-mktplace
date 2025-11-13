"""
Test script to verify OpenAI format works with lite_llm_handler1.py
"""

import logging
from backend.src.lite_llm_handler import get_llm

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_openai_format():
    """Test using OpenAI format with the LLM handler"""
    try:
        # Get LLM instance - this will use settings from .env
        logger.info("Getting LLM instance...")
        llm = get_llm()

        # Test messages in OpenAI format
        messages = [
            {"role": "user", "content": "Say 'Hello from OpenAI format test!' in Spanish"}
        ]

        logger.info("Calling LLM with OpenAI format messages...")
        response = llm.call(messages)

        logger.info(f"Response: {response}")
        print("\n" + "="*50)
        print("SUCCESS! OpenAI format is working!")
        print("="*50)
        print(f"Response: {response}")

        return response

    except Exception as e:
        logger.error(f"Error testing OpenAI format: {e}", exc_info=True)
        print("\n" + "="*50)
        print("ERROR! OpenAI format test failed!")
        print("="*50)
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    test_openai_format()
