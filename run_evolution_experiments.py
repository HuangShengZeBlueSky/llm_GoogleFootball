import os
import json
import uuid
import time
import subprocess
import argparse
from datetime import datetime

# 导入 .env 与配置
from dotenv import load_dotenv
import yaml

_env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(os.path.abspath(_env_path))

from llm_football_agent.llm_client import LLMClient
from llm_football_agent.judge_critic import JudgeCritic

def _build_llm_client(model: str) -> LLMClient:
    api_key = os.getenv("LLM_API_KEY", "")
    api_base = os.getenv("LLM_API_BASE", None)
    provider = os.getenv("LLM_PROVIDER", "openai_compatible")
    
    return LLMClient(
        model=model,
        api_key=api_key,
        base_url=api_base,
        provider=provider,
        temperature=0.7, # 裁判用较高的temperature
        max_tokens=1024,
    )

def main():
    p = argparse.ArgumentParser()
    default_model = os.getenv("LLM_MODEL", "gemini-3-flash-preview")
    p.add_argument("--model", type=str, default=default_model, help="用于跑游戏和当裁判的大模型")
    p.add_argument("--generations", type=int, default=3, help="进化的代数")
    p.add_argument("--episodes", type=int, default=5, help="每一代跑多少局验证")
    p.add_argument("--max_steps", type=int, default=200, help="每局最大物理帧")
    args = p.parse_args()

    exp_id = f"evo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    base_log_dir = os.path.abspath(f"experiment_logs/{exp_id}")
    os.makedirs(base_log_dir, exist_ok=True)

    print(f"[{exp_id}] 启动战术自我进化实验 - 目标世代数: {args.generations}, 每代局数: {args.episodes}")

    judge = JudgeCritic(_build_llm_client(args.model))
    
    current_principles = "" # Gen 0: 0原则启动
    
    stats_log = []

    for gen in range(args.generations):
        print(f"\n{'='*50}")
        print(f"世代 Generation {gen} 开始")
        print(f"{'='*50}")
        
        gen_dir = os.path.join(base_log_dir, f"gen_{gen}")
        os.makedirs(gen_dir, exist_ok=True)
        
        # 1. 写入当前原则到文件
        principles_file = os.path.join(gen_dir, "current_principles.txt")
        with open(principles_file, "w", encoding="utf-8") as f:
            f.write(current_principles)
            
        print(f"\n[ Gen {gen} 战术打法 ]")
        if not current_principles:
            print("(无，基于模型本能 0 原则踢球)")
        else:
            print(current_principles)
        print("-" * 50)

        # 2. 生成此世代的 YAML 配置
        base_config_path = os.path.abspath("configs/config.yaml")
        with open(base_config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        cfg["experiment"]["num_episodes"] = args.episodes
        cfg["experiment"]["max_steps_per_episode"] = args.max_steps
        cfg["experiment"]["log_dir"] = gen_dir
        
        # 如果是 0 原则，覆盖 cfg 标志
        if not current_principles:
            cfg["experiment"]["empty_principles"] = True
        else:
            cfg["experiment"]["principles_file"] = principles_file
            
        cfg["llm"]["model"] = args.model
        
        tmp_cfg_path = os.path.join(gen_dir, "run_config.yaml")
        with open(tmp_cfg_path, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, allow_unicode=True)

        # 3. 运行跑马 (Blocking)
        print(f"\n[ Gen {gen} 比赛中...] 正在运行 {args.episodes} 局, 请稍候.")
        cmd = [
            "python", "llm_football_agent/run_game.py",
            "--config", tmp_cfg_path,
            "--interval", "5"
        ]
        
        # 隐藏大部分输出，只保留错误
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL)
        
        # 4. 分析本代胜率
        final_reports = glob.glob(os.path.join(gen_dir, "ep_*/final_report.json"))
        scored = 0
        for r in final_reports:
            with open(r, "r") as f:
                if json.load(f).get("scored", False):
                    scored += 1
                    
        win_rate = (scored / len(final_reports)) if final_reports else 0
        print(f"\n[ Gen {gen} 结束 ] 胜率: {win_rate*100:.1f}% ({scored}/{len(final_reports)})")
        
        stats_log.append({
            "generation": gen,
            "win_rate": win_rate,
            "wins": scored,
            "total": len(final_reports),
            "principles": current_principles
        })
        
        # 5. 评价与进化衍生下一代 (如果不是最后一代)
        if gen < args.generations - 1:
            print(f"\n[ 教练复盘 ] 请 Critic 评价 Gen {gen} 的录像并生成 Gen {gen+1} 战术...")
            new_principles = judge.evaluate_generation(gen_dir, current_principles)
            current_principles = new_principles
            
    # 最后保存总日志
    summary_path = os.path.join(base_log_dir, "evolution_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(stats_log, f, indent=2, ensure_ascii=False)
        
    print(f"\n进化实验完成! 结果已保存至: {summary_path}")
    print("\n--- 胜率进化曲线 ---")
    for s in stats_log:
        print(f"Gen {s['generation']}: {s['win_rate']*100:.1f}%")

if __name__ == "__main__":
    import glob
    main()
