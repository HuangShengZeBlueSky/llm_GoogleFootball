"""
策略对照测试 (Test Method)
==========================
使用 Gemini 原生 API，对 4 种不同策略进行标准化评估：
  1. 空策略 (Empty)      — 0 原则，大模型裸奔
  2. 迭代第一次策略 (Gen1) — 由教练在 train 阶段自动总结
  3. 迭代第二次策略 (Gen2) — 教练在 Gen1 基础上再次迭代
  4. 初始手工策略 (Manual) — PROMPT_MODULES 中人工编写的 5 条原则

每种策略跑 N 轮 (默认 15)，最后输出对比报告。

用法:
    python run_test_experiments.py
    python run_test_experiments.py --episodes 20 --max_steps 200 --interval 5
"""

import os
import json
import glob
import time
import subprocess
import argparse
from datetime import datetime

from dotenv import load_dotenv
import yaml

_env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(os.path.abspath(_env_path))

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

# ── 四种待测试策略 ──────────────────────────────────────

STRATEGIES = {
    "empty": {
        "label": "Empty (0原则裸奔)",
        "principles": "",   # 空字符串 → 触发 empty_principles
    },
    "gen1_evolved": {
        "label": "Gen1 Evolved (教练第一次迭代)",
        "principles": (
            "1. 迅速靠近皮球并确保持球权。\n"
            "2. 遭遇拦截立即传球给空位队友。\n"
            "3. 进入射程范围内果断起脚射门。\n"
            "4. 无球状态下积极跑向进攻空间。\n"
            "5. 防守时优先挡在球与己方球门之间。"
        ),
    },
    "gen2_evolved": {
        "label": "Gen2 Evolved (教练第二次迭代)",
        "principles": (
            "1. 抢占球权：全速靠近并稳定控制皮球。\n"
            "2. 预判传球：被封堵前传向空位队友。\n"
            "3. 果断终结：进入射程后果断起脚射门。\n"
            "4. 动态接应：无球时持续拉开传球线路。\n"
            "5. 铁壁防守：防守时始终封锁进球路线。"
        ),
    },
    "manual_original": {
        "label": "Manual Original (人工手写初始策略)",
        "principles": (
            "1. 当持球者前方有防守者挡住 → 传球(11短传/9长传/10高球)给空位队友\n"
            "2. 接近球门(x > 0.85)且射角合适 → 果断射门(12)\n"
            "3. 传球方向由当前移动方向决定 → 先设方向(1-8)，再执行传球\n"
            "4. 利用3打1的人数优势 → 拉开空间，做三角传球配合\n"
            "5. 不要长时间盘带 → 快速传切更有效"
        ),
    },
}


def main():
    p = argparse.ArgumentParser(description="Strategy ablation test (Test Method)")
    p.add_argument("--episodes", type=int, default=15, help="每种策略跑多少轮")
    p.add_argument("--max_steps", type=int, default=200, help="每轮最大步数")
    p.add_argument("--interval", type=int, default=5, help="LLM 调用间隔")
    p.add_argument("--provider", type=str, default=None,
                   help="LLM provider (默认从 .env 读取)")
    p.add_argument("--model", type=str, default=None,
                   help="LLM model (默认从 .env 读取)")
    args = p.parse_args()

    # 决定用哪个 provider/model
    # Test 实验默认走 Gemini 原生 API (不走 Zaiwen 代理)
    provider = args.provider or "gemini_native"
    model = args.model or os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

    # API key: Test 实验专用 GEMINI_API_KEY
    api_key = os.getenv("GEMINI_API_KEY", "")
    api_base = ""

    if provider not in ("gemini_native", "gemini", "google"):
        # 如果用户手动指定了其他 provider，则切换到对应的 key
        api_key = os.getenv("LLM_API_KEY", "")
        api_base = os.getenv("LLM_API_BASE", "")

    exp_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    experiment_dir = os.path.join(BASE_PATH, "experiment_logs", exp_id)
    os.makedirs(experiment_dir, exist_ok=True)

    print("=" * 60)
    print(f"[TEST METHOD] 策略对照实验")
    print(f"实验 ID:   {exp_id}")
    print(f"Provider:  {provider}")
    print(f"Model:     {model}")
    print(f"Episodes:  {args.episodes} | Max Steps: {args.max_steps} | Interval: {args.interval}")
    print(f"策略数量:  {len(STRATEGIES)}")
    print(f"总共需跑:  {len(STRATEGIES) * args.episodes} 局")
    print("=" * 60)

    # 加载基础 config
    base_config_path = os.path.join(BASE_PATH, "configs", "config.yaml")
    with open(base_config_path, "r", encoding="utf-8") as f:
        base_cfg = yaml.safe_load(f)

    results = {}

    for strat_key, strat_info in STRATEGIES.items():
        label = strat_info["label"]
        principles_text = strat_info["principles"]

        print(f"\n{'=' * 60}")
        print(f"[TEST] 正在测试策略: {label}")
        print(f"{'=' * 60}")

        strat_dir = os.path.join(experiment_dir, strat_key)
        os.makedirs(strat_dir, exist_ok=True)

        # 写入 principles 文件
        principles_file = os.path.join(strat_dir, "principles.txt")
        with open(principles_file, "w", encoding="utf-8") as f:
            f.write(principles_text)

        # 生成临时 config
        cfg = dict(base_cfg)
        if "llm" not in cfg:
            cfg["llm"] = {}
        cfg["llm"]["model"] = model
        cfg["llm"]["provider"] = provider
        cfg["llm"]["api_key"] = api_key
        if api_base:
            cfg["llm"]["base_url"] = api_base

        if "experiment" not in cfg:
            cfg["experiment"] = {}
        cfg["experiment"]["num_episodes"] = args.episodes
        cfg["experiment"]["max_steps_per_episode"] = args.max_steps
        cfg["experiment"]["log_dir"] = strat_dir

        # 策略注入方式
        if principles_text.strip() == "":
            cfg["experiment"]["empty_principles"] = True
        else:
            cfg["experiment"]["principles_file"] = principles_file

        tmp_yaml_path = os.path.join(strat_dir, "test_config.yaml")
        with open(tmp_yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, allow_unicode=True)

        # 运行游戏
        cmd = [
            "python", "llm_football_agent/run_game.py",
            "--config", tmp_yaml_path,
            "--interval", str(args.interval)
        ]

        start_time = time.time()
        try:
            subprocess.check_call(cmd, cwd=BASE_PATH, stdout=subprocess.DEVNULL)
            elapsed = time.time() - start_time
            print(f"  [OK] 策略 '{strat_key}' 测试完成, 耗时: {elapsed:.1f}s")
        except subprocess.CalledProcessError as e:
            elapsed = time.time() - start_time
            print(f"  [ERROR] 策略 '{strat_key}' 运行失败: {e}")

        # 读取该策略的 final_report.json
        reports = glob.glob(os.path.join(strat_dir, "**", "final_report.json"), recursive=True)
        if reports:
            with open(reports[0], "r", encoding="utf-8") as f:
                report = json.load(f)
            results[strat_key] = {
                "label": label,
                "win_rate": report.get("score_rate", 0),
                "scored_episodes": report.get("scored_episodes", 0),
                "total_episodes": report.get("total_episodes", 0),
                "avg_reward": report.get("avg_reward", 0),
                "avg_steps": report.get("avg_steps", 0),
                "total_tokens": report.get("total_tokens", 0),
                "latency_p95_ms": report.get("latency_p95_ms", 0),
                "elapsed_seconds": elapsed,
                "principles": principles_text,
            }
        else:
            results[strat_key] = {
                "label": label,
                "win_rate": 0, "scored_episodes": 0, "total_episodes": 0,
                "avg_reward": 0, "avg_steps": 0, "total_tokens": 0,
                "latency_p95_ms": 0, "elapsed_seconds": elapsed,
                "principles": principles_text,
            }

    # ── 输出对比报告 ──────────────────────────────────────
    report_path = os.path.join(experiment_dir, "test_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n")
    print("=" * 70)
    print("                 [TEST METHOD] 策略对照实验报告")
    print("=" * 70)
    print(f"{'策略':<30} {'胜率':>8} {'进球/总':>10} {'平均步数':>10} {'平均奖励':>10} {'Token总量':>12}")
    print("-" * 70)

    for strat_key, r in results.items():
        label_short = r["label"][:28]
        wr = f"{r['win_rate']*100:.1f}%"
        wt = f"{r['scored_episodes']}/{r['total_episodes']}"
        print(f"{label_short:<30} {wr:>8} {wt:>10} {r['avg_steps']:>10.1f} {r['avg_reward']:>10.3f} {r['total_tokens']:>12}")

    print("-" * 70)
    
    # 找到最佳策略
    best_key = max(results, key=lambda k: (results[k]["win_rate"], results[k]["avg_reward"]))
    best = results[best_key]
    print(f"\n[BEST] 最佳策略: {best['label']}")
    print(f"       胜率: {best['win_rate']*100:.1f}% | 平均步数: {best['avg_steps']:.1f} | 平均奖励: {best['avg_reward']:.3f}")

    print(f"\n详细报告已保存至: {report_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
