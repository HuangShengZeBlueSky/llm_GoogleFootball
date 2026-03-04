# 快速开始

在本章节，你将学会如何将项目克隆到本地，配置大模型 API，并跑通你的第一局游戏！

## 1. 环境安装

本仓库依赖于 Python 环境以及底层经过修改的 `gfootball` 引擎。推荐使用 Conda 隔离环境：

```bash
# 克隆本仓库
git clone https://github.com/HuangShengZeBlueSky/llm_GoogleFootball.git
cd llm_GoogleFootball

# 运行一键环境搭建脚本 (自动创建 conda env 并安装所需特定版本引擎)
bash setup_conda_env.sh
```

## 2. 配置大模型密钥

我们将所有的敏感配置（API 密钥）隔离在项目根目录的 `.env` 文件中。

首先，基于演示模板复制一份真实配置：
```bash
cp .env.example .env
```

接着，打开 `.env` 并填写你偏好的大模型提供商 API：
```ini
# OpenAI-compatible LLM endpoint
# 例: https://api.openai.com/v1 或你的代理地址 (注意不要加 /chat/completions)
LLM_API_BASE=https://api.openai.com/v1

# 必填: API Key
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxx

# 模型名（需与服务端可用模型严格一致）
LLM_MODEL=gpt-4o
```

## 3. 运行你的第一场比赛！

### 模式 A：跑个 Demo 环境玩玩

如果你只想看看模型是不是能活着输出格式化的战术动作，可以使用我们的快捷配置：

```bash
# 使用快速验证配置 (回合数较少) 跑两局，每 5 帧调用一次 LLM
python llm_football_agent/run_game.py --config configs/config.quick.yaml --episodes 2 --interval 5
```

### 模式 B：火力全开 (真实游戏对局)

启动挂载全量日志的真实对局测试（脚本会自动处理无头服务器显示驱动等边界问题）：

```bash
# 格式：bash run_real_game.sh <回合总数> <决策跳帧间隔>
bash run_real_game.sh 5 5
```

当这局运行结束时，你可以在自动生成的 `experiment_logs/exp_当前时间戳` 文件夹下看到所有的模型对局步进日志、最终 JSON 报表以及回放录像！
