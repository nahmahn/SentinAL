import os
import logging
from dataclasses import dataclass
from typing import Any, Literal, TypeVar, overload

from groq import (
	APIError,
	APIResponseValidationError,
	APIStatusError,
	AsyncGroq,
	NotGiven,
	RateLimitError,
	Timeout,
)
from groq.types.chat import ChatCompletion, ChatCompletionToolChoiceOptionParam, ChatCompletionToolParam
from groq.types.chat.completion_create_params import (
	ResponseFormatResponseFormatJsonSchema,
	ResponseFormatResponseFormatJsonSchemaJsonSchema,
)
from httpx import URL
from pydantic import BaseModel

from aeternus.llm.base import BaseChatModel, ChatInvokeCompletion
from aeternus.llm.exceptions import ModelProviderError, ModelRateLimitError
from aeternus.llm.google.chat import ChatGoogle
from aeternus.llm.groq.parser import try_parse_groq_failed_generation
from aeternus.llm.groq.serializer import GroqMessageSerializer
from aeternus.llm.messages import BaseMessage
from aeternus.llm.schema import SchemaOptimizer
from aeternus.llm.views import ChatInvokeUsage

GroqVerifiedModels = Literal[
	'meta-llama/llama-4-maverick-17b-128e-instruct',
	'meta-llama/llama-4-scout-17b-16e-instruct',
	'llama-3.3-70b-versatile',
	'qwen/qwen3-32b',
	'moonshotai/kimi-k2-instruct',
	'openai/gpt-oss-20b',
	'openai/gpt-oss-120b',
]

JsonSchemaModels = [
	'meta-llama/llama-4-maverick-17b-128e-instruct',
	'meta-llama/llama-4-scout-17b-16e-instruct',
	'llama-3.3-70b-versatile',
	'openai/gpt-oss-20b',
	'openai/gpt-oss-120b',
]

ToolCallingModels = [
	'moonshotai/kimi-k2-instruct',
	'llama-3.3-70b-versatile',
]

T = TypeVar('T', bound=BaseModel)

logger = logging.getLogger(__name__)


@dataclass
class ChatGroq(BaseChatModel):
	"""
	A wrapper around AsyncGroq that implements the BaseLLM protocol.
	"""

	# Model configuration
	model: GroqVerifiedModels | str

	# Model params
	temperature: float | None = None
	service_tier: Literal['auto', 'on_demand', 'flex'] | None = None
	top_p: float | None = None
	seed: int | None = None

	# Client initialization parameters
	api_key: str | None = None
	base_url: str | URL | None = None
	timeout: float | Timeout | NotGiven | None = None
	max_retries: int = 10  # Increase default retries for automation reliability

	def get_client(self) -> AsyncGroq:
		return AsyncGroq(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout, max_retries=self.max_retries)

	@property
	def provider(self) -> str:
		return 'groq'

	@property
	def name(self) -> str:
		return str(self.model)

	def _get_usage(self, response: ChatCompletion) -> ChatInvokeUsage | None:
		usage = (
			ChatInvokeUsage(
				prompt_tokens=response.usage.prompt_tokens,
				completion_tokens=response.usage.completion_tokens,
				total_tokens=response.usage.total_tokens,
				prompt_cached_tokens=None,  # Groq doesn't support cached tokens
				prompt_cache_creation_tokens=None,
				prompt_image_tokens=None,
			)
			if response.usage is not None
			else None
		)
		return usage

	@overload
	async def ainvoke(
		self, messages: list[BaseMessage], output_format: None = None, **kwargs: Any
	) -> ChatInvokeCompletion[str]: ...

	@overload
	async def ainvoke(self, messages: list[BaseMessage], output_format: type[T], **kwargs: Any) -> ChatInvokeCompletion[T]: ...

	async def ainvoke(
		self, messages: list[BaseMessage], output_format: type[T] | None = None, **kwargs: Any
	) -> ChatInvokeCompletion[T] | ChatInvokeCompletion[str]:
		groq_messages = GroqMessageSerializer.serialize_messages(messages)

		try:
			if output_format is None:
				return await self._invoke_regular_completion(groq_messages)
			else:
				return await self._invoke_structured_output(groq_messages, output_format)

		except RateLimitError as e:
			logger.warning(f'Groq rate limit hit, falling back to Gemini: {e}')
			return await self._fallback_to_gemini(messages, output_format, **kwargs)

		except APIResponseValidationError as e:
			# Validation error means the model output itself was bad - might still want fallback
			logger.warning(f'Groq response validation error, falling back to Gemini: {e}')
			return await self._fallback_to_gemini(messages, output_format, **kwargs)

		except APIStatusError as e:
			# For common error codes or any status error, try fallback
			if e.status_code in {401, 429, 500, 502, 503, 504}:
				logger.warning(f'Groq API status error {e.status_code}, falling back to Gemini: {e.response.text}')
				return await self._fallback_to_gemini(messages, output_format, **kwargs)

			# If it's a 400 Bad Request but we have structured output, it might be recoverable via manual parsing
			if output_format is not None:
				try:
					logger.debug(f'Groq failed generation ({e.status_code}): {e.response.text}; trying manual parsing fallback')
					parsed_response = try_parse_groq_failed_generation(e, output_format)
					return ChatInvokeCompletion(
						completion=parsed_response,
						usage=None,
					)
				except Exception:
					pass # If manual parsing fails, fall through to generic fallback

			logger.warning(f'Groq API status error {e.status_code}, falling back to Gemini: {e.response.text}')
			return await self._fallback_to_gemini(messages, output_format, **kwargs)

		except APIError as e:
			logger.warning(f'Groq API error, falling back to Gemini: {e}')
			return await self._fallback_to_gemini(messages, output_format, **kwargs)
		except Exception as e:
			logger.error(f'Unexpected error in Groq ainvoke ({type(e).__name__}): {e}')
			return await self._fallback_to_gemini(messages, output_format, **kwargs)

	async def _fallback_to_gemini(
		self, messages: list[BaseMessage], output_format: type[T] | None = None, **kwargs: Any
	) -> ChatInvokeCompletion[T] | ChatInvokeCompletion[str]:
		"""Fallback to Gemini model if Groq fails."""
		gemini_api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
		if not gemini_api_key:
			logger.error('GEMINI_API_KEY/GOOGLE_API_KEY not found for fallback')
			# If no fallback key, re-raise the original error or a generic one
			raise ModelProviderError(message='Groq failed and no Gemini API key for fallback', model=self.name)

		logger.info('🔄 Falling back to gemini-2.0-flash')
		fallback_model = ChatGoogle(model='gemini-2.0-flash', api_key=gemini_api_key)
		return await fallback_model.ainvoke(messages, output_format, **kwargs)

	async def _invoke_regular_completion(self, groq_messages) -> ChatInvokeCompletion[str]:
		"""Handle regular completion without structured output."""
		chat_completion = await self.get_client().chat.completions.create(
			messages=groq_messages,
			model=self.model,
			service_tier=self.service_tier,
			temperature=self.temperature,
			top_p=self.top_p,
			seed=self.seed,
		)
		usage = self._get_usage(chat_completion)
		return ChatInvokeCompletion(
			completion=chat_completion.choices[0].message.content or '',
			usage=usage,
		)

	async def _invoke_structured_output(self, groq_messages, output_format: type[T]) -> ChatInvokeCompletion[T]:
		"""Handle structured output using either tool calling or JSON schema."""
		schema = SchemaOptimizer.create_optimized_json_schema(output_format)

		if self.model in ToolCallingModels:
			response = await self._invoke_with_tool_calling(groq_messages, output_format, schema)
		else:
			response = await self._invoke_with_json_schema(groq_messages, output_format, schema)

		if not response.choices[0].message.content:
			raise ModelProviderError(
				message='No content in response',
				status_code=500,
				model=self.name,
			)

		parsed_response = output_format.model_validate_json(response.choices[0].message.content)
		usage = self._get_usage(response)

		return ChatInvokeCompletion(
			completion=parsed_response,
			usage=usage,
		)

	async def _invoke_with_tool_calling(self, groq_messages, output_format: type[T], schema) -> ChatCompletion:
		"""Handle structured output using tool calling."""
		tool = ChatCompletionToolParam(
			function={
				'name': output_format.__name__,
				'description': f'Extract information in the format of {output_format.__name__}',
				'parameters': schema,
			},
			type='function',
		)
		tool_choice: ChatCompletionToolChoiceOptionParam = 'required'

		return await self.get_client().chat.completions.create(
			model=self.model,
			messages=groq_messages,
			temperature=self.temperature,
			top_p=self.top_p,
			seed=self.seed,
			tools=[tool],
			tool_choice=tool_choice,
			service_tier=self.service_tier,
		)

	async def _invoke_with_json_schema(self, groq_messages, output_format: type[T], schema) -> ChatCompletion:
		"""Handle structured output using JSON schema."""
		return await self.get_client().chat.completions.create(
			model=self.model,
			messages=groq_messages,
			temperature=self.temperature,
			top_p=self.top_p,
			seed=self.seed,
			response_format=ResponseFormatResponseFormatJsonSchema(
				json_schema=ResponseFormatResponseFormatJsonSchemaJsonSchema(
					name=output_format.__name__,
					description='Model output schema',
					schema=schema,
				),
				type='json_schema',
			),
			service_tier=self.service_tier,
		)
