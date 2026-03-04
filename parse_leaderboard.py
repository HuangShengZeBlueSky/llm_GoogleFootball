import os
import json
import glob
from collections import defaultdict

def generate_leaderboard():
    experiment_root = "./experiment_logs"
    if not os.path.exists(experiment_root):
        print(f"找不到 {experiment_root}，请先跑 run_multiple_experiments.py。")
        return

    # 获取最新一次运行产生的大实验目录，比如 exp_20250608_131415
    sub_dirs = [os.path.join(experiment_root, d) for d in os.listdir(experiment_root) 
                if os.path.isdir(os.path.join(experiment_root, d))]
    
    if not sub_dirs:
        print("未发现任何实验数据！")
        return
        
    latest_exp_dir = max(sub_dirs, key=os.path.getmtime)
    print(f"正在解析最新实验目录： {latest_exp_dir}")
    
    leaderboard_data = []

    # exp_xxxx/ 目录下是各个模型的文件夹，如 Gemini_Flash/, GPT_4o/
    model_dirs = [os.path.join(latest_exp_dir, d) for d in os.listdir(latest_exp_dir) 
                  if os.path.isdir(os.path.join(latest_exp_dir, d))]
    
    for mdir in model_dirs:
        model_name = os.path.basename(mdir)
        
        # 在模型文件夹中找寻最后的 session 报告 (因为logger存在session_*下面)
        session_dirs = sorted(glob.glob(os.path.join(mdir, "session_*")))
        if not session_dirs:
            continue
            
        latest_session = session_dirs[-1]
        report_file = os.path.join(latest_session, "final_report.json")
        csv_file = os.path.join(latest_session, "step_log.csv")
        
        if not os.path.exists(report_file):
            continue
            
        with open(report_file, "r", encoding="utf-8") as f:
            try:
                report = json.load(f)
            except Exception:
                continue

        # 如果需要更详细的 Latency计算或 ErrorRate计算，可以扫描 CSV
        # 读取 CSV 来计算"不可解析概率", "平均推理延迟"
        error_count = 0
        total_api_calls = 0
        total_latency_ms = 0.0
        
        if os.path.exists(csv_file):
            with open(csv_file, "r", encoding="utf-8") as f:
                header = f.readline().strip().split(",")
                try:
                    p_idx = header.index("parse_success")
                    l_idx = header.index("llm_time_ms")
                except ValueError:
                    p_idx, l_idx = -1, -1

                for line in f:
                    cols = line.strip().split(",")
                    if len(cols) <= max(p_idx, l_idx) or p_idx == -1:
                        continue
                        
                    # 只有LLM大模型实际发出的请求 (非延用的动作) time 会大于 0
                    time_val = float(cols[l_idx])
                    if time_val > 0:
                        total_api_calls += 1
                        total_latency_ms += time_val
                        # 如果 parse_success 标出 false
                        if cols[p_idx].lower() == "false":
                            error_count += 1
                            
        avg_latency_ms = (total_latency_ms / total_api_calls) if total_api_calls > 0 else 0
        error_rate = (error_count / total_api_calls) if total_api_calls > 0 else 0.0

        score_rate = report.get("score_rate", 0.0)
        avg_reward = report.get("avg_reward", 0.0)
        avg_steps  = report.get("avg_steps", 400.0)
        
        leaderboard_data.append({
            "model_name": model_name,
            "score_rate": score_rate,
            "avg_reward": avg_reward,
            "avg_steps": avg_steps,
            "avg_latency": avg_latency_ms,
            "error_rate": error_rate,
            "total_episodes": report.get("total_episodes", 0)
        })

    # 根据 Score Rate (排第一) -> Avg Reward (排第二) 降序排序
    leaderboard_data.sort(key=lambda x: (x["score_rate"], x["avg_reward"]), reverse=True)

    # 格式化存入 markdown
    md_out = os.path.join(latest_exp_dir, "LEADERBOARD.md")
    
    with open(md_out, "w", encoding="utf-8") as f:
        f.write("# 大语言模型玩足球 Leaderboard\n\n")
        f.write(f"> 解析实验源: `{os.path.basename(latest_exp_dir)}`\n\n")
        
        f.write("| 排名 | 模型 | 进球率 (Score/Win) | 平均总奖励 | 平均完成步数 | 平均响应延迟 | 解析失败率 | 样本(回合数) |\n")
        f.write("| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        
        for i, data in enumerate(leaderboard_data):
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}"
            
            row = [
                medal,
                f"`{data['model_name']}`",
                f"**{data['score_rate']*100:.1f}%**",
                f"{data['avg_reward']:.2f}",
                f"{data['avg_steps']:.1f}",
                f"{data['avg_latency']:.0f} ms",
                f"{data['error_rate']*100:.1f}%",
                f"{data['total_episodes']}"
            ]
            f.write("| " + " | ".join(row) + " |\n")

    # 输出供静态网页动态拉取的 json 数据
    json_out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(leaderboard_data, f, ensure_ascii=False, indent=2)
        
    print(f"\n[OK] Leaderboard 已成功生成: {md_out}")
    print(f"[OK] 网页前端接口数据已更新: {json_out}")
    print("\n--- 预览 ---")
    with open(md_out, "r", encoding="utf-8") as f:
        print(f.read())


if __name__ == "__main__":
    generate_leaderboard()
