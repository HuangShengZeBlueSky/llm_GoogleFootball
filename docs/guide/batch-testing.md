# 多模型批量赛马测试

当你已经跑通了单机，修改了提示词后，你就一定想知道：**到底哪家大模型在当前设定下最聪明、战绩最好？**

我们需要自动化的赛道，而不仅仅是手工开十个终端。

## 1. 原理与配置

打榜引擎 `run_multiple_experiments.py` 的核心逻辑是循环遍历你登记的 `MODELS_TO_TEST`。它会：
1. 为每一次角斗生成唯一的 Session ID (`exp_2026xxxx_xxxxxx`)。
2. 将环境超参强制替换为你规定的常量（比如 `interval=5`, `epsiodes=5`），保证公平竞技。
3. 循环拉起子进程执行 `run_game.py`，并将原本散布杂乱的 JSON 日志，按模型类别优雅归档在同一大文件夹下，方便你排查哪一局哪一步大模型脑抽了。

## 2. 登记选秀模型

打开 `run_multiple_experiments.py`，注册你的大模型 API：

```python
MODELS_TO_TEST = [
    {
        "name": "GLM_5",
        "model": "GLM-5",
        "provider": "openai_compatible",
        "api_key": "YOUR_KEY",
        "base_url": "YOUR_BASE_URL"
    },
    {
        "name": "Gemini_3_0_Flash",
        "model": "Gemini-3.0-Flash",
        "provider": "openai_compatible",
        "api_key": "YOUR_KEY",
        "base_url": "YOUR_BASE_URL"
    }
]
```

## 3. 发令枪响

在控制台敲下：

```bash
python run_multiple_experiments.py
```

终端将会实时打出诸如 `[1/4] 模型: GLM_5 (Model: GLM-5) ... [OK] 模型 GLM_5 跑完耗时: xxx s` 的进度条。所有模型参赛完毕后，打榜测试就结束了。

## 4. 榜单加冕

为了能够直接给导师和外界展示效果，项目内置了一键解析全量跑分 JSON，并提纯成排行榜功能的扫描器：

```bash
python parse_leaderboard.py
```

它会在最新批次的 `experiment_logs` 的根目录里扫描每一个选手，并在当前目录抛出 `LEADERBOARD.md` 静态文本文档，同时更新用于维系网站实时动态数据的 `data.json`。此时，你可以前往左侧侧边栏查看可视化 **Leaderboard**。
