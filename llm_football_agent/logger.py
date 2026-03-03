"""
结构化日志记录器 — 记录每步决策、回合结果和最终实验报告。

输出:
  session_<timestamp>/
    ├── step_log.csv          # 每步 CSV
    ├── episode_NNN.json      # 每回合 JSON
    └── final_report.json     # 汇总
"""

import csv
import json
import os
from datetime import datetime


class GameLogger:
    def __init__(self, log_dir: str):
        os.makedirs(log_dir, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(log_dir, f"session_{ts}")
        os.makedirs(self.session_dir, exist_ok=True)

        # CSV
        self.csv_path = os.path.join(self.session_dir, "step_log.csv")
        self._csv_fh = open(self.csv_path, "w", newline="", encoding="utf-8")
        self._csv = csv.writer(self._csv_fh)
        self._csv.writerow([
            "episode", "step",
            "ball_x", "ball_y", "active_player", "ball_owner",
            "action_id", "action_name", "reason",
            "parse_success", "parse_path",
            "llm_time_ms", "tokens", "retry_count", "error_type",
            "reward", "cum_reward", "score_left", "score_right",
            "raw_prompt", "raw_response",
        ])

        self.episode_summaries: list[dict] = []
        self._ep_details: list[dict] = []
        self._all_latencies_ms: list[float] = []

    # ─── per-step ───────────────────────────────────────

    def log_step(
        self, *, episode, step, obs,
        action_id, action_name, reason,
        parse_success, parse_path,
        llm_time, tokens, retry_count, error_type,
        raw_prompt, raw_response,
        reward, cumulative_reward,
    ):
        ball = obs["ball"]
        latency_ms = float(llm_time) * 1000
        self._all_latencies_ms.append(latency_ms)

        self._csv.writerow([
            episode, step,
            f"{ball[0]:.4f}", f"{ball[1]:.4f}",
            obs["active"], obs["ball_owned_team"],
            action_id, action_name, reason[:80],
            parse_success, parse_path,
            f"{latency_ms:.0f}", tokens, retry_count, error_type,
            reward, f"{cumulative_reward:.3f}",
            obs["score"][0], obs["score"][1],
            (raw_prompt or "")[:1000], (raw_response or "")[:1000],
        ])
        self._csv_fh.flush()

        self._ep_details.append({
            "step": int(step),
            "ball": [round(float(ball[0]), 4), round(float(ball[1]), 4)],
            "active": int(obs["active"]),
            "action": int(action_id),
            "action_name": action_name,
            "reason": reason,
            "parse_path": parse_path,
            "retry_count": int(retry_count),
            "error_type": error_type,
            "llm_time_ms": round(latency_ms, 2),
            "raw_prompt": raw_prompt,
            "raw_response": raw_response,
            "reward": float(reward),
        })

    # ─── per-episode ────────────────────────────────────

    def log_episode_end(self, episode, total_steps, total_reward,
                        scored, llm_stats):
        summary = {
            "episode": int(episode),
            "steps": int(total_steps),
            "reward": round(float(total_reward), 4),
            "scored": bool(scored),
            "llm_calls": int(llm_stats.get("total_calls", 0)),
            "tokens": int(llm_stats.get("total_tokens", 0)),
            "latency_p95_ms": float(llm_stats.get("latency_p95_ms", 0.0)),
            "avg_retry_count": float(llm_stats.get("avg_retry_count", 0.0)),
            "ts": datetime.now().isoformat(),
        }
        self.episode_summaries.append(summary)

        path = os.path.join(self.session_dir, f"episode_{episode:03d}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "steps": self._ep_details},
                      f, ensure_ascii=False, indent=2)
        self._ep_details = []

        print(
            f"[Ep {episode}] steps={total_steps} reward={total_reward:.3f} "
            f"scored={scored} tokens={llm_stats.get('total_tokens',0)}"
        )

    # ─── final report ───────────────────────────────────

    def save_final_report(self) -> dict:
        total = len(self.episode_summaries)
        scored = sum(1 for s in self.episode_summaries if s["scored"])

        report = {
            "total_episodes": total,
            "scored_episodes": scored,
            "score_rate": scored / max(1, total),
            "avg_reward": sum(s["reward"] for s in self.episode_summaries) / max(1, total),
            "avg_steps": sum(s["steps"] for s in self.episode_summaries) / max(1, total),
            "total_tokens": sum(s["tokens"] for s in self.episode_summaries),
            "latency_p95_ms": round(self._percentile(self._all_latencies_ms, 95), 2),
            "episodes": self.episode_summaries,
        }

        path = os.path.join(self.session_dir, "final_report.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*50}")
        print(f"实验完成！进球率: {scored}/{total} = {report['score_rate']*100:.1f}%")
        print(f"平均奖励: {report['avg_reward']:.3f}")
        print(f"总 Token: {report['total_tokens']}")
        print(f"结果 → {self.session_dir}")
        print(f"{'='*50}")
        return report

    # ─── cleanup ────────────────────────────────────────

    def close(self):
        self._csv_fh.close()

    @staticmethod
    def _percentile(values: list[float], p: int) -> float:
        if not values:
            return 0.0
        arr = sorted(values)
        idx = min(len(arr) - 1, max(0, int(round((p / 100) * (len(arr) - 1)))))
        return float(arr[idx])
