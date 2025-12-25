from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import logging

from openai import OpenAI, AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type
from aiolimiter import AsyncLimiter

from docintel.cache import DiskCache
from docintel.hashing import sha256_json
from docintel.tracing import get_tracer
from docintel.metrics import Usage, TokenEstimator, CostModel

log = logging.getLogger("docintel.llm")
tracer = get_tracer("docintel.llm")

class LLMClient:
    def __init__(self, client: OpenAI, model: str, cache: DiskCache | None, ttl_s: int | None, max_retries: int, timeout_s: float):
        self._client = client
        self._model = model
        self._cache = cache
        self._ttl_s = ttl_s
        self._max_retries = max_retries
        self._timeout_s = timeout_s

    def _retry(self):
        return retry(
            reraise=True,
            stop=stop_after_attempt(self._max_retries if self._max_retries > 0 else 1),
            wait=wait_exponential_jitter(initial=0.8, max=30),
            retry=retry_if_exception_type(Exception),
        )

    def complete(self, messages: List[Dict[str, Any]]) -> str:
        payload = {"model": self._model, "messages": messages}
        key = f"chat:{sha256_json(payload)}"

        def _call():
            return self._complete_uncached(messages)

        if self._cache:
            hit = self._cache.get(key)
            if hit is not None:
                return hit
            val = _call()
            self._cache.set(key, val, ttl_s=self._ttl_s)
            return val
        return _call()

    def _complete_uncached(self, messages: List[Dict[str, Any]]) -> str:
        with tracer.start_as_current_span("chat.completions.create") as span:
            span.set_attribute("model", self._model)

            @self._retry()
            def _do():
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=0.0,
                    timeout=self._timeout_s,
                )
                return resp.choices[0].message.content or ""

            return _do()

class AsyncLLMClient:
    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        cache: DiskCache | None,
        ttl_s: int | None,
        max_retries: int,
        timeout_s: float,
        limiter: Optional[AsyncLimiter] = None,
    ):
        self._client = client
        self._model = model
        self._cache = cache
        self._ttl_s = ttl_s
        self._max_retries = max_retries
        self._timeout_s = timeout_s
        self._limiter = limiter
        self._est = TokenEstimator(model)
        self._cost = CostModel(model)

    def _retry(self):
        return retry(
            reraise=True,
            stop=stop_after_attempt(self._max_retries if self._max_retries > 0 else 1),
            wait=wait_exponential_jitter(initial=0.8, max=30),
            retry=retry_if_exception_type(Exception),
        )

    async def complete(self, messages: List[Dict[str, Any]]) -> Tuple[str, Usage, float]:
        payload = {"model": self._model, "messages": messages}
        key = f"achat:{sha256_json(payload)}"

        if self._cache:
            hit = self._cache.get(key)
            if hit is not None:
                text, usage_dict = hit
                usage = Usage(**usage_dict)
                return text, usage, self._cost.estimate(usage).total_usd

        prompt_text = "\n".join([m.get("content","") for m in messages])
        prompt_tokens = self._est.count(prompt_text)

        async def _call():
            with tracer.start_as_current_span("async.chat.completions.create") as span:
                span.set_attribute("model", self._model)
                if self._limiter:
                    await self._limiter.acquire()

                @self._retry()
                async def _do():
                    resp = await self._client.chat.completions.create(
                        model=self._model,
                        messages=messages,
                        temperature=0.0,
                        timeout=self._timeout_s,
                    )
                    return resp

                resp = await _do()
                text = resp.choices[0].message.content or ""
                completion_tokens = self._est.count(text)
                usage = Usage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
                span.set_attribute("prompt_tokens_est", usage.prompt_tokens)
                span.set_attribute("completion_tokens_est", usage.completion_tokens)
                return text, usage

        text, usage = await _call()
        cost = self._cost.estimate(usage).total_usd
        if self._cache:
            self._cache.set(key, (text, usage.__dict__), ttl_s=self._ttl_s)
        return text, usage, cost
