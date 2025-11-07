"""
Unified LLM service for BlendX Core.

Provides a unified interface for working with Snowflake Cortex and OpenAI LLMs, including custom LiteLLM integration, embedding support, and authentication management. Supports both synchronous and asynchronous usage, and exposes utility functions for agent and embedder creation.
"""

import json
import logging
import os
import time
from functools import lru_cache
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Union

import aiohttp
import litellm
import requests
from chromadb import Documents, EmbeddingFunction, Embeddings
from crewai.llm import LLM
from litellm import CustomLLM
from snowflake.snowpark import Session

from settings import  Settings, get_settings
# from app.services.llm_tracking_service import (
#     get_llm_tracking_service,
#     setup_litellm_tracking,
# )
from jwt_generator_service import JWTGenerator

# Configure logging
logger = logging.getLogger(__name__)


class TrackedLLM(LLM):
    """
    Wrapper around CrewAI's LLM class to ensure all calls are tracked.
    This ensures we capture LLM calls that might not go through LiteLLM callbacks.

    Note: We don't override call() to preserve function calling support.
    Tracking is done via LiteLLM callbacks instead.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
      #  self._tracking_service = get_llm_tracking_service()

    def _extract_provider_from_model(self, model: str) -> str:
        """Extract provider from model name"""
        if not model:
            return "unknown"

        model_lower = model.lower()

        # Snowflake Cortex models
        if (
            model_lower.startswith("snowflake/")
            or model_lower.startswith("cortex/")
            or model_lower
            in [
                "claude-3-5-sonnet",
                "claude-3-5-haiku",
                "claude-3-opus",
                "claude-3-sonnet",
                "claude-3-haiku",
            ]
        ):
            return "snowflake"

        # OpenAI models
        elif model_lower.startswith("openai/") or model_lower in [
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4-turbo-preview",
            "gpt-4o",
            "gpt-4o-mini",
        ]:
            return "openai"

        # Anthropic models (direct API calls)
        elif model_lower.startswith("anthropic/"):
            return "anthropic"

        # Azure OpenAI
        elif model_lower.startswith("azure/"):
            return "azure"

        else:
            return "unknown"


# Define our own exception class since imports might vary
class BaseLLMException(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class SnowflakeLitellmService(CustomLLM):
    """
    Custom LiteLLM service for Snowflake Cortex API
    Based on your original implementation but integrated
    """

    def __init__(
        self,
        base_url: str,
        snowflake_account: Optional[str] = None,
        snowflake_service_user: Optional[str] = None,
        snowflake_authmethod: Optional[str] = "oauth",
        snowflake_token_path: Optional[str] = "/snowflake/session/token",
        privatekey_password: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stop: Optional[Union[str, List[str]]] = None,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
        format_messages_callback: Optional[Any] = None,
        callbacks: List[Any] = [],
        generate_id_function: Optional[Any] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        self.base_url = base_url
        self.snowflake_account = snowflake_account
        self.snowflake_service_user = snowflake_service_user
        # Normalize authmethod: "private_key" is an alias for "jwt"
        self.snowflake_authmethod = (
            "jwt" if snowflake_authmethod == "private_key" else snowflake_authmethod
        )
        self.snowflake_token_path = snowflake_token_path
        self.privatekey_password = privatekey_password
        self.temperature = temperature
        self.top_p = top_p
        self.stop = stop
        self.max_tokens = max_tokens
        self.api_key = api_key
        self.format_messages_callback = format_messages_callback
        self.callbacks = callbacks
        self.generate_id_function = generate_id_function
        self.response_format = response_format
        self.kwargs = kwargs
  #      self._tracking_service = get_llm_tracking_service()

        super().__init__()
        self._validate_environment()

    def _validate_environment(self):
        """Validates input parameters"""
        if self.snowflake_authmethod == "jwt":
            if (
                not self.snowflake_account
                or not self.snowflake_service_user
                or not self.api_key
            ):
                raise BaseLLMException(
                    status_code=500,
                    message="JWT auth method needs snowflake_account "
                    "snowflake_service_user and api_key to be set.",
                )
            # format api key
            self.api_key = self.api_key.replace("\\n", "\n").strip()

    def _execute_pre_callback(self, messages: list) -> List[Dict[str, str]]:
        """Execute callback format function for messages"""
        if self.format_messages_callback:
            return self.format_messages_callback(messages=messages)
        else:
            return messages

    def _execute_post_callbacks(self, messages: list):
        """Execute callbacks function for result messages"""
        if self.callbacks:
            for callback in self.callbacks:
                callback(messages=messages)

    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Returns the appropriate headers based on the selected authentication method.
        For "oauth", it reads the token from '/snowflake/session/token'.
        For "jwt", it uses JWTGenerator to generate a token from the provided private key.
        """
        if self.snowflake_authmethod == "oauth" and self.snowflake_token_path:
            try:
                logger.info(
                    f"🔐 Attempting OAuth authentication from {self.snowflake_token_path}"
                )
                with open(self.snowflake_token_path, "r") as f:
                    oauth_token = f.read().strip()

                headers = {
                    "Authorization": f"Bearer {oauth_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Snowflake-Authorization-Token-Type": "OAUTH",
                }
                logger.info("✅ Using OAuth token from container")
                return headers
            except FileNotFoundError:
                logger.warning(
                    f"OAuth token file not found at {self.snowflake_token_path}"
                )
                logger.info("Falling back to JWT authentication")
                # Fall through to JWT authentication

        # Use JWT (key pair) authentication
        try:
            logger.info(
                f"🔐 Attempting JWT authentication for account: {self.snowflake_account}, user: {self.snowflake_service_user}"
            )
            bearerToken = JWTGenerator(
                account=self.snowflake_account,
                user=self.snowflake_service_user,
                private_key_string=self.api_key,
                passphrase=self.privatekey_password,
            ).get_token()

            headers = {
                "Authorization": f"Bearer {bearerToken}",
                "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            }
            logger.info("✅ Using JWT authentication")
            return headers
        except Exception as e:
            logger.error(f"Failed to generate JWT token: {e}")
            logger.error(
                f"Account: {self.snowflake_account}, User: {self.snowflake_service_user}"
            )
            logger.error(f"API Key present: {bool(self.api_key)}")
            raise BaseLLMException(
                status_code=500, message=f"Authentication failed: {str(e)}"
            )

    def _process_sync_response(self, response: requests.Response):
        """Process streaming response. HTTP API only supports streaming."""
        accumulated_content = ""
        total_prompt_tokens = 0
        total_completion_tokens = 0

        try:
            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    logger.debug(f"Received line: {line_str}")

                    if line_str.startswith("data:"):
                        event_data = line_str[len("data:") :].strip()

                        # Skip [DONE] events
                        if event_data == "[DONE]":
                            continue

                        try:
                            parsed_data = json.loads(event_data)

                            # Extract content from 'choices' and accumulate it
                            if (
                                "choices" in parsed_data
                                and len(parsed_data["choices"]) > 0
                            ):
                                choice = parsed_data["choices"][0]

                                # Handle both 'delta' (streaming) and 'message' formats
                                if "delta" in choice:
                                    content = choice["delta"].get("content", "")
                                elif "message" in choice:
                                    content = choice["message"].get("content", "")
                                else:
                                    content = ""

                                if content:
                                    accumulated_content += content

                            # Update token usage
                            if "usage" in parsed_data:
                                usage = parsed_data["usage"]
                                total_prompt_tokens += usage.get("prompt_tokens", 0)
                                total_completion_tokens += usage.get(
                                    "completion_tokens", 0
                                )

                        except json.JSONDecodeError:
                            logger.warning(f"Error decoding event data: {event_data}")
        except Exception as e:
            logger.error(f"Error processing response: {e}")

        final_response = accumulated_content.strip()
        logger.info(f"Final response length: {len(final_response)}")
        return total_prompt_tokens, total_completion_tokens, final_response

    def _create_payload(self, model, messages) -> dict:
        """Creates payload based on input parameters"""
        payload = {"model": model, "messages": self._execute_pre_callback(messages)}

        if self.top_p:
            payload["top_p"] = self.top_p

        if self.temperature:
            payload["temperature"] = self.temperature

        if self.max_tokens:
            payload["max_tokens"] = self.max_tokens

        # Format response_format according to Snowflake's requirements
        if self.response_format:
            payload["response_format"] = {
                "type": "json",
                "schema": self.response_format,
            }

        return payload

    def _create_response(
        self,
        model: str,
        formatted_answer: Any,
        total_prompt_tokens: int,
        total_completion_tokens: int,
    ):
        identifier = ""
        if self.generate_id_function:
            identifier = self.generate_id_function()
        else:
            identifier = str(int(time.time() * 1000))

        json_response = {
            "id": f"chatcmpl-{identifier}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "finish_reason": "stop",
                    "index": 0,
                    "message": {
                        "content": str(formatted_answer),
                        "role": "assistant",
                    },
                }
            ],
            "usage": {
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_prompt_tokens + total_completion_tokens,
            },
        }

        return litellm.ModelResponse(
            object=json_response["object"],
            choices=json_response["choices"],
            id=json_response["id"],
            created=json_response["created"],
            model=json_response["model"],
            usage=json_response["usage"],
        )

    def completion(
        self,
        model: str,
        timeout: float,
        messages: list = [],
        headers: Optional[Dict[str, str]] = None,
        logging_obj=None,
        **kwargs,
    ) -> litellm.ModelResponse:
        """Handle completion request"""
        logger.info(
            f"🚀 Snowflake LLM Request - Model: {model}, Messages: {len(messages)}"
        )

        try:
            payload = self._create_payload(model, messages)
            logger.debug(f"Payload: {payload}")

            if not headers:
                headers = self._get_auth_headers()

            if logging_obj:
                logging_obj.pre_call(
                    input=messages,
                    api_key=self.api_key,
                    additional_args={
                        "headers": headers,
                        "api_base": self.base_url,
                        "complete_input_dict": payload,
                    },
                )

            logger.info(f"📡 Making request to: {self.base_url}")
            response = requests.post(
                url=self.base_url,
                headers=headers,
                data=json.dumps(payload),
                stream=True,
                timeout=timeout,
            )

            logger.info(f"📥 Response status: {response.status_code}")

            if response.status_code != 200:
                error_text = response.text
                logger.error(f"❌ HTTP Error {response.status_code}: {error_text}")
                logger.error(f"Request URL: {self.base_url}")
                logger.error(f"Request headers: {headers}")
                logger.error(f"Request payload: {payload}")
                raise BaseLLMException(
                    status_code=response.status_code,
                    message=f"HTTP {response.status_code}: {error_text}",
                )

            try:
                # Check if the response is a valid event-stream
                response_content_type = response.headers.get("Content-Type")
                if (
                    response_content_type
                    and "text/event-stream" in response_content_type
                ):
                    total_prompt_tokens, total_completion_tokens, final_response = (
                        self._process_sync_response(response)
                    )
                else:
                    # Handle non-event-stream responses
                    try:
                        response_data = response.json()
                        final_response = response_data
                        # Set default token counts if not in response
                        total_prompt_tokens = 0
                        total_completion_tokens = 0
                    except:
                        final_response = response.text
                        total_prompt_tokens = 0
                        total_completion_tokens = 0

                if logging_obj:
                    logging_obj.post_call(
                        api_key=self.api_key,
                        original_response=response,
                        additional_args={
                            "headers": headers,
                            "api_base": self.base_url,
                        },
                    )

                self._execute_post_callbacks(messages)

            finally:
                response.close()

            if not final_response or (
                isinstance(final_response, str) and final_response.strip() == ""
            ):
                logger.error("❌ Empty response from Snowflake LLM")
                raise BaseLLMException(
                    status_code=500, message="Empty response from Snowflake LLM"
                )

            logger.info("✅ Snowflake LLM request completed successfully")

            # Track the LLM call
            try:
                # Clean model name by removing custom-cortex-llm prefix if present
                clean_model = model
                if clean_model.startswith("custom-cortex-llm/"):
                    clean_model = clean_model[18:]  # Remove "custom-cortex-llm/" prefix

                self._tracking_service.track_llm_call(
                    model=clean_model,
                    provider="snowflake",
                    input_tokens=total_prompt_tokens,
                    output_tokens=total_completion_tokens,
                    call_type="completion",
                    cost_usd=None,  # Snowflake doesn't provide cost info
                    chat_id=None,  # Will be set by specific services
                    message_id=None,  # Will be set by specific services
                    feature=None,  # Will be set by specific services
                )
            except Exception as tracking_error:
                logger.error(f"Failed to track Snowflake LLM call: {tracking_error}")

            return self._create_response(
                model=model,
                formatted_answer=final_response,
                total_prompt_tokens=total_prompt_tokens,
                total_completion_tokens=total_completion_tokens,
            )

        except Exception as e:
            logger.error(f"❌ Error in completion: {str(e)}")
            if isinstance(e, BaseLLMException):
                raise
            raise BaseLLMException(status_code=500, message=str(e))


class SnowflakeEmbedder(EmbeddingFunction):
    """Snowflake Cortex embedder for ChromaDB"""

    def __init__(self, session: Session, model: str = "snowflake-arctic-embed-m"):
        self.session = session
        self.model = model
        logger.info(f"SnowflakeEmbedder initialized with model: {model}")

    def __call__(self, input: Documents) -> Embeddings:
        """Generate embeddings for documents"""
        logger.info(f"Generating embeddings for {len(input)} documents")
        embeddings = []

        for text in input:
            escaped_text = text.replace("'", "''")
            sql_query = f"SELECT SNOWFLAKE.CORTEX.EMBED_TEXT_768('{self.model}', '{escaped_text}') AS embedding"

            try:
                result = self.session.sql(sql_query).collect()
                if result and result[0]["EMBEDDING"]:
                    embedding_data = result[0]["EMBEDDING"]
                    embedding_vector = (
                        json.loads(embedding_data)
                        if isinstance(embedding_data, str)
                        else embedding_data
                    )
                    embeddings.append(embedding_vector)
                else:
                    embeddings.append([0.0] * 768)
            except Exception as e:
                logger.error(f"Embedding error: {str(e)}")
                embeddings.append([0.0] * 768)

        return embeddings


class UnifiedLLMService:
    """Unified service for LLM and embedder instances"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._snowflake_session = None
        self._snowflake_service = None
  #      self._tracking_service = get_llm_tracking_service()

        # Setup LiteLLM tracking
      #  setup_litellm_tracking()

    def _get_snowflake_session(self) -> Session:
        """Get or create Snowflake session"""
        if self._snowflake_session is None:
            if self.settings.environment.upper() in [
                "DEVELOPMENT",
                "SHARED",
                "STAGING",
                "PRODUCTION",
                "UAT",
            ]:
                # OAuth authentication for containers
                try:
                    with open("/snowflake/session/token", "r") as token_file:
                        oauth_token = token_file.read().strip()

                    session_config = {
                        "account": self.settings.snowflake_account,
                        "authenticator": "oauth",
                        "token": oauth_token,
                        "warehouse": self.settings.snowflake_warehouse,
                        "database": self.settings.snowflake_database,
                        "schema": self.settings.snowflake_schema,
                    }

                    if self.settings.snowflake_role:
                        session_config["role"] = self.settings.snowflake_role

                    self._snowflake_session = Session.builder.configs(
                        session_config
                    ).create()
                except FileNotFoundError:
                    logger.info(
                        "OAuth token file not found, using password authentication"
                    )
                    # Fall back to password auth for local development
                    session_config = {
                        "account": self.settings.snowflake_account,
                        "user": self.settings.snowflake_user,
                        "password": self.settings.snowflake_password,
                        "warehouse": self.settings.snowflake_warehouse,
                        "database": self.settings.snowflake_database,
                        "schema": self.settings.snowflake_schema,
                    }

                    if self.settings.snowflake_role:
                        session_config["role"] = self.settings.snowflake_role

                    self._snowflake_session = Session.builder.configs(
                        session_config
                    ).create()
            else:
                # Username/password authentication for local development
                session_config = {
                    "account": self.settings.snowflake_account,
                    "user": self.settings.snowflake_user,
                    "password": self.settings.snowflake_password,
                    "warehouse": self.settings.snowflake_warehouse,
                    "database": self.settings.snowflake_database,
                    "schema": self.settings.snowflake_schema,
                }

                if self.settings.snowflake_role:
                    session_config["role"] = self.settings.snowflake_role

                self._snowflake_session = Session.builder.configs(
                    session_config
                ).create()

        return self._snowflake_session

    def get_llm(self, provider: str = None, model: str = None, **kwargs) -> LLM:
        """
        Get LLM instance based on provider.
        Uses global settings if provider/model not specified.

        Args:
            provider: LLM provider ("snowflake", "cortex", "openai"). If None, uses global setting.
            model: Model name. If None, uses global setting.
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
        """
        # Use global settings if not specified
        if provider is None:
            provider = self.settings.llm_provider.value
            logger.info(f"🔧 Using global LLM provider: {provider}")

        if model is None:
            model = self.settings.llm_model_name
            logger.info(f"🔧 Using global LLM model: {model}")

        if provider.lower() == "cortex" or provider.lower() == "snowflake":
            return self._get_snowflake_llm(model, **kwargs)
        elif provider.lower() == "openai":
            return self._get_openai_llm(model, **kwargs)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def set_execution_context(
        self,
        execution_group_id: Optional[str] = None,
        flow_execution_id: Optional[str] = None,
        crew_execution_id: Optional[str] = None,
        agent_execution_id: Optional[str] = None,
    ):
        """Set the current execution context for LLM tracking"""
        self._tracking_service.set_execution_context(
            execution_group_id=execution_group_id,
            flow_execution_id=flow_execution_id,
            crew_execution_id=crew_execution_id,
            agent_execution_id=agent_execution_id,
        )

    def clear_execution_context(self):
        """Clear the current execution context"""
        self._tracking_service.clear_execution_context()

    def log_llm_summary(
        self,
        execution_group_id: Optional[str] = None,
        flow_execution_id: Optional[str] = None,
    ) -> None:
        """Log LLM usage summary"""
        stats = self._tracking_service.get_summary_stats(
            execution_group_id=execution_group_id, flow_execution_id=flow_execution_id
        )

        if stats["total_calls"] > 0:
            logger.info(
                f"LLM Usage Summary - Calls: {stats['total_calls']}, "
                f"Input Tokens: {stats['total_input_tokens']}, "
                f"Output Tokens: {stats['total_output_tokens']}, "
                f"Total Tokens: {stats['total_tokens']}, "
                f"Models: {', '.join(stats['models_used'])}, "
                f"Providers: {', '.join(stats['providers_used'])}"
            )
        else:
            logger.info("No LLM calls tracked for this workflow")

    def get_llm_summary_stats(
        self,
        execution_group_id: Optional[str] = None,
        flow_execution_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get summary statistics for LLM calls"""
        return self._tracking_service.get_summary_stats(
            execution_group_id=execution_group_id, flow_execution_id=flow_execution_id
        )

    def get_embedder(
        self, provider: str = None, model: str = None, **kwargs
    ) -> EmbeddingFunction:
        """
        Get embedder instance based on provider.
        Uses global settings if provider/model not specified.

        Args:
            provider: Embedding provider ("snowflake", "cortex", "openai"). If None, uses global setting.
            model: Model name. If None, uses global setting.
            **kwargs: Additional parameters

        Returns:
            EmbeddingFunction instance
        """
        # Use global settings if not specified
        if provider is None:
            provider = self.settings.embedding_provider.value
            logger.info(f"🔧 Using global embedding provider: {provider}")

        if model is None:
            model = self.settings.embedding_model_name
            logger.info(f"🔧 Using global embedding model: {model}")

        if provider.lower() == "cortex" or provider.lower() == "snowflake":
            return self._get_snowflake_embedder(model, **kwargs)
        elif provider.lower() == "openai":
            return self._get_openai_embedder(model, **kwargs)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def get_embedder_config(
        self, provider: str = None, model: str = None, **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Get embedder configuration for CrewAI. Uses global settings if provider/model not specified.

        Args:
            provider: Embedding provider. If None, uses global setting.
            model: Model name. If None, uses global setting.
            **kwargs: Additional parameters

        Returns:
            Dict with embedder configuration for CrewAI, or None for OpenAI (uses native)
        """
        # Use global settings if not specified
        if provider is None:
            provider = self.settings.embedding_provider.value

        if model is None:
            model = self.settings.embedding_model_name

        logger.info(
            f"🔧 Creating embedder config for provider: {provider}, model: {model}"
        )

        if provider.lower() == "cortex" or provider.lower() == "snowflake":
            # Get the actual embedder instance
            embedder_instance = self._get_snowflake_embedder(model, **kwargs)
            # Return CrewAI format for custom embedder
            config = {
                "provider": "custom",
                "config": {"embedder": embedder_instance},
            }
            logger.info(f"🔧 Returning Snowflake custom config")
            return config
        elif provider.lower() == "openai":
            # For OpenAI, return None so CrewAI uses its native embedder
            logger.info(f"🔧 Returning None for OpenAI (uses native embedder)")
            return None
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _get_snowflake_llm(self, model: str, **kwargs) -> TrackedLLM:
        """Create Snowflake Cortex LLM instance"""
        # Get or create the Snowflake service instance
        if self._snowflake_service is None:
            # Try to get from settings first, fallback to SQL query
            account = self.settings.snowflake_account
            user = self.settings.snowflake_service_user or self.settings.snowflake_user
            host = self.settings.snowflake_host

            # If account or user not set in settings, get from Snowflake session
            if not account or not user:
                logger.info("Account or user not set in settings, retrieving from Snowflake session")
                session = self._get_snowflake_session()
                account_info = session.sql("SELECT CURRENT_ACCOUNT(), CURRENT_USER(), CURRENT_REGION()").collect()

                if not account:
                    account = account_info[0][0]  # CURRENT_ACCOUNT()
                if not user:
                    user = account_info[0][1]     # CURRENT_USER()

                # Construct host from account and region if not set
                if not host:
                    region = account_info[0][2]   # CURRENT_REGION()
                    host = f"{account}.{region}.snowflakecomputing.com"

                logger.info(f"Retrieved from Snowflake - Account: {account}, User: {user}")

            # Use SNOWFLAKE_URL if provided (respecting HTTP/HTTPS as configured)
            if hasattr(self.settings, "snowflake_url") and self.settings.snowflake_url:
                base_url = self.settings.snowflake_url
                logger.info(f"Using configured SNOWFLAKE_URL: {base_url}")
            else:
                # Default construction - use HTTPS unless specifically configured otherwise
                base_url = f"https://{host}/api/v2/cortex/inference:complete"
                logger.info(f"Using constructed URL: {base_url}")

            # Determine auth method
            authmethod = getattr(self.settings, "snowflake_authmethod", "oauth")

            # Normalize authmethod: "private_key" is an alias for "jwt"
            if authmethod == "private_key":
                authmethod = "jwt"

            # Get private key if using JWT
            private_key = None

            # Check if OAuth token file exists
            oauth_available = os.path.exists("/snowflake/session/token")

            # For local development without token file, try to use JWT if private key is available
            if authmethod == "oauth" and not oauth_available:
                # Check if we have a private key available for JWT fallback
                has_private_key = (
                    hasattr(self.settings, "private_key") and self.settings.private_key
                ) or (
                    hasattr(self.settings, "snowflake_private_key_path")
                    and self.settings.snowflake_private_key_path
                )

                if has_private_key:
                    authmethod = "jwt"
                    logger.info(
                        "OAuth requested but no token file found, using JWT for local development"
                    )
                else:
                    raise ValueError(
                        "OAuth token file not found at /snowflake/session/token and no private key "
                        "configured for JWT authentication. Please set SNOWFLAKE_PRIVATE_KEY_PATH "
                        "or ensure the OAuth token file exists."
                    )

            if authmethod == "jwt":
                if hasattr(self.settings, "private_key") and self.settings.private_key:
                    private_key = self.settings.private_key
                elif (
                    hasattr(self.settings, "snowflake_private_key_path")
                    and self.settings.snowflake_private_key_path
                ):
                    try:
                        with open(self.settings.snowflake_private_key_path, "r") as f:
                            private_key = f.read()
                        logger.info(
                            f"✅ Loaded private key from {self.settings.snowflake_private_key_path}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to load private key: {e}")
                        raise ValueError(
                            "JWT authentication requires a valid private key"
                        )
                else:
                    raise ValueError(
                        "JWT authentication requires SNOWFLAKE_PRIVATE_KEY_PATH or private_key setting"
                    )

            # Create the Snowflake service instance once and reuse it
            self._snowflake_service = SnowflakeLitellmService(
                base_url=base_url,
                snowflake_account=account,
                snowflake_service_user=user,
                snowflake_authmethod=authmethod,
                api_key=private_key,
                privatekey_password=getattr(
                    self.settings, "snowflake_privatekey_password", None
                ),
                temperature=kwargs.get("temperature", 0.2),
                max_tokens=kwargs.get("max_tokens", 1024),
            )

            # Register custom provider with LiteLLM ONLY ONCE
            litellm.custom_provider_map = [
                {
                    "provider": "custom-cortex-llm",
                    "custom_handler": self._snowflake_service,
                }
            ]
            logger.info("✅ Registered Snowflake custom provider with LiteLLM")

        # Return LLM instance that uses the registered custom provider
        llm_params = {
            "model": f"custom-cortex-llm/{model}",
            "temperature": kwargs.get("temperature", 0.2),
            "max_tokens": kwargs.get("max_tokens", 1024),
        }

        # Add response_format if provided for structured output
        if "response_format" in kwargs:
            llm_params["response_format"] = kwargs["response_format"]

        return TrackedLLM(**llm_params)

    def _get_openai_llm(self, model: str, **kwargs) -> TrackedLLM:
        """Create OpenAI LLM instance with tracking"""
        llm_params = {
            "model": f"openai/{model}",
            "temperature": kwargs.get("temperature", 0.2),
            "max_tokens": kwargs.get("max_tokens", 1024),
        }

        # Add response_format if provided for structured output
        if "response_format" in kwargs:
            llm_params["response_format"] = kwargs["response_format"]

        return TrackedLLM(**llm_params)

    def _get_snowflake_embedder(self, model: str, **kwargs) -> SnowflakeEmbedder:
        """Create Snowflake embedder instance"""
        session = self._get_snowflake_session()
        return SnowflakeEmbedder(session, model)

    def _get_openai_embedder(self, model: str, **kwargs) -> EmbeddingFunction:
        """Create OpenAI embedder instance"""
        from chromadb.utils import embedding_functions

        # Get API key from settings or kwargs
        api_key = kwargs.get("api_key") or getattr(
            self.settings, "openai_api_key", None
        )

        if not api_key:
            raise ValueError(
                "OpenAI API key is required for OpenAI embeddings. "
                "Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )

        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=api_key, model_name=model
        )

    def close(self):
        """Close resources"""
        if self._snowflake_session:
            self._snowflake_session.close()
            self._snowflake_session = None

        # Clear the service instance
        self._snowflake_service = None


# Global service instance
_unified_service = None


@lru_cache()
def get_unified_llm_service() -> UnifiedLLMService:
    """Get singleton instance of UnifiedLLMService"""
    global _unified_service
    if _unified_service is None:
        settings = get_settings()
        _unified_service = UnifiedLLMService(settings)
    return _unified_service


# Simple individual methods that auto-use global settings
def get_llm(provider: str = None, model: str = None, **kwargs) -> LLM:
    """
    Get LLM instance. Uses global settings if provider/model not specified.

    Args:
        provider: LLM provider. If None, uses global setting.
        model: Model name. If None, uses global setting.
        **kwargs: Additional parameters (temperature, max_tokens, etc.)

    Returns:
        LLM instance

    Examples:
        llm = get_llm()  # Uses global config
        llm = get_llm("openai")  # Uses OpenAI with global model
        llm = get_llm("snowflake", "claude-3-5-sonnet")  # Specific
        llm = get_llm(temperature=0.5)  # Global config + custom params
    """
    service = get_unified_llm_service()
    return service.get_llm(provider, model, **kwargs)


def set_llm_execution_context(
    execution_group_id: Optional[str] = None,
    flow_execution_id: Optional[str] = None,
    crew_execution_id: Optional[str] = None,
    agent_execution_id: Optional[str] = None,
):
    """Set the current execution context for LLM tracking"""
    service = get_unified_llm_service()
    service.set_execution_context(
        execution_group_id=execution_group_id,
        flow_execution_id=flow_execution_id,
        crew_execution_id=crew_execution_id,
        agent_execution_id=agent_execution_id,
    )


def clear_llm_execution_context():
    """Clear the current execution context"""
    service = get_unified_llm_service()
    service.clear_execution_context()


def log_llm_summary(
    execution_group_id: Optional[str] = None, flow_execution_id: Optional[str] = None
) -> None:
    """Log LLM usage summary"""
    service = get_unified_llm_service()
    service.log_llm_summary(
        execution_group_id=execution_group_id, flow_execution_id=flow_execution_id
    )


def get_llm_summary_stats(
    execution_group_id: Optional[str] = None, flow_execution_id: Optional[str] = None
) -> Dict[str, Any]:
    """Get summary statistics for LLM calls"""
    service = get_unified_llm_service()
    return service.get_llm_summary_stats(
        execution_group_id=execution_group_id, flow_execution_id=flow_execution_id
    )


def get_embedder(
    provider: str = None, model: str = None, **kwargs
) -> EmbeddingFunction:
    """
    Get embedder instance. Uses global settings if provider/model not specified.

    Args:
        provider: Embedding provider. If None, uses global setting.
        model: Model name. If None, uses global setting.
        **kwargs: Additional parameters

    Returns:
        EmbeddingFunction instance

    Examples:
        embedder = get_embedder()  # Uses global config
        embedder = get_embedder("openai")  # Uses OpenAI with global model
        embedder = get_embedder("snowflake", "snowflake-arctic-embed-l")  # Specific
    """
    service = get_unified_llm_service()
    return service.get_embedder(provider, model, **kwargs)


def get_embedder_config(
    provider: str = None, model: str = None, **kwargs
) -> Optional[Dict[str, Any]]:
    """
    Get embedder configuration for CrewAI. Uses global settings if provider/model not specified.

    Args:
        provider: Embedding provider. If None, uses global setting.
        model: Model name. If None, uses global setting.
        **kwargs: Additional parameters

    Returns:
        Dictionary with provider and config for CrewAI, or None for OpenAI (uses native)

    Examples:
        embedder = get_embedder_config()  # Uses global config
        embedder = get_embedder_config("openai")  # Returns None (uses native)
        embedder = get_embedder_config("snowflake", "snowflake-arctic-embed-l")  # Custom config
    """
    service = get_unified_llm_service()
    return service.get_embedder_config(provider, model, **kwargs)


# Legacy functions for backwards compatibility
def get_llm_for_provider(provider: str = None, model: str = None, **kwargs) -> LLM:
    """Legacy function - use get_llm() instead"""
    return get_llm(provider, model, **kwargs)


def get_embedder_for_provider(
    provider: str = None, model: str = None, **kwargs
) -> Optional[Dict[str, Any]]:
    """Legacy function - use get_embedder_config() instead"""
    return get_embedder_config(provider, model, **kwargs)


def get_crew_embedder_config() -> Optional[Dict[str, Any]]:
    """Get embedder configuration for CrewAI crews based on settings"""
    return get_embedder_config()


def get_global_embedder() -> Optional[Dict[str, Any]]:
    """Get global embedder configuration for backwards compatibility"""
    return get_embedder_config()


# Example usage for agent creation
def create_agent_with_llm(provider: str = None, model: str = None, **agent_kwargs):
    """
    Helper function to create agents with appropriate LLM.
    Uses global settings if provider/model not specified.
    """
    from crewai import Agent

    llm = get_llm(provider, model)

    return Agent(llm=llm, **agent_kwargs)


def create_agent_with_global_config(**agent_kwargs):
    """
    Helper function to create agents using global configuration.
    """
    from crewai import Agent

    llm = get_llm()  # Uses global config

    return Agent(llm=llm, **agent_kwargs)


# Singleton instance for backwards compatibility
def get_snowflake_litellm_service(
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    snowflake_account: Optional[str] = None,
    snowflake_service_user: Optional[str] = None,
    response_format: Optional[Dict[str, Any]] = None,
    snowflake_authmethod: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    privatekey_password: Optional[str] = None,
) -> SnowflakeLitellmService:
    """Backwards compatibility function"""
    return SnowflakeLitellmService(
        base_url=base_url,
        snowflake_account=snowflake_account,
        snowflake_service_user=snowflake_service_user,
        snowflake_authmethod=snowflake_authmethod,
        api_key=api_key,
        privatekey_password=privatekey_password,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=response_format,
    )
