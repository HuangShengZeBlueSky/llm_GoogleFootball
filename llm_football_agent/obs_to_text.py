"""
Observation-to-Text Adapter
将 GRF raw observation 转为 LLM 可读的自然语言场景描述。

两种模式：
  - obs_to_text():         详细描述（约 400-600 字），含战术提示
  - obs_to_text_compact(): 紧凑描述（约 100 字），省 token
"""

import numpy as np


# ── 映射表 ──────────────────────────────────────────────

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


# ── 工具函数 ────────────────────────────────────────────

def _dist(a, b):
    return float(np.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2))


# ── 详细版 ──────────────────────────────────────────────

def obs_to_text(obs: dict, include_tactical_hints: bool = True) -> str:
    """
    将 GRF raw observation 转为详细的自然语言场景描述。

    Args:
        obs:  GRF 环境返回的 raw observation 字典
        include_tactical_hints: 是否附加简短战术提示

    Returns:
        描述当前局面的自然语言文本
    """
    ball       = obs["ball"]
    ball_dir   = obs["ball_direction"]
    owned_team = obs["ball_owned_team"]
    owned_plr  = obs["ball_owned_player"]
    active     = obs["active"]

    left_pos   = obs["left_team"]
    left_dir   = obs["left_team_direction"]
    left_roles = obs.get("left_team_roles", [])

    right_pos  = obs["right_team"]
    right_dir  = obs["right_team_direction"]

    steps_left = obs["steps_left"]
    score      = obs["score"]
    game_mode  = obs["game_mode"]
    sticky     = obs.get("sticky_actions", [0] * 10)

    goal_pos = (1.0, 0.0)  # 对方球门中心

    # ---- 组装文本 ----
    lines = [
        "=== 当前局面 ===",
        f"比分: 我方 {score[0]} - {score[1]} 对方 | 剩余步数: {steps_left}",
        f"比赛状态: {GAME_MODE_NAMES.get(game_mode, '未知')}",
    ]

    # 球
    owner_str = (
        f"我方{owned_plr}号球员持球" if owned_team == 0
        else ("对方持球" if owned_team == 1 else "球处于自由状态")
    )
    lines.append(
        f"\n[球] 位置=({ball[0]:.3f}, {ball[1]:.3f}, {ball[2]:.3f}), "
        f"运动方向=({ball_dir[0]:.3f}, {ball_dir[1]:.3f}), {owner_str}"
    )

    lines.append(f"\n[当前控制] {active}号球员")

    # 粘性动作
    sticky_labels = ["左", "左上", "上", "右上", "右", "右下", "下", "左下", "冲刺", "盘带"]
    active_sticky = [sticky_labels[i] for i in range(min(len(sticky), 10)) if sticky[i]]
    if active_sticky:
        lines.append(f"[激活中的持续动作] {', '.join(active_sticky)}")

    # 我方
    lines.append("\n[我方球员] (进攻方, 左队)")
    for i, pos in enumerate(left_pos):
        role = ROLE_NAMES.get(left_roles[i], "未知") if i < len(left_roles) else "未知"
        d2g  = _dist(pos, goal_pos)
        ctrl = " ★当前控制" if i == active else ""
        hb   = " 【持球】" if (owned_team == 0 and owned_plr == i) else ""
        mv   = (f"移动({left_dir[i][0]:.3f}, {left_dir[i][1]:.3f})"
                if i < len(left_dir) else "")
        lines.append(
            f"  {i}号 {role}: 位置({pos[0]:.3f}, {pos[1]:.3f}) "
            f"{mv} 距球门{d2g:.2f}{ctrl}{hb}"
        )

    # 对方
    lines.append("\n[对方球员] (防守方, 右队)")
    for i, pos in enumerate(right_pos):
        role = "门将" if i == 0 else f"防守{i}"
        lines.append(f"  {i}号 {role}: 位置({pos[0]:.3f}, {pos[1]:.3f})")

    # 可用动作
    useful = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 17]
    lines.append("\n[可选动作]")
    for a in useful:
        lines.append(f"  {a} = {ACTION_NAMES[a]}")

    # 战术提示
    if include_tactical_hints:
        lines.append("\n[战术参考]")
        if owned_team == 0 and owned_plr < len(left_pos):
            bp = left_pos[owned_plr]
            d  = _dist(bp, goal_pos)
            if d < 0.3:
                lines.append("  → 非常接近球门，优先考虑射门(12)！")
            elif d < 0.5:
                lines.append("  → 在射程范围内，可考虑射门(12)或做最后一传")
            for j, rp in enumerate(right_pos):
                if j == 0:
                    continue
                if _dist(bp, rp) < 0.15:
                    lines.append(
                        f"  → 防守者{j}号距离很近({_dist(bp, rp):.2f})，考虑传球避开！"
                    )

    return "\n".join(lines)


# ── 紧凑版 ──────────────────────────────────────────────

def obs_to_text_compact(obs: dict) -> str:
    """紧凑版观测描述（~100 字），适合省 token 场景。"""
    ball   = obs["ball"]
    active = obs["active"]
    owned  = obs["ball_owned_team"]
    left   = obs["left_team"]
    right  = obs["right_team"]
    steps  = obs["steps_left"]

    owner = (
        f"我方{obs['ball_owned_player']}号"
        if owned == 0
        else ("对方" if owned == 1 else "无")
    )

    t  = f"步数剩{steps}|球({ball[0]:.2f},{ball[1]:.2f})持球:{owner}|控制:{active}号\n"
    t += "我方:" + " ".join(f"{i}({p[0]:.2f},{p[1]:.2f})" for i, p in enumerate(left)) + "\n"
    t += "对方:" + " ".join(f"{i}({p[0]:.2f},{p[1]:.2f})" for i, p in enumerate(right)) + "\n"
    t += "动作:0不动|1-8方向|9长传|10高球|11短传|12射门|13加速|17盘带"
    return t
