from __future__ import annotations

import ast
import asyncio
import json
import operator
import os
import time
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import httpx
import requests
from logic.admin_settings import (
    get_active_ai_config,
    get_provider_headers,
    normalize_provider,
)

_free_models_cache: List[str] = []
_free_models_fetched_at: float = 0.0
_FREE_MODELS_TTL = 600


class AIService:
    def __init__(self) -> None:
        self.provider = normalize_provider(os.getenv("DEFAULT_AI_PROVIDER", "omniroute"))
        self.omniroute_url = os.getenv(
            "OMNIROUTE_URL", "http://127.0.0.1:20128/v1/chat/completions"
        )
        self.omniroute_api_key = os.getenv("OMNIROUTE_API_KEY", "")
        self.omniroute_model = os.getenv("OMNIROUTE_MODEL", "auto")
        self.duckai_url = os.getenv(
            "DUCKAI_URL", "http://localhost:3000/v1/chat/completions"
        )
        self.duckai_api_key = os.getenv("DUCKAI_API_KEY", "")
        self.openrouter_url = os.getenv(
            "OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions"
        )
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.alibaba_url = os.getenv(
            "ALIBABA_AI_URL",
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
        )
        self.alibaba_api_key = os.getenv(
            "ALIBABA_AI_KEY", os.getenv("ALIBABA_API_KEY", "")
        )
        self.mock_mode = os.getenv("NEXUS_MOCK_AI", "false").lower() in {
            "1", "true", "yes"
        }
        self._default_free_models = [
            "google/gemma-4-31b-it:free",
            "google/gemma-4-26b-a4b-it:free",
            "qwen/qwen3-next-80b-a3b-instruct:free",
            "qwen/qwen3-coder:free",
            "meta-llama/llama-3.1-8b-instruct:free",
            "liquid/lfm-2.5-1.2b-instruct:free",
            "minimax/minimax-m2.5:free",
            "z-ai/glm-4.5-air:free",
            "openrouter/auto-free",
        ]

    def _load_runtime_config(self) -> Dict[str, object]:
        try:
            config = get_active_ai_config()
            if config:
                return config
        except Exception as exc:
            print(f"[AI-CONFIG] Falling back to environment config: {exc}")

        if self.provider == "omniroute":
            base_url = self.omniroute_url
            api_key = self.omniroute_api_key
            model = self.omniroute_model
        elif self.provider == "alibaba":
            base_url = self.alibaba_url
            api_key = self.alibaba_api_key
            model = os.getenv("ALIBABA_AI_MODEL", "qwen-plus")
        elif self.provider == "duckai":
            base_url = self.duckai_url
            api_key = self.duckai_api_key
            model = os.getenv("DUCKAI_MODEL", "gpt-4o-mini")
        elif self.provider == "openrouter":
            base_url = self.openrouter_url
            api_key = self.openrouter_api_key
            model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
        else:
            base_url = os.getenv(
                "OPENAI_COMPATIBLE_URL", self.omniroute_url
            )
            api_key = os.getenv(
                "OPENAI_COMPATIBLE_API_KEY", self.omniroute_api_key
            )
            model = os.getenv("OPENAI_COMPATIBLE_MODEL", "auto")

        return {
            "provider": self.provider,
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
            "fallback_models": [],
            "referer": os.getenv("OPENROUTER_REFERER", "http://localhost:5008"),
            "title": os.getenv("OPENROUTER_TITLE", "Nexus AI"),
            "extra_headers": {},
            "source": "environment",
        }

    def _get_config(
        self, runtime_config: Optional[Dict[str, object]] = None
    ) -> Tuple[str, str, str, Dict[str, str]]:
        config = runtime_config or self._load_runtime_config()
        provider = normalize_provider(str(config.get("provider") or self.provider))
        if provider == "omniroute":
            default_url, default_key = self.omniroute_url, self.omniroute_api_key
        elif provider == "openrouter":
            default_url, default_key = self.openrouter_url, self.openrouter_api_key
        elif provider == "alibaba":
            default_url, default_key = self.alibaba_url, self.alibaba_api_key
        elif provider == "duckai":
            default_url, default_key = self.duckai_url, self.duckai_api_key
        else:
            default_url = os.getenv("OPENAI_COMPATIBLE_URL", self.omniroute_url)
            default_key = os.getenv("OPENAI_COMPATIBLE_API_KEY", self.omniroute_api_key)

        url = str(config.get("base_url") or default_url)
        api_key = str(config.get("api_key") or default_key)
        headers = dict(get_provider_headers(config))
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        else:
            headers.pop("Authorization", None)
        return url, api_key, provider, headers

    def resolve_model(
        self,
        requested_model: Optional[str] = None,
        runtime_config: Optional[Dict[str, object]] = None,
    ) -> str:
        """Resolve request/routing model names against the active gateway."""
        config = runtime_config or self._load_runtime_config()
        provider = normalize_provider(str(config.get("provider") or self.provider))
        configured = str(config.get("model") or "").strip()
        requested = str(requested_model or "").strip()
        if provider == "omniroute":
            configured = configured or self.omniroute_model or "auto"
            # Cognitive routing historically emits OpenRouter free-model IDs.
            # OmniRoute owns model selection, so those legacy IDs map to its
            # configured model (normally auto or auto/fast).
            if (
                not requested
                or requested in {"auto", "openrouter/free"}
                or requested.startswith("openrouter/")
                or requested.endswith(":free")
            ):
                return configured
            return requested
        if requested and requested not in {"", "auto", "openrouter/free"}:
            return requested
        if configured:
            return configured
        return requested or "openrouter/free"

    def fetch_free_models(self) -> List[str]:
        """Fetch and cache OpenRouter models with zero prompt/completion cost."""
        global _free_models_cache, _free_models_fetched_at
        runtime_config = self._load_runtime_config()
        provider = normalize_provider(str(runtime_config.get("provider") or self.provider))
        api_key = str(runtime_config.get("api_key") or self.openrouter_api_key)
        now = time.time()
        if _free_models_cache and now - _free_models_fetched_at < _FREE_MODELS_TTL:
            return list(_free_models_cache)
        if provider != "openrouter":
            return list(self._default_free_models)

        try:
            response = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
                timeout=10,
            )
            response.raise_for_status()
            free: List[str] = []
            for model in response.json().get("data", []):
                model_id = str(model.get("id") or "")
                pricing = model.get("pricing") or {}
                prompt_price = str(pricing.get("prompt", "1"))
                completion_price = str(pricing.get("completion", "1"))
                context_length = int(model.get("context_length") or 0)
                is_free = model_id.endswith(":free") or (
                    prompt_price == "0" and completion_price == "0"
                )
                is_usable = context_length >= 8192 and "ocr" not in model_id
                if model_id and is_free and is_usable:
                    free.append(model_id)
            if free:
                _free_models_cache = list(dict.fromkeys(free))
                _free_models_fetched_at = now
                return list(_free_models_cache)
        except Exception as exc:
            print(f"[FREE-ROUTER] Failed to fetch free models: {exc}")
        return list(self._default_free_models)

    async def fetch_free_models_async(self) -> List[str]:
        return await asyncio.to_thread(self.fetch_free_models)

    def get_fallback_chain(self, primary_model: str) -> List[str]:
        config = self._load_runtime_config()
        provider = normalize_provider(str(config.get("provider") or self.provider))
        primary = self.resolve_model(primary_model, config)
        if self.mock_mode:
            return [primary]
        configured = config.get("fallback_models") or []
        if isinstance(configured, list) and configured:
            configured_models = [
                self.resolve_model(str(item), config) for item in configured
            ]
            allow_paid = os.getenv("ALLOW_PAID_MODELS", "false").lower() in {
                "1", "true", "yes"
            }
            if provider == "openrouter" and not allow_paid:
                configured_models = [
                    model
                    for model in configured_models
                    if model.endswith(":free") or model.startswith("openrouter/")
                ]
            candidates = [primary] + configured_models
        elif provider == "openrouter":
            candidates = [primary] + self.fetch_free_models()
        else:
            candidates = [primary]
        return list(dict.fromkeys(model for model in candidates if model))

    @staticmethod
    def _message_value(message: Any, key: str, default: Any = None) -> Any:
        if hasattr(message, key):
            return getattr(message, key)
        if isinstance(message, dict):
            return message.get(key, default)
        return default

    def _build_messages(
        self,
        prompt: str,
        history: Optional[List[Any]],
        system_prompt: str,
        provider: str,
        images: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        history = history or []
        messages: List[Dict[str, Any]] = []

        if provider == "duckai":
            if history:
                system_merged = False
                for message in history:
                    role = self._message_value(message, "role", "user")
                    content = self._message_value(message, "content", "")
                    item = {"role": role, "content": content}
                    if role == "user" and not system_merged:
                        item["content"] = f"{system_prompt}\n\n{content}"
                        system_merged = True
                    self._copy_tool_fields(message, item)
                    messages.append(item)
                if prompt:
                    messages.append({"role": "user", "content": prompt})
            elif prompt:
                messages.append(
                    {"role": "user", "content": f"{system_prompt}\n\nUSER MESSAGE: {prompt}"}
                )
            return messages

        messages.append({"role": "system", "content": system_prompt})
        for message in history:
            role = self._message_value(message, "role", "user")
            content = self._message_value(message, "content", "")
            item: Dict[str, Any] = {"role": role, "content": content}
            self._copy_tool_fields(message, item)
            messages.append(item)

        if prompt:
            if images:
                content_parts: List[Dict[str, Any]] = [
                    {"type": "text", "text": prompt}
                ]
                for image_url in images[:4]:
                    content_parts.append(
                        {"type": "image_url", "image_url": {"url": image_url}}
                    )
                messages.append({"role": "user", "content": content_parts})
            else:
                messages.append({"role": "user", "content": prompt})
        return messages

    def _copy_tool_fields(self, message: Any, item: Dict[str, Any]) -> None:
        tool_calls = self._message_value(message, "tool_calls")
        tool_call_id = self._message_value(message, "tool_call_id")
        reasoning_details = self._message_value(message, "reasoning_details")
        if tool_calls:
            item["tool_calls"] = tool_calls
        if item.get("role") == "tool" and tool_call_id:
            item["tool_call_id"] = tool_call_id
        if reasoning_details:
            item["reasoning_details"] = reasoning_details

    async def _consume_sse(
        self, response: httpx.Response
    ) -> AsyncGenerator[Tuple[str, Any], None]:
        """Consume provider SSE and aggregate fragmented tool calls."""
        tool_buffers: Dict[str, Dict[str, Any]] = {}
        async for line in response.aiter_lines():
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if data_str == "[DONE]":
                break
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue
            choices = data.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            deltas = delta.get("tool_calls") or []
            for fallback_index, call_delta in enumerate(deltas):
                index = str(call_delta.get("index", fallback_index))
                current = tool_buffers.setdefault(
                    index,
                    {
                        "id": "",
                        "type": "function",
                        "function": {"name": "", "arguments": ""},
                    },
                )
                if call_delta.get("id"):
                    current["id"] = call_delta["id"]
                if call_delta.get("type"):
                    current["type"] = call_delta["type"]
                function_delta = call_delta.get("function") or {}
                current["function"]["name"] += str(function_delta.get("name") or "")
                current["function"]["arguments"] += str(
                    function_delta.get("arguments") or ""
                )
            content = delta.get("content")
            if content:
                yield "text", content

        if tool_buffers:
            calls = [tool_buffers[key] for key in sorted(tool_buffers)]
            for index, call in enumerate(calls):
                if not call.get("id"):
                    call["id"] = f"tool_call_{index}"
            yield "tool_calls", calls

    def _mock_response(self, prompt: str, system_prompt: str) -> str:
        if "Nexus Cognitive Intent Analyzer" in system_prompt:
            text = prompt.lower()
            if any(term in text for term in ["microservice", "kubernetes", "observability dashboard"]):
                domain, complexity, mode, model = (
                    "architecture", 0.8, "systems_mode", "qwen/qwen3-coder:free"
                )
            elif any(term in text for term in ["lead", "closing", "funnel", "operasi"]):
                domain, complexity, mode, model = (
                    "operations", 0.65, "diagnosis_mode", "google/gemma-4-31b-it:free"
                )
            elif any(term in text for term in ["tacit knowledge", "governance", "ownership"]):
                domain, complexity, mode, model = (
                    "governance", 0.75, "strategic_mode", "google/gemma-4-31b-it:free"
                )
            elif any(term in text for term in ["seperti umur 5", "belajar", "jelaskan"]):
                domain, complexity, mode, model = (
                    "educational", 0.35, "educational_mode", "liquid/lfm-2.5-1.2b-instruct:free"
                )
            else:
                domain, complexity, mode, model = (
                    "factual", 0.3, "factual_mode", "liquid/lfm-2.5-1.2b-instruct:free"
                )
            return json.dumps(
                {
                    "domain": domain,
                    "abstraction_level": 0.6 if domain in {"governance", "architecture"} else 0.3,
                    "reasoning_complexity": complexity,
                    "ambiguity_score": 0.15,
                    "strategic_impact": 0.65 if domain in {"governance", "operations"} else 0.2,
                    "operational_impact": 0.7 if domain in {"operations", "architecture"} else 0.2,
                    "governance_relevance": 0.8 if domain == "governance" else 0.1,
                    "suggested_mode": mode,
                    "suggested_model": model,
                    "requires_grill_me": False,
                    "confidence": 0.95,
                    "reasoning_rationale": "Deterministic development response.",
                }
            )
        return f"[Mock Rohadi] Saya menerima pesan Anda: {prompt[:500]}"

    async def call_ai_stream(
        self,
        prompt: str,
        history: Optional[List[Any]] = None,
        system_prompt: str = "You are Nexus AI, a helpful personal assistant.",
        model: str = "auto",
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Any = "auto",
        images: Optional[List[str]] = None,
    ) -> AsyncGenerator[str, None]:
        if self.mock_mode:
            yield self._mock_response(prompt, system_prompt)
            return

        runtime_config = self._load_runtime_config()
        url, _, provider, headers = self._get_config(runtime_config)
        model = self.resolve_model(model, runtime_config)
        messages = self._build_messages(
            prompt, history, system_prompt, provider, images
        )
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        max_retries = 2
        last_error = ""
        for attempt in range(max_retries):
            try:
                print(
                    f"[STREAM] {provider.upper()} attempt {attempt + 1}/{max_retries} model={model}"
                )
                timeout = httpx.Timeout(180.0, connect=15.0)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream(
                        "POST", url, json=payload, headers=headers
                    ) as response:
                        response_to_consume = response
                        status = response.status_code
                        body = ""
                        if status == 400 and tools:
                            # Some free models reject function calling. Retry the
                            # same request once without tools, but never expose a
                            # half-formed tool call to the caller.
                            fallback_payload = dict(payload)
                            fallback_payload.pop("tools", None)
                            fallback_payload.pop("tool_choice", None)
                            async with client.stream(
                                "POST", url, json=fallback_payload, headers=headers
                            ) as fallback_response:
                                if fallback_response.status_code == 200:
                                    async for kind, value in self._consume_sse(
                                        fallback_response
                                    ):
                                        if kind == "text":
                                            yield value
                                    return
                                status = fallback_response.status_code
                                body = (await fallback_response.aread())[:1_000].decode(
                                    "utf-8", errors="replace"
                                )

                        if status != 200:
                            if not body:
                                body = (await response.aread())[:1_000].decode(
                                    "utf-8", errors="replace"
                                )
                            last_error = f"AI provider returned {status}: {body}"
                            if status in {408, 409, 425, 429, 500, 502, 503, 504}:
                                raise RuntimeError(last_error)
                            yield (
                                "data: "
                                + json.dumps(
                                    {
                                        "type": "error",
                                        "message": f"AI provider returned HTTP {status}",
                                        "retryable": False,
                                    }
                                )
                                + "\n\n"
                            )
                            return

                        async for kind, value in self._consume_sse(response_to_consume):
                            if kind == "text":
                                yield value
                            else:
                                yield (
                                    "data: "
                                    + json.dumps(
                                        {
                                            "type": "tool_calls",
                                            "tool_calls": value,
                                        },
                                        ensure_ascii=False,
                                    )
                                    + "\n\n"
                                )
                        return
            except Exception as exc:
                last_error = str(exc)
                print(f"[STREAM ERROR] {last_error}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue

        yield f"data: {json.dumps({'type': 'error', 'message': f'Connection error: {last_error}', 'retryable': True})}\n\n"

    def call_ai(
        self,
        prompt: str,
        history: Optional[List[Any]] = None,
        system_prompt: str = "You are Nexus AI, a helpful personal assistant.",
        model: str = "auto",
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Any = "auto",
        images: Optional[List[str]] = None,
    ) -> Optional[str]:
        if self.mock_mode:
            return self._mock_response(prompt, system_prompt)

        runtime_config = self._load_runtime_config()
        url, _, provider, headers = self._get_config(runtime_config)
        model = self.resolve_model(model, runtime_config)
        payload: Dict[str, Any] = {
            "model": model,
            "messages": self._build_messages(
                prompt, history, system_prompt, provider, images
            ),
            "temperature": 0.7,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            message = (response.json().get("choices") or [{}])[0].get("message") or {}
            if message.get("tool_calls"):
                return json.dumps({"tool_calls": message["tool_calls"]})
            content = message.get("content")
            return str(content).strip() if content is not None else ""
        except Exception as exc:
            print(f"[{provider}] call failed: {exc}")
            return None

    call_duckai = call_ai
    call_duckai_stream = call_ai_stream

    @staticmethod
    def _safe_calculate(expression: str) -> float | int:
        operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.Mod: operator.mod,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }

        def evaluate(node: ast.AST) -> float | int:
            if isinstance(node, ast.Expression):
                return evaluate(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            if isinstance(node, ast.UnaryOp) and type(node.op) in operators:
                return operators[type(node.op)](evaluate(node.operand))
            if isinstance(node, ast.BinOp) and type(node.op) in operators:
                left, right = evaluate(node.left), evaluate(node.right)
                if isinstance(node.op, ast.Pow) and abs(right) > 20:
                    raise ValueError("Exponent is too large")
                return operators[type(node.op)](left, right)
            raise ValueError("Only basic arithmetic is allowed")

        tree = ast.parse((expression or "")[:200], mode="eval")
        result = evaluate(tree)
        if abs(float(result)) > 1e100:
            raise ValueError("Result is too large")
        return result

    async def execute_tool_call(self, tool_call: Dict[str, Any]) -> str:
        from tools.web_search_tool import web_search_tool

        function = tool_call.get("function") or {}
        tool_name = str(function.get("name") or "")
        arguments = function.get("arguments") or {}
        try:
            args = json.loads(arguments) if isinstance(arguments, str) else arguments
            if not isinstance(args, dict):
                raise ValueError("Tool arguments must be an object")

            if tool_name == "web_search":
                result = await web_search_tool.search(
                    str(args.get("query") or ""),
                    max(1, min(int(args.get("num_results", 5)), 10)),
                )
                return json.dumps(result, ensure_ascii=False)

            if tool_name == "research_topic":
                topic = str(args.get("topic") or "")[:500]
                depth = str(args.get("depth") or "shallow")
                search_result = await web_search_tool.search(
                    topic, num_results=10 if depth == "deep" else 5
                )
                if "error" in search_result:
                    return json.dumps(search_result)
                detailed_content = []
                for url_data in search_result.get("results", [])[:3]:
                    url = url_data.get("url", "")
                    if not url:
                        continue
                    content = await web_search_tool.fetch_url_content(url)
                    if "error" not in content:
                        detailed_content.append(
                            {
                                "url": url,
                                "title": content.get("title", ""),
                                "content": content.get("content", "")[:500],
                            }
                        )
                paa = await web_search_tool.get_people_also_ask(topic)
                related = await web_search_tool.get_related_searches(topic)
                return json.dumps(
                    {
                        "topic": topic,
                        "search_results": search_result.get("results", [])[:5],
                        "detailed_content": detailed_content,
                        "people_also_ask": paa.get("questions", []),
                        "related_searches": related.get("related_searches", []),
                        "depth": depth,
                    },
                    ensure_ascii=False,
                )

            if tool_name == "fetch_url":
                return json.dumps(
                    await web_search_tool.fetch_url_content(str(args.get("url") or "")),
                    ensure_ascii=False,
                )

            if tool_name == "get_people_also_ask":
                return json.dumps(
                    await web_search_tool.get_people_also_ask(
                        str(args.get("query") or "")
                    ),
                    ensure_ascii=False,
                )

            if tool_name == "get_related_searches":
                return json.dumps(
                    await web_search_tool.get_related_searches(
                        str(args.get("query") or "")
                    ),
                    ensure_ascii=False,
                )

            if tool_name == "get_current_time":
                timezone_name = str(args.get("timezone") or "UTC")
                try:
                    current = datetime.now(ZoneInfo(timezone_name))
                except Exception:
                    current = datetime.now(timezone.utc)
                return json.dumps(
                    {"current_time": current.isoformat(), "timezone": timezone_name}
                )

            if tool_name == "calculate":
                return json.dumps(
                    {"result": self._safe_calculate(str(args.get("expression") or ""))}
                )

            if tool_name == "grill_me":
                from tools.grill_me_skill_v2 import grill_me_skill

                question = await asyncio.to_thread(
                    grill_me_skill.generate_grill_question,
                    str(args.get("user_idea") or ""),
                    [],
                    "tool-grill",
                )
                return json.dumps(
                    {"response": grill_me_skill.format_response(question)},
                    ensure_ascii=False,
                )

            return json.dumps({"error": f"Unknown tool: {tool_name}"})
        except Exception as exc:
            return json.dumps({"error": str(exc)})


ai_service = AIService()
