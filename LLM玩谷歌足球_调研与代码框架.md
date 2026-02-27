# LLM 玩谷歌足球 — 调研与代码框架

> 目标场景：`academy_3_vs_1_with_keeper`（3名进攻球员 vs 1名防守球员 + 门将）

---

## 一、场景详述

### 1.1 场景配置

| 项目 | 值 |
|------|-----|
| 场景名称 | `academy_3_vs_1_with_keeper` |
| 进攻方（左队） | GK(不可控) + 3 名可控进攻球员 |
| 防守方（右队） | GK + 1 名防守球员（AI 控制） |
| 回合时长 | 400 步（约 10 秒游戏时间） |
| 越位规则 | 关闭 (`offsides=False`) |
| 得分结束 | 是 (`end_episode_on_score=True`) |
| 出界结束 | 是 (`end_episode_on_out_of_play=True`) |
| 丢球结束 | 否 (`end_episode_on_possession_change=False`) |
| 确定性 | 否 (`deterministic=False`) |

### 1.2 初始布局

```
球场坐标系: x ∈ [-1, 1], y ∈ [-0.42, 0.42]
左球门: x = -1, y ∈ [-0.044, 0.044]
右球门: x = +1, y ∈ [-0.044, 0.044]

初始状态 (大致):
  球: 约 (0.5, 0.0) 附近, 由进攻方持有
  左队GK:  (-1.0, 0.0)  [不可控]
  进攻球员1: ≈(0.5, 0.0)   持球者
  进攻球员2: ≈(0.6, 0.15)  跑位接应
  进攻球员3: ≈(0.6, -0.15) 跑位接应
  右队GK:  (-1.0→右侧镜像→+1.0 附近)
  防守球员:  ≈(0.7, 0.0)  之间拦截
```

### 1.3 奖励信号

- **稀疏奖励**: 进球 +1，被进球 -1
- **Checkpoint 奖励** (可选): 环境内置 `scoring` 和 `checkpoints` wrapper，球每越过球场的10%线奖励 +0.1，鼓励向前推进

---

## 二、观测空间（Observation Space）

### 2.1 Raw 观测字典

环境 `representation='raw'` 时返回 Python dict，包含以下字段：

#### 球信息
| 字段 | 类型 | 说明 |
|------|------|------|
| `ball` | `[x, y, z]` | 球的三维坐标 |
| `ball_direction` | `[x, y, z]` | 球的运动向量（每步位移） |
| `ball_rotation` | `[x, y, z]` | 球的旋转角度（弧度） |
| `ball_owned_team` | `{-1, 0, 1}` | -1=无人控球, 0=左队, 1=右队 |
| `ball_owned_player` | `{0..N-1}` | 持球球员索引 |

#### 左队信息（进攻方，我方）
| 字段 | 类型 | 说明 |
|------|------|------|
| `left_team` | `N × [x, y]` | 各球员位置 |
| `left_team_direction` | `N × [x, y]` | 各球员运动向量 |
| `left_team_tired_factor` | `N × float` | 疲劳度 0~1 (0=不累) |
| `left_team_yellow_card` | `N × int` | 黄牌数 |
| `left_team_active` | `N × bool` | 是否在场（红牌=False） |
| `left_team_roles` | `N × int` | 角色: 0=GK, 5=CM, 9=CF 等 |

#### 右队信息（防守方，对手）
| 字段 | 说明 |
|------|------|
| `right_team` | 同左队格式 |
| `right_team_direction` | 同左队格式 |
| `right_team_roles` | 同左队格式 |

#### 控制球员信息
| 字段 | 类型 | 说明 |
|------|------|------|
| `active` | `int` | 当前控制的球员索引 |
| `designated` | `int` | 主导球员索引（通常=active） |
| `sticky_actions` | `10 × {0,1}` | 粘性动作开关状态 |

#### 比赛状态
| 字段 | 类型 | 说明 |
|------|------|------|
| `score` | `[left, right]` | 比分 |
| `steps_left` | `int` | 剩余步数 |
| `game_mode` | `int` | 0=Normal, 1=KickOff, 4=Corner... |

### 2.2 坐标系要点

- 球场四角: `(-1, -0.42)` 左上, `(1, -0.42)` 右上, `(-1, 0.42)` 左下, `(1, 0.42)` 右下
- 左球门中心: `(-1, 0)`, 右球门中心: `(1, 0)`
- 球门 Y 范围: `[-0.044, 0.044]`

---

## 三、动作空间（Action Space）

19 个离散动作：

| ID | 动作名 | 类型 | 说明 |
|----|--------|------|------|
| 0 | `action_idle` | 即时 | 什么都不做 |
| 1 | `action_left` | 粘性 | 向左跑 |
| 2 | `action_top_left` | 粘性 | 向左上跑 |
| 3 | `action_top` | 粘性 | 向上跑 |
| 4 | `action_top_right` | 粘性 | 向右上跑 |
| 5 | `action_right` | 粘性 | 向右跑 |
| 6 | `action_bottom_right` | 粘性 | 向右下跑 |
| 7 | `action_bottom` | 粘性 | 向下跑 |
| 8 | `action_bottom_left` | 粘性 | 向左下跑 |
| 9 | `action_long_pass` | 即时 | 长传（方向自动取决于移动方向） |
| 10 | `action_high_pass` | 即时 | 高球传球（不易被截） |
| 11 | `action_short_pass` | 即时 | 短传 |
| 12 | `action_shot` | 即时 | 射门（总是朝向对方球门） |
| 13 | `action_sprint` | 粘性 | 加速跑 |
| 14 | `action_release_direction` | 即时 | 释放移动方向 |
| 15 | `action_release_sprint` | 即时 | 停止加速 |
| 16 | `action_sliding` | 即时 | 铲球（防守用） |
| 17 | `action_dribble` | 粘性 | 开始盘带 |
| 18 | `action_release_dribble` | 即时 | 停止盘带 |

> **粘性动作**: 执行后持续生效，直到被显式释放或被其他粘性动作覆盖

> **进攻场景常用子集**: `idle(0)`, 方向(1-8), `short_pass(11)`, `long_pass(9)`, `high_pass(10)`, `shot(12)`, `sprint(13)`, `dribble(17)`

---

## 四、LLM 玩游戏的核心架构

### 4.1 核心思路：Observation-to-Text → LLM Reasoning → Text-to-Action

借鉴 TextStarCraft II 等 LLM 玩游戏的方法论，核心流程为：

```
┌──────────────┐    ┌───────────────────┐    ┌──────────────┐    ┌────────────┐
│ GRF Environment │──▶│ Obs-to-Text Adapter │──▶│  LLM (GPT-4等) │──▶│ Text-to-Action │──▶ env.step()
│  (raw obs dict) │    │ (结构化→自然语言)    │    │ (推理+决策)      │    │ (解析→action_id) │
└──────────────┘    └───────────────────┘    └──────────────┘    └────────────┘
        ▲                                                                │
        └────────────────────────────────────────────────────────────────┘
```

### 4.2 关键设计模块

#### (A) Observation-to-Text Adapter (观测 → 文本)

将 raw 观测字典转化为 LLM 可读的自然语言场景描述：

```python
def obs_to_text(obs: dict) -> str:
    """将 GRF raw observation 转为自然语言文本"""
    ball_pos = obs['ball']
    ball_owned = obs['ball_owned_team']
    active = obs['active']
    left_team = obs['left_team']        # 我方球员位置
    right_team = obs['right_team']      # 对方球员位置
    steps_left = obs['steps_left']

    # 判断持球状态
    if ball_owned == 0:
        owner = f"我方球员{obs['ball_owned_player']}持球"
    elif ball_owned == 1:
        owner = "对方持球"
    else:
        owner = "球处于自由状态"

    text = f"""
【当前局面】（剩余 {steps_left} 步）
- 球位置: ({ball_pos[0]:.2f}, {ball_pos[1]:.2f}), {owner}
- 当前控制球员: {active}号

【我方球员位置】(左队, 进攻方)
"""
    for i, pos in enumerate(left_team):
        role = "GK" if i == 0 else f"进攻{i}"
        controllable = "← 当前控制" if i == active else ""
        text += f"  {role}: ({pos[0]:.2f}, {pos[1]:.2f}) {controllable}\n"

    text += "\n【对方球员位置】(右队, 防守方)\n"
    for i, pos in enumerate(right_team):
        role = "GK" if i == 0 else f"防守{i}"
        text += f"  {role}: ({pos[0]:.2f}, {pos[1]:.2f})\n"

    text += f"""
【球门位置】
- 对方球门: x=1.0, y ∈ [-0.044, 0.044]
- 我方球门: x=-1.0

【可选动作】
0=不动, 1=左, 2=左上, 3=上, 4=右上, 5=右, 6=右下, 7=下, 8=左下
9=长传, 10=高球, 11=短传, 12=射门, 13=加速, 17=盘带
"""
    return text
```

#### (B) LLM Reasoning (大模型推理)

给LLM一个 System Prompt + 场景描述，让它输出动作决策：

```python
SYSTEM_PROMPT = """你是一个专业足球战术 AI，控制进攻方球队在 3v1+GK 的场景中进球。

规则:
1. 你控制3名进攻球员(环境每步自动切换到关键球员)
2. 目标是突破1名防守球员和门将，完成射门得分
3. 你需要利用传球配合、跑位拉开空间

坐标系:
- 球场 x ∈ [-1, 1], y ∈ [-0.42, 0.42]
- 对方球门在 x=1.0, 球门口 y ∈ [-0.044, 0.044]
- x 越大越接近对方球门

战术指导:
- 当持球球员前方有防守者时，考虑传球给空位队友
- 当接近球门且无人阻挡时，果断射门(动作12)
- 利用短传(11)做快速配合，长传(9)/高球(10)做转移
- 接近球门 x > 0.8 且角度合适时应果断射门

你必须只输出一个 JSON:
{"action": <动作ID>, "reason": "<简要理由>"}
"""
```

#### (C) Text-to-Action Parser (文本 → 动作)

```python
import json
import re

def parse_llm_response(response: str) -> int:
    """从 LLM 响应中提取动作 ID"""
    try:
        # 尝试直接 JSON 解析
        match = re.search(r'\{[^}]+\}', response)
        if match:
            data = json.loads(match.group())
            action = int(data.get('action', 0))
            if 0 <= action <= 18:
                return action
    except (json.JSONDecodeError, ValueError):
        pass
    return 0  # 默认 idle
```

### 4.3 多智能体控制方案

GRF `academy_3_vs_1_with_keeper` 场景有两种控制模式：

| 模式 | 设置 | 说明 |
|------|------|------|
| **单智能体** | `number_of_left_players_agent_controls=1` | 只控制持球/最近球员，环境自动切换 |
| **多智能体** | `number_of_left_players_agent_controls=3` | 同时控制3名球员，每步返回3个obs |

> **推荐先用单智能体模式**：降低 LLM 调用次数和复杂度，环境会自动切换活跃球员

---

## 五、视频录制与日志

### 5.1 环境参数

```python
env = gfootball.env.create_environment(
    env_name='academy_3_vs_1_with_keeper',
    representation='raw',
    rewards='scoring,checkpoints',
    write_video=True,              # 录制视频
    write_full_episode_dumps=True, # 保存完整 episode dump
    write_goal_dumps=True,         # 保存进球片段
    render=False,                  # 服务器端可设 False，仍产生简化动画
    logdir='./grf_logs',           # 日志和视频输出目录
    number_of_left_players_agent_controls=1,
)
```

### 5.2 输出文件

```
./grf_logs/
  ├── score_xxxx.avi          # 全回合动画视频
  ├── episode_done_xxxx.dump  # 完整 episode 二进制回放
  └── ...
```

---

## 六、完整代码框架

### 6.1 项目结构

```
谷歌足球/
├── llm_football_agent/
│   ├── __init__.py
│   ├── env_wrapper.py       # 环境封装 + 视频录制
│   ├── obs_to_text.py       # 观测 → 文本转换
│   ├── llm_client.py        # LLM API 调用封装
│   ├── action_parser.py     # 文本 → 动作解析
│   ├── logger.py            # 结构化日志记录
│   └── run_game.py          # 主运行脚本
├── configs/
│   └── config.yaml          # 配置文件
├── logs/                    # 日志输出
├── videos/                  # 视频输出
├── requirements.txt
└── README.md
```

### 6.2 核心代码

以下是完整的可运行代码框架：

#### `requirements.txt`

```
gfootball
openai
pyyaml
```

#### `configs/config.yaml`

```yaml
# LLM 配置
llm:
  model: "gpt-4o"                     # 或本地模型
  api_key: "YOUR_API_KEY"
  base_url: "https://api.openai.com/v1"  # 可替换为本地/代理地址
  temperature: 0.3
  max_tokens: 256

# 环境配置
env:
  scenario: "academy_3_vs_1_with_keeper"
  representation: "raw"
  rewards: "scoring,checkpoints"
  render: false
  write_video: true
  write_full_episode_dumps: true
  logdir: "./grf_logs"
  num_controlled_players: 1           # 1=单智能体, 3=多智能体

# 实验配置
experiment:
  num_episodes: 10                    # 运行回合数
  max_steps_per_episode: 400
  log_dir: "./logs"
  video_dir: "./videos"
```

#### `llm_football_agent/obs_to_text.py`

```python
"""Observation-to-Text Adapter: 将 GRF raw 观测转为 LLM 可读文本"""

import numpy as np


# 球员角色映射
ROLE_NAMES = {
    0: "门将(GK)", 1: "中后卫(CB)", 2: "左后卫(LB)", 3: "右后卫(RB)",
    4: "防守中场(DM)", 5: "中场(CM)", 6: "左中场(LM)", 7: "右中场(RM)",
    8: "前腰(AM)", 9: "前锋(CF)",
}

GAME_MODE_NAMES = {
    0: "正常比赛", 1: "开球", 2: "球门球", 3: "任意球",
    4: "角球", 5: "界外球", 6: "点球",
}

ACTION_NAMES = {
    0: "不动(idle)", 1: "跑-左", 2: "跑-左上", 3: "跑-上",
    4: "跑-右上", 5: "跑-右", 6: "跑-右下", 7: "跑-下",
    8: "跑-左下", 9: "长传", 10: "高球传球", 11: "短传",
    12: "射门", 13: "加速", 14: "释放方向", 15: "停止加速",
    16: "铲球", 17: "盘带", 18: "停止盘带",
}


def distance(pos1, pos2):
    """计算两点距离"""
    return np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)


def obs_to_text(obs: dict, include_tactical_hints: bool = True) -> str:
    """
    将 GRF raw observation 转为详细的自然语言场景描述。
    
    Args:
        obs: GRF 环境返回的 raw observation 字典
        include_tactical_hints: 是否附加战术提示
    
    Returns:
        描述当前局面的自然语言文本
    """
    ball = obs['ball']
    ball_dir = obs['ball_direction']
    ball_owned_team = obs['ball_owned_team']
    ball_owned_player = obs['ball_owned_player']
    active = obs['active']
    
    left_team = obs['left_team']
    left_dir = obs['left_team_direction']
    left_roles = obs.get('left_team_roles', [])
    
    right_team = obs['right_team']
    right_dir = obs['right_team_direction']
    
    steps_left = obs['steps_left']
    score = obs['score']
    game_mode = obs['game_mode']
    sticky = obs.get('sticky_actions', [0]*10)
    
    # === 构建文本描述 ===
    lines = []
    lines.append(f"=== 当前局面 ===")
    lines.append(f"比分: 我方 {score[0]} - {score[1]} 对方 | 剩余步数: {steps_left}")
    lines.append(f"比赛状态: {GAME_MODE_NAMES.get(game_mode, '未知')}")
    
    # 球信息
    if ball_owned_team == 0:
        owner_str = f"我方{ball_owned_player}号球员持球"
    elif ball_owned_team == 1:
        owner_str = "对方持球"
    else:
        owner_str = "球处于自由状态"
    
    lines.append(f"\n[球] 位置=({ball[0]:.3f}, {ball[1]:.3f}, {ball[2]:.3f}), "
                 f"运动方向=({ball_dir[0]:.3f}, {ball_dir[1]:.3f}), {owner_str}")
    
    # 当前控制球员
    lines.append(f"\n[当前控制] {active}号球员")
    
    # 粘性动作状态
    sticky_names = ['左', '左上', '上', '右上', '右', '右下', '下', '左下', '冲刺', '盘带']
    active_sticky = [sticky_names[i] for i in range(len(sticky)) if sticky[i]]
    if active_sticky:
        lines.append(f"[激活中的持续动作] {', '.join(active_sticky)}")
    
    # 我方球员
    lines.append(f"\n[我方球员] (进攻方, 左队)")
    goal_pos = [1.0, 0.0]  # 对方球门
    for i, pos in enumerate(left_team):
        role = ROLE_NAMES.get(left_roles[i], "未知") if i < len(left_roles) else "未知"
        dist_to_goal = distance(pos, goal_pos)
        ctrl = " ★当前控制" if i == active else ""
        has_ball = " 【持球】" if (ball_owned_team == 0 and ball_owned_player == i) else ""
        dir_info = f"移动({left_dir[i][0]:.3f}, {left_dir[i][1]:.3f})" if i < len(left_dir) else ""
        lines.append(f"  {i}号 {role}: 位置({pos[0]:.3f}, {pos[1]:.3f}) "
                     f"{dir_info} 距球门{dist_to_goal:.2f}{ctrl}{has_ball}")
    
    # 对方球员
    lines.append(f"\n[对方球员] (防守方, 右队)")
    for i, pos in enumerate(right_team):
        role = "门将" if i == 0 else f"防守{i}"
        lines.append(f"  {i}号 {role}: 位置({pos[0]:.3f}, {pos[1]:.3f})")
    
    # 可用动作
    lines.append(f"\n[可选动作]")
    useful_actions = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 17]
    for aid in useful_actions:
        lines.append(f"  {aid} = {ACTION_NAMES[aid]}")
    
    # 战术提示
    if include_tactical_hints:
        lines.append(f"\n[战术参考]")
        # 持球球员距离球门的距离
        if ball_owned_team == 0 and ball_owned_player < len(left_team):
            bp = left_team[ball_owned_player]
            d = distance(bp, goal_pos)
            if d < 0.3:
                lines.append("  → 非常接近球门，优先考虑射门(12)！")
            elif d < 0.5:
                lines.append("  → 在射程范围内，可考虑射门(12)或做最后一传")
            
            # 检查防守者是否在传球路线上
            for j, rp in enumerate(right_team):
                if j == 0:  # 跳过门将
                    continue
                if distance(bp, rp) < 0.15:
                    lines.append(f"  → 防守者{j}号距离很近({distance(bp, rp):.2f})，考虑传球避开！")
    
    return '\n'.join(lines)


def obs_to_text_compact(obs: dict) -> str:
    """紧凑版观测描述（节省 token）"""
    ball = obs['ball']
    active = obs['active']
    owned = obs['ball_owned_team']
    left = obs['left_team']
    right = obs['right_team']
    steps = obs['steps_left']
    
    owner = f"我方{obs['ball_owned_player']}号" if owned == 0 else ("对方" if owned == 1 else "无")
    
    text = f"步数剩{steps}|球({ball[0]:.2f},{ball[1]:.2f})持球:{owner}|控制:{active}号\n"
    text += "我方:" + " ".join([f"{i}({p[0]:.2f},{p[1]:.2f})" for i, p in enumerate(left)]) + "\n"
    text += "对方:" + " ".join([f"{i}({p[0]:.2f},{p[1]:.2f})" for i, p in enumerate(right)]) + "\n"
    text += "动作:0不动|1-8方向|9长传|10高球|11短传|12射门|13加速|17盘带"
    
    return text
```

#### `llm_football_agent/llm_client.py`

```python
"""LLM API 调用封装"""

import json
import time
from openai import OpenAI


SYSTEM_PROMPT = """你是一个专业足球战术 AI。你正在控制进攻方（左队）在 academy_3_vs_1_with_keeper 场景中尝试进球。

【场景】3 名进攻球员 vs 1 名防守球员 + 1 名门将。你需要通过传球配合突破防守，完成射门得分。

【坐标系】
- 球场: x ∈ [-1, 1], y ∈ [-0.42, 0.42]
- 对方球门: x = 1.0, 球门口 y ∈ [-0.044, 0.044]
- x 越大 → 越接近对方球门
- y 正值 → 球场下方, y 负值 → 球场上方

【核心战术原则】
1. 当持球者前方有防守者挡住时 → 传球(11短传/9长传/10高球)给空位队友
2. 当接近球门(x > 0.85)且射角合适 → 果断射门(12)
3. 传球方向由当前移动方向决定 → 先设置方向(1-8)，再执行传球
4. 利用3打1的人数优势 → 拉开空间，做三角传球配合
5. 不要长时间盘带 → 快速传切更有效

【输出格式】（严格遵守）
只输出一个 JSON 对象:
{"action": <0-18的整数>, "reason": "<20字以内的理由>"}
"""


class LLMClient:
    def __init__(self, model: str, api_key: str, base_url: str = None,
                 temperature: float = 0.3, max_tokens: int = 256):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.total_tokens = 0
        self.call_count = 0
    
    def decide(self, obs_text: str, history: list = None) -> dict:
        """
        向 LLM 发送观测文本，获取动作决策。
        
        Args:
            obs_text: 观测的文本描述
            history: 可选，最近几步的历史记录 [{"obs": ..., "action": ..., "reason": ...}]
        
        Returns:
            {"action": int, "reason": str, "raw_response": str}
        """
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # 加入少量近期历史
        if history:
            recent = history[-3:]  # 最近3步
            hist_text = "\n".join([
                f"第{h['step']}步: 动作={h['action']}({h.get('reason', '')}) → 结果观察到场景变化"
                for h in recent
            ])
            messages.append({"role": "user", "content": f"【近期决策历史】\n{hist_text}"})
            messages.append({"role": "assistant", "content": "好的，我会参考历史做出更好的决策。"})
        
        messages.append({"role": "user", "content": obs_text})
        
        start = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            raw = response.choices[0].message.content.strip()
            elapsed = time.time() - start
            
            # 统计 token
            usage = response.usage
            if usage:
                self.total_tokens += usage.total_tokens
            self.call_count += 1
            
            return {
                "raw_response": raw,
                "elapsed": elapsed,
                "tokens": usage.total_tokens if usage else 0,
            }
        except Exception as e:
            return {
                "raw_response": "",
                "elapsed": time.time() - start,
                "tokens": 0,
                "error": str(e),
            }
    
    def get_stats(self) -> dict:
        return {
            "total_calls": self.call_count,
            "total_tokens": self.total_tokens,
            "avg_tokens_per_call": self.total_tokens / max(1, self.call_count),
        }
```

#### `llm_football_agent/action_parser.py`

```python
"""Text-to-Action Parser: 解析 LLM 输出为动作 ID"""

import json
import re


ACTION_MAP = {
    "idle": 0, "不动": 0, "空闲": 0,
    "left": 1, "左": 1,
    "top_left": 2, "左上": 2,
    "top": 3, "上": 3,
    "top_right": 4, "右上": 4,
    "right": 5, "右": 5,
    "bottom_right": 6, "右下": 6,
    "bottom": 7, "下": 7,
    "bottom_left": 8, "左下": 8,
    "long_pass": 9, "长传": 9,
    "high_pass": 10, "高球": 10, "高球传球": 10,
    "short_pass": 11, "短传": 11,
    "shot": 12, "射门": 12,
    "sprint": 13, "加速": 13, "冲刺": 13,
    "release_direction": 14, "释放方向": 14,
    "release_sprint": 15, "停止加速": 15,
    "sliding": 16, "铲球": 16,
    "dribble": 17, "盘带": 17,
    "release_dribble": 18, "停止盘带": 18,
}


def parse_action(response: str) -> dict:
    """
    从 LLM 响应中提取动作和理由。
    
    支持格式:
    1. {"action": 12, "reason": "接近球门射门"}
    2. 纯数字 "12"
    3. 动作名 "shot" 或 "射门"
    
    Returns:
        {"action": int, "reason": str, "parse_success": bool}
    """
    # 方法1: 尝试 JSON 解析
    try:
        json_match = re.search(r'\{[^}]+\}', response)
        if json_match:
            data = json.loads(json_match.group())
            action = int(data.get('action', data.get('动作', 0)))
            reason = str(data.get('reason', data.get('理由', '')))
            if 0 <= action <= 18:
                return {"action": action, "reason": reason, "parse_success": True}
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    
    # 方法2: 尝试提取纯数字
    num_match = re.search(r'\b(\d{1,2})\b', response)
    if num_match:
        action = int(num_match.group(1))
        if 0 <= action <= 18:
            return {"action": action, "reason": response[:50], "parse_success": True}
    
    # 方法3: 尝试匹配动作名
    response_lower = response.lower().strip()
    for name, action_id in ACTION_MAP.items():
        if name in response_lower:
            return {"action": action_id, "reason": response[:50], "parse_success": True}
    
    # 默认: idle
    return {"action": 0, "reason": f"解析失败，默认idle: {response[:50]}", "parse_success": False}
```

#### `llm_football_agent/logger.py`

```python
"""结构化日志记录器"""

import json
import os
import csv
from datetime import datetime


class GameLogger:
    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(log_dir, f"session_{timestamp}")
        os.makedirs(self.session_dir, exist_ok=True)
        
        # 初始化 CSV 日志
        self.csv_path = os.path.join(self.session_dir, "step_log.csv")
        self.csv_file = open(self.csv_path, 'w', newline='', encoding='utf-8')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow([
            'episode', 'step', 'ball_x', 'ball_y', 'active_player',
            'ball_owner', 'action_id', 'action_name', 'reason',
            'parse_success', 'llm_time_ms', 'tokens', 'reward',
            'cumulative_reward', 'score_left', 'score_right',
        ])
        
        # Episode 摘要
        self.episode_summaries = []
        
        # 详细 JSON 日志
        self.episode_details = []
    
    def log_step(self, episode: int, step: int, obs: dict,
                 action_id: int, action_name: str, reason: str,
                 parse_success: bool, llm_time: float, tokens: int,
                 reward: float, cumulative_reward: float):
        """记录每一步"""
        ball = obs['ball']
        self.csv_writer.writerow([
            episode, step, f"{ball[0]:.4f}", f"{ball[1]:.4f}",
            obs['active'], obs['ball_owned_team'],
            action_id, action_name, reason[:80],
            parse_success, f"{llm_time*1000:.0f}", tokens,
            reward, f"{cumulative_reward:.3f}",
            obs['score'][0], obs['score'][1],
        ])
        self.csv_file.flush()  # 即时写入
        
        # 详细日志
        self.episode_details.append({
            "step": step,
            "ball_pos": [round(ball[0], 4), round(ball[1], 4)],
            "active_player": obs['active'],
            "action": action_id,
            "action_name": action_name,
            "reason": reason,
            "reward": reward,
        })
    
    def log_episode_end(self, episode: int, total_steps: int,
                        total_reward: float, scored: bool,
                        llm_stats: dict):
        """记录回合结束"""
        summary = {
            "episode": episode,
            "total_steps": total_steps,
            "total_reward": round(total_reward, 4),
            "scored": scored,
            "llm_calls": llm_stats.get("total_calls", 0),
            "total_tokens": llm_stats.get("total_tokens", 0),
            "timestamp": datetime.now().isoformat(),
        }
        self.episode_summaries.append(summary)
        
        # 保存 episode 详情
        detail_path = os.path.join(self.session_dir, f"episode_{episode:03d}.json")
        with open(detail_path, 'w', encoding='utf-8') as f:
            json.dump({
                "summary": summary,
                "steps": self.episode_details,
            }, f, ensure_ascii=False, indent=2)
        
        self.episode_details = []  # 重置
        
        print(f"[Episode {episode}] steps={total_steps}, "
              f"reward={total_reward:.3f}, scored={scored}, "
              f"tokens={llm_stats.get('total_tokens', 0)}")
    
    def save_final_report(self):
        """保存最终报告"""
        report_path = os.path.join(self.session_dir, "final_report.json")
        
        scored_count = sum(1 for s in self.episode_summaries if s['scored'])
        total = len(self.episode_summaries)
        
        report = {
            "total_episodes": total,
            "scored_episodes": scored_count,
            "score_rate": scored_count / max(1, total),
            "avg_reward": sum(s['total_reward'] for s in self.episode_summaries) / max(1, total),
            "avg_steps": sum(s['total_steps'] for s in self.episode_summaries) / max(1, total),
            "total_tokens": sum(s['total_tokens'] for s in self.episode_summaries),
            "episodes": self.episode_summaries,
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*50}")
        print(f"实验完成! 进球率: {scored_count}/{total} = {report['score_rate']*100:.1f}%")
        print(f"平均奖励: {report['avg_reward']:.3f}")
        print(f"总 Token 消耗: {report['total_tokens']}")
        print(f"结果保存至: {self.session_dir}")
        print(f"{'='*50}")
        
        return report
    
    def close(self):
        self.csv_file.close()
```

#### `llm_football_agent/run_game.py` — 主运行脚本

```python
"""主运行脚本: LLM 玩 academy_3_vs_1_with_keeper"""

import os
import sys
import yaml
import time
import argparse
import gfootball.env as football_env

from obs_to_text import obs_to_text, obs_to_text_compact
from llm_client import LLMClient
from action_parser import parse_action, ACTION_MAP
from logger import GameLogger


# 动作 ID → 名称
ACTION_NAMES = {
    0: "idle", 1: "left", 2: "top_left", 3: "top", 4: "top_right",
    5: "right", 6: "bottom_right", 7: "bottom", 8: "bottom_left",
    9: "long_pass", 10: "high_pass", 11: "short_pass", 12: "shot",
    13: "sprint", 14: "release_dir", 15: "release_sprint",
    16: "sliding", 17: "dribble", 18: "release_dribble",
}


def load_config(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def create_env(cfg: dict):
    """创建 GRF 环境"""
    env_cfg = cfg['env']
    env = football_env.create_environment(
        env_name=env_cfg['scenario'],
        representation=env_cfg.get('representation', 'raw'),
        rewards=env_cfg.get('rewards', 'scoring,checkpoints'),
        write_video=env_cfg.get('write_video', True),
        write_full_episode_dumps=env_cfg.get('write_full_episode_dumps', True),
        write_goal_dumps=True,
        render=env_cfg.get('render', False),
        logdir=env_cfg.get('logdir', './grf_logs'),
        number_of_left_players_agent_controls=env_cfg.get('num_controlled_players', 1),
    )
    return env


def run_episode(env, llm: LLMClient, logger: GameLogger,
                episode_id: int, max_steps: int,
                call_interval: int = 5,
                verbose: bool = True,
                compact_obs: bool = False):
    """
    运行一个 episode。
    
    Args:
        call_interval: 每隔多少步调用一次 LLM（中间步重复上次动作）
                       设为1则每步都调用（更精确但 token 消耗大）
        compact_obs: 是否使用紧凑版观测文本（节省 token）
    """
    obs = env.reset()
    
    # 处理多智能体返回
    if isinstance(obs, list):
        obs = obs[0]
    
    done = False
    total_reward = 0.0
    step = 0
    history = []
    current_action = 0  # 默认 idle
    current_reason = "初始"
    
    while not done and step < max_steps:
        # 是否调用 LLM
        should_call_llm = (step % call_interval == 0) or step == 0
        
        if should_call_llm:
            # 生成观测文本
            if compact_obs:
                obs_text = obs_to_text_compact(obs)
            else:
                obs_text = obs_to_text(obs, include_tactical_hints=True)
            
            # LLM 推理
            llm_result = llm.decide(obs_text, history=history[-5:])
            
            if 'error' in llm_result:
                print(f"  [LLM Error] {llm_result['error']}")
                current_action = 0
                current_reason = "LLM 调用失败"
                parse_ok = False
            else:
                # 解析动作
                parsed = parse_action(llm_result['raw_response'])
                current_action = parsed['action']
                current_reason = parsed['reason']
                parse_ok = parsed['parse_success']
                
                if verbose and step % call_interval == 0:
                    print(f"  Step {step}: LLM → action={current_action}"
                          f"({ACTION_NAMES.get(current_action, '?')}) "
                          f"| {current_reason[:40]} "
                          f"| {llm_result['elapsed']*1000:.0f}ms")
        else:
            parse_ok = True  # 复用上次决策
            llm_result = {"elapsed": 0, "tokens": 0}
        
        # 执行动作
        next_obs, reward, done, info = env.step(current_action)
        
        if isinstance(next_obs, list):
            next_obs = next_obs[0]
        if isinstance(reward, list):
            reward = reward[0]
        if isinstance(done, list):
            done = done[0]
        
        total_reward += reward
        
        # 记录日志
        logger.log_step(
            episode=episode_id, step=step, obs=obs,
            action_id=current_action,
            action_name=ACTION_NAMES.get(current_action, '?'),
            reason=current_reason,
            parse_success=parse_ok,
            llm_time=llm_result.get('elapsed', 0),
            tokens=llm_result.get('tokens', 0),
            reward=reward,
            cumulative_reward=total_reward,
        )
        
        # 更新历史
        if should_call_llm:
            history.append({
                "step": step,
                "action": current_action,
                "reason": current_reason,
            })
        
        obs = next_obs
        step += 1
    
    # 判断是否进球
    scored = obs['score'][0] > 0
    
    logger.log_episode_end(
        episode=episode_id,
        total_steps=step,
        total_reward=total_reward,
        scored=scored,
        llm_stats=llm.get_stats(),
    )
    
    return scored, total_reward, step


def main():
    parser = argparse.ArgumentParser(description='LLM plays GRF academy_3_vs_1_with_keeper')
    parser.add_argument('--config', type=str, default='configs/config.yaml', help='配置文件路径')
    parser.add_argument('--episodes', type=int, default=None, help='覆盖运行回合数')
    parser.add_argument('--interval', type=int, default=5, help='LLM调用间隔(步)')
    parser.add_argument('--compact', action='store_true', help='使用紧凑版观测文本')
    parser.add_argument('--verbose', action='store_true', default=True, help='详细输出')
    args = parser.parse_args()
    
    # 加载配置
    cfg = load_config(args.config)
    num_episodes = args.episodes or cfg['experiment']['num_episodes']
    
    print(f"{'='*50}")
    print(f"LLM Football Agent — academy_3_vs_1_with_keeper")
    print(f"Model: {cfg['llm']['model']}")
    print(f"Episodes: {num_episodes}")
    print(f"LLM call interval: 每{args.interval}步")
    print(f"{'='*50}\n")
    
    # 初始化组件
    env = create_env(cfg)
    llm = LLMClient(
        model=cfg['llm']['model'],
        api_key=cfg['llm']['api_key'],
        base_url=cfg['llm'].get('base_url'),
        temperature=cfg['llm'].get('temperature', 0.3),
        max_tokens=cfg['llm'].get('max_tokens', 256),
    )
    logger = GameLogger(cfg['experiment']['log_dir'])
    
    # 运行实验
    results = []
    for ep in range(num_episodes):
        print(f"\n--- Episode {ep+1}/{num_episodes} ---")
        scored, reward, steps = run_episode(
            env, llm, logger,
            episode_id=ep,
            max_steps=cfg['experiment'].get('max_steps_per_episode', 400),
            call_interval=args.interval,
            verbose=args.verbose,
            compact_obs=args.compact,
        )
        results.append({"scored": scored, "reward": reward, "steps": steps})
    
    # 最终报告
    report = logger.save_final_report()
    logger.close()
    env.close()
    
    return report


if __name__ == '__main__':
    main()
```

---

## 七、快速上手指南

### 7.1 环境安装

```bash
# Linux/macOS (推荐)
sudo apt-get install -y git cmake build-essential libgl1-mesa-dev \
    libsdl2-dev libsdl2-image-dev libsdl2-ttf-dev libsdl2-gfx-dev \
    libboost-all-dev libdirectfb-dev libst-dev

# 创建虚拟环境
python -m venv grf_env
source grf_env/bin/activate  # Linux/macOS
# grf_env\Scripts\activate   # Windows

# 安装 gfootball
pip install gfootball
pip install openai pyyaml

# 验证安装
python -c "import gfootball; print('GRF installed successfully')"
```

### 7.2 运行实验

```bash
# 基础运行 (每5步调用一次LLM)
python llm_football_agent/run_game.py --config configs/config.yaml

# 高精度模式 (每步调用LLM，token消耗大)
python llm_football_agent/run_game.py --interval 1

# 省token模式 (紧凑观测 + 10步间隔)
python llm_football_agent/run_game.py --interval 10 --compact

# 指定回合数
python llm_football_agent/run_game.py --episodes 5
```

### 7.3 输出结构

```
logs/
└── session_20260225_170000/
    ├── step_log.csv             # 每步详细 CSV 日志
    ├── episode_000.json         # 每回合 JSON 详情
    ├── episode_001.json
    ├── ...
    └── final_report.json        # 最终汇总报告

grf_logs/
├── score_xxxx.avi               # 视频录制
└── episode_done_xxxx.dump       # Episode 回放文件
```

---

## 八、关键设计考量

### 8.1 LLM 调用频率 vs 精度权衡

| 策略 | `call_interval` | Token/Episode | 精度 |
|------|:---:|:---:|:---:|
| 每步调用 | 1 | ~100K | 最高，但延迟大 |
| 每5步调用 | 5 | ~20K | 推荐平衡点 |
| 每10步调用 | 10 | ~10K | 省token，适合初步测试 |
| 关键事件触发 | 动态 | ~5K | 最优，但需额外逻辑 |

### 8.2 优化方向

1. **事件驱动调用**: 仅在持球变化、接近球门、防守者逼近时调用 LLM
2. **Few-shot 示例**: 在 prompt 中加入2-3个成功进球的决策范例
3. **思维链 (CoT)**: 要求 LLM 输出 "分析→方案→动作" 的推理链
4. **多智能体协作**: 3个球员分别有独立 LLM 决策（token消耗×3）
5. **混合方案**: LLM 输出高层战术（传/射/带），规则引擎处理方向选择
6. **历史记忆**: 维护最近 N 步决策历史，帮助 LLM 理解局势演变

### 8.3 评估指标

| 指标 | 说明 |
|------|------|
| **进球率** | `scored_episodes / total_episodes` |
| **平均奖励** | 含 checkpoint 奖励的均值 |
| **平均步数** | 进球所需平均步数（越少越好） |
| **Token 消耗** | 总 token 数和成本 |
| **解析成功率** | LLM 输出被成功解析的比例 |
| **决策多样性** | 动作分布的熵值 |

---

## 九、参考论文与项目

1. **Google Research Football** — Kurach et al., AAAI 2019 ([论文](https://arxiv.org/abs/1907.11180), [代码](https://github.com/google-research/football))
2. **Large Language Models Play StarCraft II** — 展示了 Obs-to-Text / Text-to-Action 适配器的设计范式 ([arxiv](https://arxiv.org/abs/2312.11865))
3. **A Survey on LLM-Based Game Agents** — 分类梳理了 LLM 在游戏中的感知、记忆、思考、行动模块 ([arxiv](https://arxiv.org/abs/2404.02039))
4. **Voyager** — LLM驱动的 Minecraft agent，展示了代码生成式动作、技能库等高级范式
5. **ReAct / Reflexion** — LLM Agent 的推理-行动框架，可用于增强足球场景的决策质量
