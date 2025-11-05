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
from litellm import CustomLLM
from snowflake.snowpark import Session

from snowflake.jwt_generator_service import JWTGenerator

# Configure logging
logger = logging.getLogger(__name__)


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

                # self._tracking_service.track_llm_call(
                #     model=clean_model,
                #     provider="snowflake",
                #     input_tokens=total_prompt_tokens,
                #     output_tokens=total_completion_tokens,
                #     call_type="completion",
                #     cost_usd=None,  # Snowflake doesn't provide cost info
                #     chat_id=None,  # Will be set by specific services
                #     message_id=None,  # Will be set by specific services
                #     feature=None,  # Will be set by specific services
                # )
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
