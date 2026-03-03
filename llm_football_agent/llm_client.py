"""统一 LLM Gateway（Provider Adapter + Retry + Prompt 组装）。

支持：
    - OpenAI-compatible（OpenAI / vLLM / OneAPI / 兼容网关）
    - Gemini native（google-generativeai，可选依赖）
    - Qwen（基于 OpenAI-compatible 的专用适配器）
"""

import re
import time
import importlib
from abc import ABC, abstractmethod

from openai import OpenAI


PROMPT_MODULES = {
    "role": (
        "你是一个专业足球战术 AI。你正在控制进攻方（左队）在 "
        "academy_3_vs_1_with_keeper 场景中尝试进球。"
    ),
    "scenario": (
        "【场景】3 名进攻球员 vs 1 名防守球员 + 1 名门将。你需要通过传球配合突破防守，完成射门得分。"
    ),
    "coordinate": (
        "【坐标系】\n"
        "- 球场: x ∈ [-1, 1], y ∈ [-0.42, 0.42]\n"
        "- 对方球门: x = 1.0, 球门口 y ∈ [-0.044, 0.044]\n"
        "- x 越大 → 越接近对方球门\n"
        "- y 正值 → 球场下方, y 负值 → 球场上方"
    ),
    "principles": (
        "【核心战术原则】\n"
        "1. 当持球者前方有防守者挡住 → 传球(11短传/9长传/10高球)给空位队友\n"
        "2. 接近球门(x > 0.85)且射角合适 → 果断射门(12)\n"
        "3. 传球方向由当前移动方向决定 → 先设方向(1-8)，再执行传球\n"
        "4. 利用3打1的人数优势 → 拉开空间，做三角传球配合\n"
        "5. 不要长时间盘带 → 快速传切更有效"
    ),
    "thinking": (
        "【内部思考步骤（不要输出）】\n"
        "- 先判断球权与防守压迫\n"
        "- 再评估到球门距离与射门角度\n"
        "- 最后只输出一个动作，不要输出多动作序列"
    ),
    "output": (
        "【输出格式】（严格遵守）\n"
        "只输出一个 JSON 对象:\n"
        "{\"action\": <0-18的整数>, \"reason\": \"<20字以内的理由>\"}"
    ),
}

SYSTEM_PROMPT = "\n\n".join(PROMPT_MODULES.values())


class ProviderAdapter(ABC):
    @abstractmethod
    def generate(self, *, model: str, messages: list[dict], temperature: float, max_tokens: int) -> dict:
        """返回统一结构: {raw_response: str, tokens: int}"""


class OpenAICompatibleAdapter(ProviderAdapter):
    def __init__(self, api_key: str, base_url: str | None, timeout: float):
        self.client = OpenAI(
            api_key=api_key,
            base_url=LLMGateway._normalize_base_url(base_url),
            timeout=timeout,
        )

    def generate(self, *, model: str, messages: list[dict], temperature: float, max_tokens: int) -> dict:
        resp = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        raw = (resp.choices[0].message.content or "").strip()
        usage = getattr(resp, "usage", None)
        tokens = int(usage.total_tokens) if usage and usage.total_tokens else 0
        return {"raw_response": raw, "tokens": tokens}


class QwenAdapter(OpenAICompatibleAdapter):
    """Qwen 适配器：默认仍走 OpenAI-compatible 协议。"""


class GeminiNativeAdapter(ProviderAdapter):
    def __init__(self, api_key: str, timeout: float):
        self.timeout = timeout
        try:
            genai = importlib.import_module("google.generativeai")
        except Exception as exc:
            raise ImportError(
                "Gemini native 适配器需要安装 google-generativeai。"
            ) from exc

        genai.configure(api_key=api_key)
        self._genai = genai

    def generate(self, *, model: str, messages: list[dict], temperature: float, max_tokens: int) -> dict:
        prompt = []
        for item in messages:
            role = item.get("role", "user")
            if role == "assistant":
                prompt.append(f"[assistant]\n{item.get('content', '')}")
            elif role == "system":
                prompt.append(f"[system]\n{item.get('content', '')}")
            else:
                prompt.append(f"[user]\n{item.get('content', '')}")

        text_prompt = "\n\n".join(prompt)
        model_obj = self._genai.GenerativeModel(model_name=model)
        resp = model_obj.generate_content(
            text_prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
            request_options={"timeout": self.timeout},
        )
        raw = (getattr(resp, "text", None) or "").strip()
        usage_meta = getattr(resp, "usage_metadata", None)
        tokens = 0
        if usage_meta and hasattr(usage_meta, "total_token_count"):
            tokens = int(getattr(usage_meta, "total_token_count") or 0)
        return {"raw_response": raw, "tokens": tokens}


class LLMGateway:
    """线程不安全，每个 worker 应持有独立实例。"""

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str | None = None,
        provider: str = "openai_compatible",
        temperature: float = 0.3,
        max_tokens: int = 256,
        timeout: float = 10.0,
        max_retries: int = 5,
        retry_backoff_base: float = 0.8,
    ):
        self.model = model
        self.provider = provider
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max(0, int(max_retries))
        self.retry_backoff_base = max(0.1, float(retry_backoff_base))
        self.timeout = timeout
        self.adapter = self._create_adapter(
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

        self.total_tokens = 0
        self.call_count = 0
        self.latencies: list[float] = []
        self.retry_hist: list[int] = []

    def _create_adapter(self, *, provider: str, api_key: str, base_url: str | None, timeout: float) -> ProviderAdapter:
        p = (provider or "openai_compatible").strip().lower()

        if p in {"openai", "openai_compatible", "compat", "compatible"}:
            return OpenAICompatibleAdapter(api_key=api_key, base_url=base_url, timeout=timeout)
        if p in {"qwen", "qwen_compatible"}:
            return QwenAdapter(api_key=api_key, base_url=base_url, timeout=timeout)
        if p in {"gemini", "gemini_native", "google"}:
            return GeminiNativeAdapter(api_key=api_key, timeout=timeout)

        raise ValueError(f"不支持的 provider: {provider}")

    # ─────────────────────────────────────────────────────

    def decide(self, obs_text: str, history: list | None = None, memory_context: str | None = None) -> dict:
        """
        向 LLM 发送观测文本，获取原始响应。

        Args:
            obs_text: 观测的文本描述
            history:  最近几步 [{"step":, "action":, "reason":}, ...]

        Returns:
            dict with keys:
                raw_response, elapsed, tokens, raw_prompt,
                retry_count, error_type[, error]
        """
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if memory_context:
            messages.append({"role": "user", "content": f"【记忆检索】\n{memory_context}"})

        if history:
            recent = history[-3:]
            hist_lines = "\n".join(
                f"第{h['step']}步: 动作={h['action']}({h.get('reason','')})"
                for h in recent
            )
            messages.append({"role": "user", "content": f"【近期决策历史】\n{hist_lines}"})
            messages.append(
                {"role": "assistant", "content": "好的，我会参考历史做出更好的决策。"}
            )

        messages.append({"role": "user", "content": obs_text})

        raw_prompt = self._messages_to_prompt_text(messages)
        t0 = time.time()

        last_error = None
        last_error_type = "unknown"
        attempts_used = 0
        for attempt in range(self.max_retries + 1):
            attempts_used = attempt
            try:
                out = self.adapter.generate(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                elapsed = time.time() - t0
                tokens = int(out.get("tokens", 0))
                retry_count = attempt

                self.total_tokens += tokens
                self.call_count += 1
                self.latencies.append(elapsed)
                self.retry_hist.append(retry_count)

                return {
                    "raw_response": out.get("raw_response", ""),
                    "elapsed": elapsed,
                    "tokens": tokens,
                    "raw_prompt": raw_prompt,
                    "retry_count": retry_count,
                    "error_type": "none",
                    "provider": self.provider,
                }
            except Exception as exc:
                last_error = exc
                last_error_type = self._classify_error(exc)
                should_retry = self._should_retry(exc, last_error_type)
                if (not should_retry) or attempt >= self.max_retries:
                    break
                backoff = self.retry_backoff_base * (2 ** attempt)
                time.sleep(backoff)

        elapsed = time.time() - t0
        retry_count = max(0, attempts_used)
        self.call_count += 1
        self.latencies.append(elapsed)
        self.retry_hist.append(retry_count)
        return {
            "raw_response": "",
            "elapsed": elapsed,
            "tokens": 0,
            "raw_prompt": raw_prompt,
            "retry_count": retry_count,
            "error_type": last_error_type,
            "provider": self.provider,
            "error": str(last_error) if last_error else "unknown error",
        }

    # ─────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        p95_ms = self._percentile(self.latencies, 95) * 1000
        return {
            "total_calls": self.call_count,
            "total_tokens": self.total_tokens,
            "avg_tokens_per_call": (
                self.total_tokens / self.call_count if self.call_count else 0
            ),
            "avg_retry_count": (
                sum(self.retry_hist) / len(self.retry_hist) if self.retry_hist else 0.0
            ),
            "latency_p95_ms": round(p95_ms, 2),
        }

    @staticmethod
    def _messages_to_prompt_text(messages: list[dict]) -> str:
        chunks = []
        for item in messages:
            chunks.append(f"[{item.get('role', 'user')}]\n{item.get('content', '')}")
        return "\n\n".join(chunks)

    @staticmethod
    def _extract_status_code(exc: Exception) -> int | None:
        code = getattr(exc, "status_code", None)
        if isinstance(code, int):
            return code
        msg = str(exc)
        m = re.search(r"\b(4\d\d|5\d\d)\b", msg)
        if m:
            return int(m.group(1))
        return None

    @classmethod
    def _classify_error(cls, exc: Exception) -> str:
        msg = str(exc).lower()
        status = cls._extract_status_code(exc)

        if "timed out" in msg or "timeout" in msg:
            return "timeout"
        if status == 429:
            return "rate_limit"
        if status is not None and 500 <= status <= 599:
            return "server_5xx"
        if status is not None and 400 <= status <= 499:
            return "client_4xx"
        return "unknown"

    @classmethod
    def _should_retry(cls, exc: Exception, error_type: str) -> bool:
        if error_type in {"timeout", "rate_limit", "server_5xx"}:
            return True
        if error_type == "client_4xx":
            return False
        msg = str(exc).lower()
        return any(x in msg for x in ["timed out", "timeout", "temporarily", "connection reset"])

    @staticmethod
    def _percentile(values: list[float], p: int) -> float:
        if not values:
            return 0.0
        arr = sorted(values)
        idx = min(len(arr) - 1, max(0, int(round((p / 100) * (len(arr) - 1)))))
        return float(arr[idx])

    @staticmethod
    def _normalize_base_url(base_url: str | None) -> str | None:
        if not base_url:
            return base_url

        normalized = base_url.strip().rstrip("/")
        for suffix in ("/chat/completions", "/completions"):
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)]
                break
        return normalized


# 向后兼容旧命名
LLMClient = LLMGateway
