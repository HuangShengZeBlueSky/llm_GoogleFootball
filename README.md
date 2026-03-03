# LLM Google Football

一个“让大模型实时决策玩 Google Research Football（GRF）”的实验仓库。  
当前默认场景是 `academy_3_vs_1_with_keeper`，支持真实 GRF 环境与 mock 环境。

---

## 1. 项目目标

- 把 GRF 原始观测（`raw obs`）转换成大模型可读文本。
- 让 LLM 在每 N 步输出离散动作（0~18），并在环境执行。
- 记录完整实验日志（step / episode / final）用于复盘、调优、评估。
- 提供可扩展架构：统一 LLM 网关、重试策略、记忆模块。

---

## 2. 仓库结构

```text
.
├── llm_football_agent/
│   ├── run_game.py          # 主入口：加载配置、创建环境、循环决策
│   ├── llm_client.py        # LLMGateway + Provider Adapter + Retry
│   ├── obs_to_text.py       # obs -> 文本（详细/紧凑）
│   ├── action_parser.py     # LLM 输出 -> action_id 容错解析
│   ├── memory.py            # Working/Episodic 记忆管理
│   ├── logger.py            # step/episode/final 结构化日志
│   └── mock_env.py          # 无 GRF 时的模拟环境
├── configs/
│   ├── config.yaml          # 主配置
│   └── config.quick.yaml    # 快速验证配置（短回合）
├── run_real_game.sh         # 实际运行脚本（conda + compact）
├── setup_conda_env.sh       # 一键安装依赖与 gfootball
├── .env.example             # 环境变量模板（不含真实密钥）
├── logs/                    # 结构化实验日志
└── grf_logs/                # GRF dump/video 等产物
```

---

## 3. 核心执行流程（端到端）

1) 启动入口：`llm_football_agent/run_game.py`  
2) 配置加载：`config.yaml -> .env 覆盖 -> CLI 覆盖`（CLI 优先级最高）  
3) 环境创建：真实 GRF 或 `--mock`  
4) 每回合循环：
- 每 `interval` 步调用一次 LLM；中间步复用上次动作
- `obs_to_text` 把观测转文本
- `memory.build_context()` 拼接记忆上下文
- `llm.decide()` 请求模型（带重试）
- `action_parser.parse_action()` 解析 JSON / 数字 / 关键词
- `env.step(action)` 执行动作
- `logger.log_step()` 写 step 级日志

5) 回合结束：
- `memory.end_episode()` 写入 episodic 经验
- `logger.log_episode_end()` 输出回合摘要

6) 全部结束：
- `logger.save_final_report()` 写汇总报告

---

## 4. 提示词 / obs / think / action 的结构化链路

### 4.1 obs（观测）
- 输入：GRF raw observation（位置、球权、比分、比赛模式等）。
- 转换：`obs_to_text.py`
  - `obs_to_text()`：详细版（信息全）
  - `obs_to_text_compact()`：紧凑版（省 token）

### 4.2 prompt（提示词）
`llm_client.py` 内采用模块化系统提示词（`PROMPT_MODULES`）：
- `role`：角色设定
- `scenario`：任务与场景
- `coordinate`：坐标语义
- `principles`：战术原则
- `thinking`：内部思考约束（不直接输出推理过程）
- `output`：强约束 JSON 输出格式

每次请求还会附加：
- `memory_context`（Working + Episodic 检索）
- `history`（最近几步决策）
- 当前 `obs_text`

### 4.3 think（决策）
- 在模型内部完成态势判断与策略选择。
- 工程层只接收结构化输出，不依赖“显式思维链”。

### 4.4 action（执行）
- 模型输出 -> `parse_action()` 容错解析 -> `action_id`。
- `run_game.py` 调用 `env.step(action_id)` 执行。
- 非 LLM 调用步复用上一动作（平衡 token 与实时性）。

---

## 5. 统一大模型入口（LLMGateway）

文件：`llm_football_agent/llm_client.py`

### 5.1 Provider 适配
- `openai_compatible`：OpenAI/vLLM/OneAPI 兼容接口
- `qwen`：当前复用 OpenAI-compatible 协议
- `gemini_native`：使用 `google-generativeai`（可选依赖）

### 5.2 重试策略
- 参数：`max_retries`（默认 5）
- 可重试：`timeout`、`429`、`5xx`
- 不重试：`4xx` 参数错误
- 退避：指数退避 `retry_backoff_base * 2^attempt`

### 5.3 统一返回字段
`decide()` 返回：
- `raw_response`
- `tokens`
- `elapsed`
- `raw_prompt`
- `retry_count`
- `error_type`
- `provider`

---

## 6. 记忆模块

文件：`llm_football_agent/memory.py`

- `WorkingMemory`：短期窗口（最近 N 步）
- `EpisodicMemory`：跨回合经验片段（检索 top-k）
- `MemoryManager`：
  - `on_step()`：写入当前回合轨迹
  - `build_context()`：构造提示词记忆上下文
  - `end_episode()`：提炼关键事件并沉淀到 episodic

---

## 7. 日志与产物

每次运行生成目录：`logs/session_YYYYMMDD_HHMMSS/`

- `step_log.csv`：逐步日志（关键字段）
  - `action_id`, `action_name`, `reason`
  - `parse_success`, `parse_path`
  - `llm_time_ms`, `tokens`, `retry_count`, `error_type`
  - `raw_prompt`, `raw_response`
  - `reward`, `cum_reward`, `score_left`, `score_right`

- `episode_XXX.json`：回合摘要 + step 明细
- `final_report.json`：总体统计
  - `score_rate`, `avg_reward`, `avg_steps`
  - `total_tokens`, `latency_p95_ms`

GRF 侧产物（视频/回放）在：`grf_logs/`

---

## 8. 配置说明

主配置：`configs/config.yaml`

### 8.1 llm
- `model`
- `provider`
- `api_key`
- `base_url`
- `temperature`
- `max_tokens`
- `timeout`
- `max_retries`
- `retry_backoff_base`

### 8.2 env
- `scenario`
- `representation`
- `rewards`
- `render`
- `write_video`
- `write_full_episode_dumps`
- `logdir`
- `num_controlled_players`

### 8.3 experiment
- `num_episodes`
- `max_steps_per_episode`
- `log_dir`

### 8.4 memory
- `working_size`
- `episodic_size`
- `retrieval_top_k`

配置优先级：`CLI > .env > config.yaml`

---

## 9. 快速开始

### 9.1 环境安装

```bash
bash setup_conda_env.sh
```

### 9.2 配置密钥

```bash
cp .env.example .env
# 编辑 .env，填写 LLM_API_KEY / LLM_API_BASE / LLM_MODEL
```

> `LLM_API_BASE` 请填写 API 根路径，不要填 `/chat/completions`。

### 9.3 运行

真实环境（推荐脚本）：

```bash
bash run_real_game.sh 5 5
```

手动运行：

```bash
python llm_football_agent/run_game.py --config configs/config.yaml --episodes 3 --interval 5
```

Mock 运行（无 gfootball 也可调试）：

```bash
python llm_football_agent/run_game.py --mock --episodes 2 --interval 5
```

Gemini 原生 provider：

```bash
python llm_football_agent/run_game.py --provider gemini_native
```

---

## 10. 安全与密钥防泄露（重要）

### 10.1 当前仓库策略
- `.env` 已在 `.gitignore` 中。
- `.env.example` 仅保留空占位，不含真实 key。

### 10.2 提交前建议

```bash
git status --short
git diff -- .env
```

确保 `.env` 没被 `git add`。

### 10.3 历史扫描（建议周期执行）

```bash
git grep -n -I -E 'sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z\-_]{20,}' $(git rev-list --all) --
```

### 10.4 若已泄露，必须做
1. 立刻在平台侧轮换/吊销密钥  
2. 重写 Git 历史（例如 `git filter-repo`）  
3. 强推后通知协作者重新拉取

---

## 11. 常见问题

- `404 Not Found`：通常是 `LLM_API_BASE` 配成了完整 endpoint。请改成根路径。  
- `Request timed out`：增大 `timeout`，并保留 `max_retries`。  
- `Gym has been unmaintained...`：兼容性提示，不一定影响当前运行。  
- 无图形界面服务器：设置 `SDL_VIDEODRIVER=dummy`（脚本已处理）。

---

## 12. 后续可扩展方向

- 自动提示词调优（离线评测 + 目标函数）
- 动作合法性先验过滤（rule-based safety layer）
- 更强记忆检索（向量化/语义检索）
- 多 agent 协同（传控/射门/防守角色分工）
