"""
主运行脚本 — LLM 玩 academy_3_vs_1_with_keeper

用法:
    python run_game.py                                # 默认配置
    python run_game.py --episodes 3 --interval 5      # 3回合，每5步调LLM
    python run_game.py --compact --interval 10         # 省token模式
    python run_game.py --mock --episodes 2             # 模拟模式(无gfootball也能跑)
"""

import argparse
import os
import sys

# ── 加载 .env ────────────────────────────────────────────
from dotenv import load_dotenv

_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(os.path.abspath(_env_path))

import yaml

# ── 检测 gfootball 是否可用 ───────────────────────────────
_HAS_GRF = False
try:
    import gfootball.env as football_env
    _HAS_GRF = True
except ImportError:
    pass

from mock_env import create_mock_environment             # 始终可用

from obs_to_text import obs_to_text, obs_to_text_compact
from llm_client import LLMClient
from action_parser import parse_action, ACTION_NAMES
from logger import GameLogger


# ── 配置 ────────────────────────────────────────────────

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def merge_env_into_config(cfg: dict) -> dict:
    """用 .env 环境变量覆盖 config.yaml 里的 LLM 配置（.env 优先）"""
    llm = cfg.setdefault("llm", {})
    if os.getenv("LLM_API_BASE"):
        llm["base_url"] = os.getenv("LLM_API_BASE")
    if os.getenv("LLM_API_KEY"):
        llm["api_key"] = os.getenv("LLM_API_KEY")
    if os.getenv("LLM_MODEL"):
        llm["model"] = os.getenv("LLM_MODEL")
    return cfg


# ── 环境 ────────────────────────────────────────────────

def create_env(cfg: dict, use_mock: bool = False):
    if use_mock or not _HAS_GRF:
        if not _HAS_GRF:
            print("[!] gfootball 未安装，自动切换到模拟环境 (mock)")
        else:
            print("[i] 使用模拟环境 (--mock)")
        return create_mock_environment(
            max_steps=cfg["experiment"].get("max_steps_per_episode", 400),
        )

    c = cfg["env"]
    return football_env.create_environment(
        env_name=c["scenario"],
        representation=c.get("representation", "raw"),
        rewards=c.get("rewards", "scoring,checkpoints"),
        write_video=c.get("write_video", True),
        write_full_episode_dumps=c.get("write_full_episode_dumps", True),
        write_goal_dumps=True,
        render=c.get("render", False),
        logdir=c.get("logdir", "./grf_logs"),
        number_of_left_players_agent_controls=c.get("num_controlled_players", 1),
    )


# ── 单回合 ──────────────────────────────────────────────

def run_episode(
    env, llm: LLMClient, logger: GameLogger,
    episode_id: int, max_steps: int,
    call_interval: int = 5,
    verbose: bool = True,
    compact_obs: bool = False,
):
    """
    运行一个 episode。

    Args:
        call_interval: 每隔多少步调用一次 LLM（中间步复用上次动作）
        compact_obs:   使用紧凑观测文本（省 token）
    """
    obs = env.reset()
    if isinstance(obs, list):
        obs = obs[0]

    done = False
    total_reward = 0.0
    step = 0
    history = []
    cur_action = 0
    cur_reason = "初始"

    while not done and step < max_steps:
        call_llm = (step % call_interval == 0) or step == 0

        if call_llm:
            obs_text = (obs_to_text_compact(obs) if compact_obs
                        else obs_to_text(obs, include_tactical_hints=True))

            result = llm.decide(obs_text, history=history[-5:])

            if "error" in result:
                print(f"  [LLM Error @ step {step}] {result['error']}")
                cur_action, cur_reason, parse_ok = 0, "LLM调用失败", False
            else:
                parsed = parse_action(result["raw_response"])
                cur_action = parsed["action"]
                cur_reason = parsed["reason"]
                parse_ok = parsed["parse_success"]

                if verbose:
                    print(
                        f"  Step {step}: → {cur_action}"
                        f"({ACTION_NAMES.get(cur_action, '?')}) "
                        f"| {cur_reason[:40]} "
                        f"| {result['elapsed']*1000:.0f}ms"
                    )
        else:
            parse_ok = True
            result = {"elapsed": 0, "tokens": 0}

        # env step
        next_obs, reward, done, info = env.step(cur_action)
        if isinstance(next_obs, list):
            next_obs = next_obs[0]
        if isinstance(reward, list):
            reward = reward[0]
        if isinstance(done, list):
            done = done[0]

        total_reward += reward

        logger.log_step(
            episode=episode_id, step=step, obs=obs,
            action_id=cur_action,
            action_name=ACTION_NAMES.get(cur_action, "?"),
            reason=cur_reason,
            parse_success=parse_ok,
            llm_time=result.get("elapsed", 0),
            tokens=result.get("tokens", 0),
            reward=reward,
            cumulative_reward=total_reward,
        )

        if call_llm:
            history.append({"step": step, "action": cur_action, "reason": cur_reason})

        obs = next_obs
        step += 1

    scored = obs["score"][0] > 0
    logger.log_episode_end(
        episode=episode_id, total_steps=step,
        total_reward=total_reward, scored=scored,
        llm_stats=llm.get_stats(),
    )
    return scored, total_reward, step


# ── main ────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="LLM plays academy_3_vs_1_with_keeper")
    default_config = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "configs", "config.yaml"))
    p.add_argument("--config", default=default_config)
    p.add_argument("--episodes", type=int, default=None)
    p.add_argument("--interval", type=int, default=5, help="LLM 调用间隔（步）")
    p.add_argument("--compact", action="store_true", help="紧凑观测文本")
    p.add_argument("--verbose", action="store_true", default=True)
    p.add_argument("--mock", action="store_true",
                   help="使用模拟环境(无需安装 gfootball)")
    # CLI 覆盖 API 配置（可选，优先级: CLI > .env > config.yaml）
    p.add_argument("--api_base", type=str, default=None,
                   help="LLM API base URL")
    p.add_argument("--api_key", type=str, default=None,
                   help="LLM API key")
    p.add_argument("--model", type=str, default=None,
                   help="LLM model name")
    args = p.parse_args()

    # 加载配置: config.yaml → .env 覆盖 → CLI 覆盖
    cfg = load_config(args.config)
    cfg = merge_env_into_config(cfg)

    # CLI 参数最高优先级
    if args.api_base:
        cfg["llm"]["base_url"] = args.api_base
    if args.api_key:
        cfg["llm"]["api_key"] = args.api_key
    if args.model:
        cfg["llm"]["model"] = args.model

    n_ep = args.episodes or cfg["experiment"]["num_episodes"]

    use_mock = args.mock
    mode_str = "模拟环境" if (use_mock or not _HAS_GRF) else "GRF 真实环境"

    print(f"{'='*50}")
    print(f"LLM Football Agent — academy_3_vs_1_with_keeper")
    print(f"Model:    {cfg['llm']['model']}")
    print(f"API Base: {cfg['llm'].get('base_url', 'default')}")
    print(f"环境模式: {mode_str}")
    print(f"Episodes: {n_ep} | Interval: {args.interval}")
    print(f"{'='*50}\n")

    env = create_env(cfg, use_mock=use_mock)
    llm = LLMClient(
        model=cfg["llm"]["model"],
        api_key=cfg["llm"]["api_key"],
        base_url=cfg["llm"].get("base_url"),
        temperature=cfg["llm"].get("temperature", 0.3),
        max_tokens=cfg["llm"].get("max_tokens", 1024),
    )
    logger = GameLogger(cfg["experiment"]["log_dir"])

    for ep in range(n_ep):
        print(f"\n--- Episode {ep+1}/{n_ep} ---")
        run_episode(
            env, llm, logger,
            episode_id=ep,
            max_steps=cfg["experiment"].get("max_steps_per_episode", 10),
            call_interval=args.interval,
            verbose=args.verbose,
            compact_obs=args.compact,
        )

    logger.save_final_report()
    logger.close()
    env.close()


if __name__ == "__main__":
    main()
