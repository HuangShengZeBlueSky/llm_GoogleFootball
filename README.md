# 🤖 LLM Google Football Agent

一个基于大语言模型（LLM）的自动化足球战术决策框架。让大模型通过“文本观测-逻辑推理-指令输出”的闭环，实时接管 Google Research Football (GRF) 的球场！

当前主打场景：`academy_3_vs_1_with_keeper`（3名进攻球员对战1名防守球员+门将）。

在线文档：https://huangshengzebluesky.github.io/llm_GoogleFootball/
online doc:https://huangshengzebluesky.github.io/llm_GoogleFootball/
---

## 🏆 大模型选秀争霸赛排行榜 (Leaderboard)

基于本框架的多模型并行测试脚本，我们在相同环境超参下对四大主流模型进行了公平角逐（胜率优先，平均奖励次之）：

<div align="center">

| 🏅 战绩排名 | 🤖 参赛模型 | ⚽ 进球胜率 | 🌟 场均评分 (Reward) | ⚡ 拔剑速度 (延迟) | 🎯 战术执行步数 | ❌ 脑抽率 (解析失败) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| <h3 style="margin:0;">🥇 冠军</h3> | **`GLM-5`** | <b style="color:green;font-size:1.1em">80.0%</b> | **1.28** | 6.61s | **114.4** 步 | 0.0% |
| <h3 style="margin:0;">🥈 亚军</h3> | **`Gemini-3.0-Flash`** | <b style="color:blue;font-size:1.1em">40.0%</b> | 1.19 | **4.61s** | 258.4 步 | 0.0% |
| <h3 style="margin:0;">🥉 季军</h3> | **`Qwen-3-Max`** | <b style="color:orange;font-size:1.1em">20.0%</b> | 1.06 | 5.82s | 331.0 步 | 0.0% |
| 🛡️ 殿军 | **`Kimi-k2.5`** | <b style="color:red;font-size:1.1em">20.0%</b> | 0.81 | 6.38s | 325.6 步 | 0.0% |

> *测算基准：5局制淘汰赛，最大物理帧400步，模型思考间隔为 5 帧。*
> **赛事点评**：**`GLM-5`** 展现出统治级的突击破门能力（场均114步闪电战得分），而 **`Gemini-3.0-Flash`** 则斩获了最快的大脑思考速度（4.6秒/步）。所有模型指令解析成功率均达到惊人的 100%！

</div>

---

## 🏗️ 核心架构与原理解析

大模型看不懂视频像素，我们将复杂的 3D 足球环境转化为 LLM 可读懂的文字空间：
1. **👁 观测转译 (Obs-to-Text)**：将 GRF 的原始 `raw` 字典坐标系，转化为对齐的人类自然语言（例：“我方1号距球门0.3，前方有防守球员”）。
2. **🧠 大脑推理 (LLM Client)**：系统 Prompt 中预置战术板（跑位拉扯、倒三角传球等原则），按物理帧率定频呼叫大模型输出战术流。
3. **🦾 动作执剑 (Action Parser)**：将大模型反馈的 JSON/模糊文本（如 `{"action": 12, "reason": "打门!"}`），容错解析并映射到虚拟球场的 19 个硬编码动作方向。

---

## 📂 仓库结构

```text
.
├── llm_football_agent/      # 核心智能体引擎
│   ├── run_game.py          # ⚽单局游戏主控引擎
│   ├── llm_client.py        # 🧠统一模型网关接口
│   ├── obs_to_text.py       # 👁️态势感知模块
│   ├── action_parser.py     # 🦾指令解析器
│   └── logger.py            # 📝多模态对战日志器
├── configs/
│   └── config.yaml          # ⚙️单模型实验主配置文件
├── run_multiple_experiments.py # 🚀【打榜用】多模型批量评测赛马脚本
├── parse_leaderboard.py        # 📊【打榜用】自动解析日志产出榜单
└── experiment_logs/         # 📁实验战绩、JSON回放存档区
```

---

## 🚀 运行案例与使用指南 (Quick Start)

### 1. 环境与密钥准备

本系统兼容本地 GFootball 环境与服务器环境（支持 `--mock` 无图形化界面空跑推演）。
首先配置您的 `.env` 环境变量文件，填入主战车调用大模型的 API：
```ini
LLM_API_BASE=https://api.openai.com/v1  # 或你的中转代理 API
LLM_API_KEY=sk-xxxx...
LLM_MODEL=gpt-4o  # 你想用的基底主玩模型
```

### 2. 模式 A：单骑闯关（跑单个大模型性能测试）

测试你的 `.env` 指定的大模型能否流畅运行与进球：
```bash
# 采用 --interval 5 控制每 5 个物理帧呼叫一次 LLM 决策，共测 3 局
python llm_football_agent/run_game.py --episodes 3 --interval 5
```

### 3. 模式 B：诸神之战（多模型自动赛马实验）

想要一键测定大模型代码能力变迁进度？跑一个自动化赛马拉力测试！
1. 打开 `run_multiple_experiments.py`，修改 `MODELS_TO_TEST` 数组，填入各家模型参赛选手的 API 细节。
2. 运行自动化打榜（它会按顺序动态替换参数，互不干扰）：
```bash
python run_multiple_experiments.py
```
3. 执行解析指令。解析器会前往 `experiment_logs` 抓取最新鲜的战斗记录，一键出榜：
```bash
python parse_leaderboard.py
```

*所有高光录像、回合步骤拆解日志将保存在 `experiment_logs/exp_当前时间戳/` 各个模型的子文件夹内，便于溯源复盘。*
