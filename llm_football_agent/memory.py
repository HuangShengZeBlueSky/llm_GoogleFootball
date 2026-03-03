"""轻量记忆模块：Working + Episodic。"""

from __future__ import annotations

import re
from collections import deque


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


def _tokenize(text: str) -> set[str]:
    if not text:
        return set()
    return set(_TOKEN_RE.findall(text.lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    u = a | b
    if not u:
        return 0.0
    return len(a & b) / len(u)


class WorkingMemory:
    def __init__(self, max_steps: int = 8):
        self.max_steps = max(1, int(max_steps))
        self.buffer = deque(maxlen=self.max_steps)

    def add(self, *, step: int, action: int, reason: str, reward: float, obs_text: str = ""):
        self.buffer.append(
            {
                "step": int(step),
                "action": int(action),
                "reason": str(reason),
                "reward": float(reward),
                "obs_text": obs_text,
            }
        )

    def recent(self, n: int = 5) -> list[dict]:
        n = max(1, int(n))
        return list(self.buffer)[-n:]

    def clear(self):
        self.buffer.clear()


class EpisodicMemory:
    def __init__(self, max_items: int = 200):
        self.max_items = max(1, int(max_items))
        self.items: list[dict] = []

    def add(self, *, episode: int, summary: str, tags: str, priority: float):
        record = {
            "episode": int(episode),
            "summary": summary,
            "tags": tags,
            "priority": float(priority),
            "tokens": _tokenize(summary + " " + tags),
        }
        self.items.append(record)
        if len(self.items) > self.max_items:
            self.items = self.items[-self.max_items :]

    def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        q = _tokenize(query)
        scored = []
        for item in self.items:
            sim = _jaccard(q, item["tokens"])
            score = sim * 0.7 + min(1.0, item["priority"]) * 0.3
            scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [it for s, it in scored[: max(0, int(top_k))] if s > 0]


class MemoryManager:
    def __init__(
        self,
        working_size: int = 8,
        episodic_size: int = 200,
        retrieval_top_k: int = 3,
    ):
        self.working = WorkingMemory(max_steps=working_size)
        self.episodic = EpisodicMemory(max_items=episodic_size)
        self.retrieval_top_k = max(1, int(retrieval_top_k))
        self._episode_events: list[dict] = []

    def on_step(
        self,
        *,
        step: int,
        action: int,
        reason: str,
        reward: float,
        obs_text: str = "",
        parse_success: bool = True,
    ):
        self.working.add(step=step, action=action, reason=reason, reward=reward, obs_text=obs_text)
        self._episode_events.append(
            {
                "step": int(step),
                "action": int(action),
                "reason": str(reason),
                "reward": float(reward),
                "obs_text": obs_text,
                "parse_success": bool(parse_success),
            }
        )

    def build_context(self, obs_text: str) -> str:
        lines = []

        recent = self.working.recent(5)
        if recent:
            lines.append("[Working Memory | 最近决策]")
            for item in recent:
                lines.append(
                    f"- step={item['step']} action={item['action']} reward={item['reward']:.3f} reason={item['reason'][:30]}"
                )

        recalls = self.episodic.retrieve(obs_text, top_k=self.retrieval_top_k)
        if recalls:
            lines.append("\n[Episodic Memory | 历史经验]")
            for mem in recalls:
                lines.append(
                    f"- ep={mem['episode']} tags={mem['tags']} summary={mem['summary'][:80]}"
                )

        return "\n".join(lines).strip()

    def end_episode(self, *, episode: int, scored: bool, total_reward: float):
        if not self._episode_events:
            self.working.clear()
            return

        key_events = sorted(
            self._episode_events,
            key=lambda x: abs(float(x["reward"])),
            reverse=True,
        )[:3]
        action_set = sorted({e["action"] for e in self._episode_events})
        parse_fail_count = sum(1 for e in self._episode_events if not e["parse_success"])

        event_brief = " | ".join(
            f"s{e['step']}:a{e['action']} r={e['reward']:.2f}" for e in key_events
        )
        summary = (
            f"episode={episode} scored={int(scored)} total_reward={total_reward:.3f}; "
            f"key={event_brief}"
        )
        tags = f"scored={int(scored)} actions={','.join(map(str, action_set))} parse_fail={parse_fail_count}"
        priority = min(1.0, max(0.0, (1.0 if scored else 0.2) + min(0.6, abs(total_reward) / 2.0)))

        self.episodic.add(
            episode=episode,
            summary=summary,
            tags=tags,
            priority=priority,
        )
        self._episode_events = []
        self.working.clear()
