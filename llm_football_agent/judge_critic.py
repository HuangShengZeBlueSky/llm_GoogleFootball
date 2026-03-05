import os
import json
import glob
import pandas as pd
from typing import List, Dict

# 复用原有的 LLMClient 进行评价
from .llm_client import LLMClient


class JudgeCritic:
    """
    裁判与教练模块
    职责:
      1. 读取上一代的比赛日志（final_report.json, step_log.csv）
      2. 提取出“进球的成功经验”和“失球的失败教训”
      3. 呼叫大模型（Critic）总结出新一代的原则 (Principles)
    """

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def evaluate_generation(self, log_dir: str, current_principles: str) -> str:
        """
        评估一个世代的日志，返回下一代的新原则。
        """
        # 1. 解析日志
        summary_prompt = self._build_evaluation_prompt(log_dir, current_principles)
        
        # 2. 调用 LLM Critic
        print("[Judge/Critic] 正在思考并总结新一代战术原则...")
        
        # 使用统一网关调用
        # 将提示词组装为 user content，不需要外部历史
        messages = [
            {
                "role": "system", 
                "content": "你是一位世界顶级的足球教练 (Critic)。你的任务是通过复盘上一代 AI 球员的比赛录像数据，发现他们的问题，并总结出最多 5 条、且文字极其精炼的战术原则(Principles)，用于指导下一代 AI 比赛。"
            },
            {
                "role": "user",
                "content": summary_prompt
            }
        ]

        result = self.llm.adapter.generate(
            model=self.llm.model,
            messages=messages,
            temperature=0.7, # 稍微高一点的temperature以增加创新性
            max_tokens=800
        )
        
        new_principles = result.get("raw_response", "").strip()
        
        if not new_principles:
            print("[Judge/Critic] 警告: 未能生成有效的新原则，将原样返回。")
            return current_principles
            
        return new_principles

    def _build_evaluation_prompt(self, log_dir: str, current_principles: str) -> str:
        """从日志目录构建复盘提示词"""
        report_files = glob.glob(os.path.join(log_dir, "ep_*/final_report.json"))
        
        total_eps = len(report_files)
        scored_eps = 0
        failed_eps = 0
        
        success_cases = []
        failure_cases = []
        
        for rf in report_files:
            try:
                with open(rf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                ep = data.get("episode", 0)
                scored = data.get("scored", False)
                
                # 读取对应的 step log 提取最后几步关键动作
                csv_file = os.path.join(os.path.dirname(rf), "step_log.csv")
                last_actions = ""
                if os.path.exists(csv_file):
                    df = pd.read_csv(csv_file)
                    # 提取最后 5 步的动作
                    if not df.empty:
                        tail = df.tail(5)
                        last_actions = ", ".join(tail["action_name"].astype(str).tolist())
                
                if scored:
                    scored_eps += 1
                    success_cases.append(f"局次 {ep}: 进球成功。最后关键动作序列: [{last_actions}]。")
                else:
                    failed_eps += 1
                    failure_cases.append(f"局次 {ep}: 未能进球。最后动作序列: [{last_actions}]。")
            except Exception as e:
                print(f"[Judge/Critic] 无法读取 {rf}: {e}")

        # 抽样显示，防止 prompt 过长
        s_text = "\n".join(success_cases[:3]) if success_cases else "无成功进球局。"
        f_text = "\n".join(failure_cases[:5]) if failure_cases else "无失败局。"

        prompt = f"""
【上一代比赛复盘报告】
总场次: {total_eps}
进球场次: {scored_eps}
失败场次: {failed_eps}

【使用的旧战术原则】:
{current_principles if current_principles else "(无，0 原则启动)"}

【成功局关键动作截取(抽样)】:
{s_text}

【失败局关键动作截取(抽样)】:
{f_text}

【你的任务】
基于以上胜负数据和关键动作序列（例如一直盲目带球导致失败，或通过短传+射门成功），对旧的战术原则进行**修订和进化**。
1. 如果失败率高，指出球员可能犯的常见错误（如不传球），并在新原则中重点强调。
2. 你必须输出一个纯文本的、不超过 5 条的【核心战术原则】。
3. 这些原则将被直接插入到下一代球员的提示词中，所以语气必须是**直接命令**（例如：“1. 接近球门果断射门”）。
4. **不要输出任何其他解释性废话，直接输出新原则的内容。**
格式参考：
1. xxx
2. xxx
3. xxx
"""
        return prompt
