"""
Health Router.

Endpoints for health checks and testing connections (Cortex, Secrets, Serper, LiteLLM).
"""

import json
import logging
import os

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.handlers.lite_llm_handler import get_llm
from app.utils.spcs_helper import get_serper_api_key, get_secret, _LOCAL_SECRETS_DIR

router = APIRouter(tags=["Health"])
logger = logging.getLogger(__name__)


@router.get("/")
async def root():
    """Root endpoint."""
    return {"message": "BlendX CrewAI API"}


@router.get("/health")
async def health():
    """Health check endpoint."""
    health_info = {
        "status": "ok",
        "environment": os.getenv("ENVIRONMENT", "not set"),
        "snowflake_authmethod": os.getenv("SNOWFLAKE_AUTHMETHOD", "not set"),
        "snowflake_account": os.getenv("SNOWFLAKE_ACCOUNT", "not set"),
        "oauth_token_exists": os.path.exists("/snowflake/session/token"),
    }

    if health_info["oauth_token_exists"]:
        try:
            with open("/snowflake/session/token", "r") as f:
                token = f.read().strip()
                health_info["oauth_token_length"] = len(token)
        except Exception as e:
            health_info["oauth_token_error"] = str(e)

    return health_info


@router.get("/test-cortex")
async def test_cortex(db: Session = Depends(get_db)):
    """
    Test Cortex connection using direct SQL call.
    This bypasses LiteLLM to diagnose connection/permission issues.
    """
    logger.info("Testing Cortex connection via SQL")

    try:
        # Get warehouse from env var, or detect from current session (QUERY_WAREHOUSE)
        warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "").strip()
        if not warehouse:
            # Get warehouse from current session (set by QUERY_WAREHOUSE in CREATE SERVICE)
            result = db.execute(text("SELECT CURRENT_WAREHOUSE()")).fetchone()
            warehouse = result[0] if result and result[0] else None
            logger.info(f"Detected warehouse from session: {warehouse}")

        test_prompt = "Say 'Hello, Cortex is working!' in exactly those words."

        logger.info(f"Using warehouse: {warehouse}")
        query = text(f"USE WAREHOUSE {warehouse}; SELECT SNOWFLAKE.CORTEX.COMPLETE('claude-3-5-sonnet', :prompt) as response")

        logger.info(f"Executing Cortex SQL query with prompt: {test_prompt}")
        result = db.execute(query, {"prompt": test_prompt}).fetchone()

        if result and result[0]:
            response_text = result[0]
            logger.info(f"✅ Cortex response received: {response_text[:100]}...")

            return {
                "status": "success",
                "message": "Cortex is working correctly via SQL",
                "response": response_text,
                "method": "SNOWFLAKE.CORTEX.COMPLETE",
                "model": "claude-3-5-sonnet",
            }
        else:
            logger.error("❌ Empty response from Cortex")
            return {
                "status": "error",
                "message": "Received empty response from Cortex",
                "response": None,
            }

    except Exception as e:
        logger.error(f"❌ Cortex test failed: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to call Cortex: {str(e)}",
            "error_type": type(e).__name__,
            "response": None,
        }


@router.get("/test-secrets")
async def test_secrets():
    """
    Test Snowflake secrets access.
    Validates that secrets can be retrieved from Snowflake SPCS or environment.
    """
    logger.info("Testing Snowflake secrets access")

    try:
        results = {"status": "success", "secrets": {}}

        # Check SERPER_API_KEY from different sources
        # Check SPCS path
        spcs_path = "/secrets/serper/secret_string"
        spcs_secret = None
        if os.path.exists(spcs_path):
            with open(spcs_path, "r") as f:
                spcs_secret = f.read().strip()

        # Check local flat file (simple)
        local_flat_path = _LOCAL_SECRETS_DIR / "SERPER_API_KEY"
        local_flat_secret = None
        if local_flat_path.exists() and local_flat_path.is_file():
            local_flat_secret = local_flat_path.read_text().strip()

        # Check local nested path (SPCS-compatible)
        local_nested_path = _LOCAL_SECRETS_DIR / "serper" / "secret_string"
        local_nested_secret = None
        if local_nested_path.exists():
            local_nested_secret = local_nested_path.read_text().strip()

        # Also check environment variable for comparison
        env_var = os.getenv("SERPER_API_KEY")

        if spcs_secret:
            results["secrets"]["SERPER_API_KEY"] = {
                "found": True,
                "source": "SPCS secret file",
                "path": spcs_path,
                "length": len(spcs_secret),
                "preview": f"{spcs_secret[:4]}****" if len(spcs_secret) > 4 else "****",
            }
            logger.info(f"✅ SERPER_API_KEY found via SPCS secret: {spcs_secret[:4]}****")
        elif local_flat_secret:
            results["secrets"]["SERPER_API_KEY"] = {
                "found": True,
                "source": "local flat file",
                "path": str(local_flat_path),
                "length": len(local_flat_secret),
                "preview": f"{local_flat_secret[:4]}****" if len(local_flat_secret) > 4 else "****",
            }
            logger.info(f"✅ SERPER_API_KEY found via local flat file: {local_flat_secret[:4]}****")
        elif local_nested_secret:
            results["secrets"]["SERPER_API_KEY"] = {
                "found": True,
                "source": "local nested file (SPCS-compatible)",
                "path": str(local_nested_path),
                "length": len(local_nested_secret),
                "preview": f"{local_nested_secret[:4]}****" if len(local_nested_secret) > 4 else "****",
            }
            logger.info(f"✅ SERPER_API_KEY found via local nested file: {local_nested_secret[:4]}****")
        elif env_var:
            results["secrets"]["SERPER_API_KEY"] = {
                "found": True,
                "source": "environment variable (fallback)",
                "length": len(env_var),
                "preview": f"{env_var[:4]}****" if len(env_var) > 4 else "****",
            }
            logger.info(f"✅ SERPER_API_KEY found via environment variable: {env_var[:4]}****")
        else:
            results["secrets"]["SERPER_API_KEY"] = {"found": False, "source": None}
            logger.warning("❌ SERPER_API_KEY not found in SPCS secrets, local secrets, or environment")

        # Add debug info about SPCS secrets directory
        spcs_secrets_dir = "/secrets"
        if os.path.exists(spcs_secrets_dir):
            results["spcs_secrets_directory"] = {
                "exists": True,
                "path": spcs_secrets_dir,
                "contents": os.listdir(spcs_secrets_dir) if os.path.isdir(spcs_secrets_dir) else "not a directory",
            }
        else:
            results["spcs_secrets_directory"] = {"exists": False, "path": spcs_secrets_dir}

        # Add debug info about local secrets directory
        local_secrets_dir = str(_LOCAL_SECRETS_DIR)
        if _LOCAL_SECRETS_DIR.exists():
            # Filter out git files from contents
            ignored_files = {".gitkeep", ".gitignore"}
            contents = [
                f for f in os.listdir(local_secrets_dir)
                if f not in ignored_files
            ] if _LOCAL_SECRETS_DIR.is_dir() else "not a directory"
            results["local_secrets_directory"] = {
                "exists": True,
                "path": local_secrets_dir,
                "contents": contents,
            }
        else:
            results["local_secrets_directory"] = {"exists": False, "path": local_secrets_dir}

        return results

    except Exception as e:
        logger.error(f"❌ Secrets test failed: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to test secrets: {str(e)}",
            "error_type": type(e).__name__,
        }


@router.get("/test-serper")
async def test_serper():
    """
    Test Serper API connection directly.
    Makes a simple search request to verify the external access integration is working.
    """
    logger.info("Testing Serper API connection")

    try:
        import requests

        api_key = get_serper_api_key()

        if not api_key:
            logger.error("❌ SERPER_API_KEY not found in SPCS secrets or environment")
            return {
                "status": "error",
                "message": "SERPER_API_KEY not found in SPCS secrets or environment variables",
                "response": None,
            }

        logger.info(f"✅ API Key found: {api_key[:4]}****")

        url = "https://google.serper.dev/search"
        payload = json.dumps({"q": "artificial intelligence"})
        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }

        logger.info("Sending request to Serper API...")
        response = requests.post(url, headers=headers, data=payload, timeout=30)

        logger.info(f"✅ Serper API responded with status: {response.status_code}")

        try:
            response_json = response.json()

            if response.status_code == 200:
                results_count = len(response_json.get("organic", []))
                logger.info(f"✅ Serper search successful! Found {results_count} results")

                return {
                    "status": "success",
                    "message": "Serper API is working correctly",
                    "http_status": response.status_code,
                    "results_count": results_count,
                    "search_query": "artificial intelligence",
                    "response_preview": response_json.get("organic", [])[0] if results_count > 0 else None,
                    "full_response": response_json,
                }
            else:
                logger.error(f"❌ Serper API returned error status: {response.status_code}")
                return {
                    "status": "error",
                    "message": f"Serper API returned error status: {response.status_code}",
                    "http_status": response.status_code,
                    "response": response_json,
                }
        except json.JSONDecodeError as je:
            logger.error(f"❌ Failed to parse Serper response as JSON: {str(je)}")
            return {
                "status": "error",
                "message": "Failed to parse Serper response as JSON",
                "http_status": response.status_code,
                "raw_response": response.text[:500],
            }

    except Exception as e:
        logger.error(f"❌ Serper test failed: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to call Serper API: {str(e)}",
            "error_type": type(e).__name__,
            "response": None,
        }


@router.get("/test-litellm")
async def test_litellm():
    """
    Test LiteLLM connection using LLM handler.
    This tests the complete LiteLLM/REST API path.
    """
    logger.info("Testing LiteLLM connection")

    try:
        llm = get_llm(provider="snowflake", model="claude-3-5-sonnet")
        logger.info(f"✅ LLM instance created: {llm}")

        test_prompt = "Say 'Hello, LiteLLM is working!' in exactly those words."

        logger.info(f"Calling LLM with prompt: {test_prompt}")

        response = llm.call([{"role": "user", "content": test_prompt}])

        logger.info(f"✅ LiteLLM response received {response}")

        if hasattr(response, "content"):
            response_text = response.content
        elif isinstance(response, dict) and "content" in response:
            response_text = response["content"]
        elif hasattr(response, "choices") and len(response.choices) > 0:
            response_text = response.choices[0].message.content
        else:
            response_text = str(response)

        logger.info(f"Response text: {response_text[:100]}...")

        return {
            "status": "success",
            "message": "LiteLLM is working correctly",
            "response": response_text,
            "method": "LiteLLM (lite_llm_handler)",
            "model": "claude-3-5-sonnet",
            "llm_type": str(type(llm).__name__),
        }

    except Exception as e:
        logger.error(f"❌ LiteLLM test failed: {str(e)}", exc_info=True)

        error_details = {
            "status": "error",
            "message": f"Failed to call LiteLLM: {str(e)}",
            "error_type": type(e).__name__,
            "response": None,
        }

        if hasattr(e, "status_code"):
            error_details["status_code"] = e.status_code
        if hasattr(e, "response"):
            error_details["api_response"] = str(e.response)[:500]

        return error_details
