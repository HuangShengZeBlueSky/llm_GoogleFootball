import os
import subprocess
import yaml
import time
from datetime import datetime
import shutil

from dotenv import load_dotenv
load_dotenv()

DEFAULT_API_KEY = os.getenv("LLM_API_KEY", "YOUR_API_KEY")
DEFAULT_BASE_URL = os.getenv("LLM_API_BASE", "YOUR_BASE_URL")

ZAIWEN_API_BASE = os.getenv("ZAIWEN_API_BASE", "https://back.zaiwenai.com/api/v1/ai")
ZAIWEN_API_KEY = os.getenv("ZAIWEN_API_KEY", "")

# --- 实验配置: 在这里定义你想一次性测试的模型 ---
MODELS_TO_TEST = [
    {
        "name": "grok-code-fast-1",
        "model": "grok-code-fast-1",
        "provider": "openai_compatible",
        "api_key": ZAIWEN_API_KEY,
        "base_url": ZAIWEN_API_BASE
    },
    {
        "name": "minimax-m2.1",
        "model": "minimax-m2.1",
        "provider": "openai_compatible",
        "api_key": ZAIWEN_API_KEY,
        "base_url": ZAIWEN_API_BASE
    },
    {
        "name": "gpt-oss-120b",
        "model": "gpt-oss-120b",
        "provider": "openai_compatible",
        "api_key": ZAIWEN_API_KEY,
        "base_url": ZAIWEN_API_BASE
    },
    {
        "name": "deepseek-v3.2",
        "model": "deepseek-v3.2",
        "provider": "openai_compatible",
        "api_key": ZAIWEN_API_KEY,
        "base_url": ZAIWEN_API_BASE
    },
    {
        "name": "claude-haiku-4.5",
        "model": "claude-haiku-4.5",
        "provider": "openai_compatible",
        "api_key": ZAIWEN_API_KEY,
        "base_url": ZAIWEN_API_BASE
    }
]

# 公共实验参数
CONFIG_FILE = "configs/config.yaml"
EPISODES_PER_MODEL = 10              # 每个模型跑的回合数
INTERVAL_STEPS = 5                   # 调用周期: 每隔5步让模型输出一次动作
MAX_STEPS_OVERRIDE = 200             # 每局最多200步
MAIN_LOG_DIR = "./experiment_logs"   # 统一存放本次大规模实验的数据
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

def run_experiments():
    experiment_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    experiment_base_path = os.path.join(BASE_PATH, MAIN_LOG_DIR, f"exp_{experiment_id}")
    os.makedirs(experiment_base_path, exist_ok=True)
    
    print(f"==================================================")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 启动批量实验评估，包含记忆消融实验")
    print(f"实验根目录: {experiment_base_path}")
    print(f"评估数量: {len(MODELS_TO_TEST)} 个模型 x 2 种内存策略 (With/Without Memory)")
    print(f"回合/组: {EPISODES_PER_MODEL}")
    print(f"==================================================")
    
    # 获取原始 config
    default_config_path = os.path.join(BASE_PATH, CONFIG_FILE)
    with open(default_config_path, "r", encoding="utf-8") as f:
        base_cfg = yaml.safe_load(f)
        
    for idx, exp_conf in enumerate(MODELS_TO_TEST):
        model_name = exp_conf["name"]
        print(f"\n==================================================")
        print(f"正在评估模型 [{idx+1}/{len(MODELS_TO_TEST)}]: {model_name} (Model: {exp_conf['model']}) ...")
        
        # 针对每个模型跑两组：with_memory 和 without_memory
        for memory_mode in ["with_memory", "without_memory"]:
            print(f"  -> 测试分支: {memory_mode}")
            
            # 1. 复制一份配置并修改特定参数
            tmp_cfg = dict(base_cfg)
            
            # 覆写 LLM 参数
            if "llm" not in tmp_cfg:
                 tmp_cfg["llm"] = {}
            tmp_cfg["llm"]["model"] = exp_conf.get("model", tmp_cfg["llm"]["model"])
            tmp_cfg["llm"]["provider"] = exp_conf.get("provider", tmp_cfg["llm"].get("provider", "openai_compatible"))
            
            if "api_key" in exp_conf:
                 tmp_cfg["llm"]["api_key"] = exp_conf["api_key"]
            if "base_url" in exp_conf:
                 tmp_cfg["llm"]["base_url"] = exp_conf["base_url"]
                 
            # 覆写 实验 日志目录，隔离存放
            # 增加子目录用于消融实验
            model_log_dir = os.path.join(experiment_base_path, f"{model_name}_{memory_mode}")
            if "experiment" not in tmp_cfg:
                 tmp_cfg["experiment"] = {}
            tmp_cfg["experiment"]["num_episodes"] = EPISODES_PER_MODEL
            tmp_cfg["experiment"]["log_dir"] = model_log_dir
            tmp_cfg["experiment"]["max_steps_per_episode"] = MAX_STEPS_OVERRIDE
            
            # 覆写 记忆 参数
            if memory_mode == "without_memory":
                # 将记忆池大小设为0，实现彻底的无记忆消融
                tmp_cfg["memory"] = {
                    "working_size": 0,
                    "episodic_size": 0,
                    "retrieval_top_k": 0
                }
            else:
                # 恢复默认带记忆的配置
                tmp_cfg["memory"] = {
                    "working_size": 8,
                    "episodic_size": 200,
                    "retrieval_top_k": 3
                }
            
            # 保存为一个临时 yaml
            tmp_yaml_path = os.path.join(BASE_PATH, f"tmp_config_{model_name}_{memory_mode}.yaml")
            with open(tmp_yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(tmp_cfg, f, allow_unicode=True)
                
            # 2. 调用命令
            cmd = [
                "python", "llm_football_agent/run_game.py",
                "--config", tmp_yaml_path,
                "--interval", str(INTERVAL_STEPS)
            ]
            
            start_time = time.time()
            try:
                # 运行测试
                subprocess.check_call(cmd, cwd=BASE_PATH)
                print(f"  [OK] 分支 {memory_mode} 评估完成，耗时: {time.time()-start_time:.1f}s")
            except subprocess.CalledProcessError as e:
                print(f"  [ERROR] 分支 {memory_mode} 运行失败, 忽略: {e}")
            finally:
                # 善后清理
                if os.path.exists(tmp_yaml_path):
                    os.remove(tmp_yaml_path)

    print("\n---------------------------------------------------------")
    print(f"[*] 全部记忆消融批量实验结束！日志保存在： {experiment_base_path}")
    print("你可以立即使用 'python parse_leaderboard.py' 来生成 Markdown 排行榜。")
    print("---------------------------------------------------------")


if __name__ == "__main__":
    run_experiments()
