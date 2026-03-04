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

# --- 实验配置: 在这里定义你想一次性测试的模型 ---
# 包含不同的模型名称和它们的API参数
# 你可以在这里配置: model, api_key, base_url, provider, api_timeout 等
MODELS_TO_TEST = [
    {
        "name": "Kimi_k2_5",
        "model": "kimi-k2.5",
        "provider": "openai_compatible",
        "api_key": DEFAULT_API_KEY,
        "base_url": DEFAULT_BASE_URL
    },
    {
        "name": "GLM_5",
        "model": "GLM-5",
        "provider": "openai_compatible",
        "api_key": DEFAULT_API_KEY,
        "base_url": DEFAULT_BASE_URL
    },
    {
        "name": "Gemini_3_0_Flash",
        "model": "Gemini-3.0-Flash",
        "provider": "openai_compatible",
        "api_key": DEFAULT_API_KEY,
        "base_url": DEFAULT_BASE_URL
    },
    {
        "name": "Qwen_3_Max",
        "model": "Qwen-3-Max",
        "provider": "openai_compatible",
        "api_key": DEFAULT_API_KEY,
        "base_url": DEFAULT_BASE_URL
    }
]

# 公共实验参数
CONFIG_FILE = "configs/config.yaml"
EPISODES_PER_MODEL = 5               # 每个模型跑的回合数
INTERVAL_STEPS = 5                   # 调用周期: 每隔5步让模型输出一次动作
MAX_STEPS_OVERRIDE = 400             # 恢复到400，让物理引擎有足够的时间跑到终点
MAIN_LOG_DIR = "./experiment_logs"   # 统一存放本次大规模实验的数据
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

def run_experiments():
    experiment_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    experiment_base_path = os.path.join(BASE_PATH, MAIN_LOG_DIR, f"exp_{experiment_id}")
    os.makedirs(experiment_base_path, exist_ok=True)
    
    print(f"==================================================")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 启动批量实验评估，实验根目录: {experiment_base_path}")
    print(f"评估数量: {len(MODELS_TO_TEST)} 个不同配置模型 | 回合/模型: {EPISODES_PER_MODEL}")
    print(f"==================================================")
    
    # 获取原始 config
    default_config_path = os.path.join(BASE_PATH, CONFIG_FILE)
    with open(default_config_path, "r", encoding="utf-8") as f:
        base_cfg = yaml.safe_load(f)
        
    for idx, exp_conf in enumerate(MODELS_TO_TEST):
        model_name = exp_conf["name"]
        print(f"\n[{idx+1}/{len(MODELS_TO_TEST)}] 正在评估模型: {model_name} (Model: {exp_conf['model']}) ...")
        
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
        model_log_dir = os.path.join(experiment_base_path, model_name)
        if "experiment" not in tmp_cfg:
             tmp_cfg["experiment"] = {}
        tmp_cfg["experiment"]["num_episodes"] = EPISODES_PER_MODEL
        tmp_cfg["experiment"]["log_dir"] = model_log_dir
        tmp_cfg["experiment"]["max_steps_per_episode"] = MAX_STEPS_OVERRIDE
        
        # 保存为一个临时 yaml
        tmp_yaml_path = os.path.join(BASE_PATH, f"tmp_config_{model_name}.yaml")
        with open(tmp_yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(tmp_cfg, f, allow_unicode=True)
            
        # 2. 调用命令
        cmd = [
            "python", "llm_football_agent/run_game.py",
            "--config", tmp_yaml_path,
            "--interval", str(INTERVAL_STEPS)
            # '--mock' # 若需要测试可加上
        ]
        
        start_time = time.time()
        try:
            # 运行测试
            subprocess.check_call(cmd, cwd=BASE_PATH)
            print(f"[OK] 模型 {model_name} 评估完成，耗时: {time.time()-start_time:.1f}s")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] 模型 {model_name} 运行失败, 忽略并进入下一个实验。 错误: {e}")
        finally:
            # 善后清理
            if os.path.exists(tmp_yaml_path):
                os.remove(tmp_yaml_path)

    print("\n---------------------------------------------------------")
    print(f"[*] 全部批处理实验结束！日志保存在： {experiment_base_path}")
    print("你可以立即使用 'python parse_leaderboard.py' 来生成 Markdown 排行榜。")
    print("---------------------------------------------------------")


if __name__ == "__main__":
    run_experiments()
