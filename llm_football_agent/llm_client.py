"""
LLM Client — 封装 OpenAI-compatible API 调用。

支持 OpenAI / Azure / 本地部署（vLLM / Ollama 等）任何兼容接口。
"""

import time
from openai import OpenAI


SYSTEM_PROMPT = """\
你是一个专业足球战术 AI。你正在控制进攻方（左队）在 academy_3_vs_1_with_keeper 场景中尝试进球。

【场景】3 名进攻球员 vs 1 名防守球员 + 1 名门将。你需要通过传球配合突破防守，完成射门得分。

【坐标系】
- 球场: x ∈ [-1, 1], y ∈ [-0.42, 0.42]
- 对方球门: x = 1.0, 球门口 y ∈ [-0.044, 0.044]
- x 越大 → 越接近对方球门
- y 正值 → 球场下方, y 负值 → 球场上方

【核心战术原则】
1. 当持球者前方有防守者挡住 → 传球(11短传/9长传/10高球)给空位队友
2. 接近球门(x > 0.85)且射角合适 → 果断射门(12)
3. 传球方向由当前移动方向决定 → 先设方向(1-8)，再执行传球
4. 利用3打1的人数优势 → 拉开空间，做三角传球配合
5. 不要长时间盘带 → 快速传切更有效

【输出格式】（严格遵守）
只输出一个 JSON 对象:
{"action": <0-18的整数>, "reason": "<20字以内的理由>"}
"""


class LLMClient:
    """线程不安全，每个 worker 应持有独立实例。"""

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 256,
        timeout: float = 10.0,
    ):
        normalized_base_url = self._normalize_base_url(base_url)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = OpenAI(
            api_key=api_key,
            base_url=normalized_base_url,
            timeout=timeout,
        )
        self.total_tokens = 0
        self.call_count = 0

    # ─────────────────────────────────────────────────────

    def decide(self, obs_text: str, history: list | None = None) -> dict:
        """
        向 LLM 发送观测文本，获取原始响应。

        Args:
            obs_text: 观测的文本描述
            history:  最近几步 [{"step":, "action":, "reason":}, ...]

        Returns:
            dict with keys: raw_response, elapsed, tokens[, error]
        """
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

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

        t0 = time.time()
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            raw = resp.choices[0].message.content.strip()
            usage = resp.usage
            if usage:
                self.total_tokens += usage.total_tokens
            self.call_count += 1
            return {
                "raw_response": raw,
                "elapsed": time.time() - t0,
                "tokens": usage.total_tokens if usage else 0,
            }
        except Exception as exc:
            return {
                "raw_response": "",
                "elapsed": time.time() - t0,
                "tokens": 0,
                "error": str(exc),
            }

    # ─────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        return {
            "total_calls": self.call_count,
            "total_tokens": self.total_tokens,
            "avg_tokens_per_call": (
                self.total_tokens / self.call_count if self.call_count else 0
            ),
        }

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
