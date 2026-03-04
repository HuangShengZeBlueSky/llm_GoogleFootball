# 实验配置指南

所有主要的跑马超参数与引擎属性设置都受 `configs/config.yaml` 文件的核心统御。即使你在批处理代码中使用覆盖，它依然是你必须理解的基础字典。

## `config.yaml` 速查表

### 🤖 LLM (大模型行为基座)
| 参数名 | 说明 | 默认值 / 建议 |
| :--- | :--- | :--- |
| `model` | 核心参战大模型名称 (如 qwen-max, gpt-4o) | `gpt-4o` |
| `provider` | API 调用提供商配适器 | `openai_compatible` |
| `temperature` | 控制发散度与想象力。越高盘带越野 | `0.1` (求稳进球) |
| `max_tokens` | 一次回复允许吞吐的最大字数 | `800` |
| `max_retries` | 遇到 429 限频等报错允许死磕重试的次数 | `5` |

### 🎮 Env (足球物理场参数)
| 参数名 | 说明 | 默认值 / 建议 |
| :--- | :--- | :--- |
| `scenario_name` | 地图关卡名 | `academy_3_vs_1_with_keeper` |
| `render` | 是否要在本地机器拉起 GUI 动画弹窗 (Linux 服务器强建议否) | `false` |
| `write_video` | 是否把每一局存成高标清战局录像给赛后复盘 | `true` |
| `write_full_episode_dumps` | 是否留存 .dump 回放文件 | `true` |

### 🔬 Experiment (排位赛制)
| 参数名 | 说明 | 默认值 / 建议 |
| :--- | :--- | :--- |
| `num_episodes` | 一次启动测试打几局排位 | `5` |
| `max_steps_per_episode` | 引擎强行拔插头（单局超时平局）上限物理步数 | `400` |
| `interval_steps` | 大模型跳帧频度，每隔多少步唤醒 LLM 大脑发号施令 | `5` |

## 环境变量的覆盖法则

你可以完全不用进 YAML 里面修改密钥！在 `run_game.py` 的执行层，系统采用**洋葱式的重载合并模型**：

1. **底层兜底**: 先全部吞下 `config.yaml` 里面的设置属性。
2. **中间层篡改**: 引擎会嗅探你工作区的 `.env`，如果你写了 `LLM_MODEL=xxx`，它会强行覆盖底层。
3. **顶层一票否决**: 如果你通过 Bash Shell `--episodes 10` 命令直接打在入口处，CLI 拥有最高解释权和覆写权。
