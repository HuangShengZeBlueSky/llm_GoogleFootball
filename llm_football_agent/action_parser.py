"""
Text-to-Action Parser — 从 LLM 原始输出中提取动作 ID。

支持三种容错解析：
  1. JSON 格式  {"action": 12, "reason": "..."}
  2. 纯数字      "12"
  3. 动作关键词  "射门" / "shot"
"""

import json
import re


ACTION_MAP = {
    # 英文
    "idle": 0, "left": 1, "top_left": 2, "top": 3,
    "top_right": 4, "right": 5, "bottom_right": 6, "bottom": 7,
    "bottom_left": 8, "long_pass": 9, "high_pass": 10,
    "short_pass": 11, "shot": 12, "sprint": 13,
    "release_direction": 14, "release_sprint": 15,
    "sliding": 16, "dribble": 17, "release_dribble": 18,
    # 中文
    "不动": 0, "空闲": 0,
    "左": 1, "左上": 2, "上": 3, "右上": 4, "右": 5,
    "右下": 6, "下": 7, "左下": 8,
    "长传": 9, "高球": 10, "高球传球": 10,
    "短传": 11, "射门": 12,
    "加速": 13, "冲刺": 13,
    "释放方向": 14, "停止加速": 15,
    "铲球": 16, "盘带": 17, "停止盘带": 18,
}

ACTION_NAMES = {
    0: "idle", 1: "left", 2: "top_left", 3: "top", 4: "top_right",
    5: "right", 6: "bottom_right", 7: "bottom", 8: "bottom_left",
    9: "long_pass", 10: "high_pass", 11: "short_pass", 12: "shot",
    13: "sprint", 14: "release_dir", 15: "release_sprint",
    16: "sliding", 17: "dribble", 18: "release_dribble",
}


def parse_action(response: str) -> dict:
    """
    从 LLM 响应中提取动作和理由。

    Returns:
        {"action": int, "reason": str, "parse_success": bool}
    """
    # 1) JSON
    try:
        m = re.search(r"\{[^}]+\}", response)
        if m:
            data = json.loads(m.group())
            act = int(data.get("action", data.get("动作", -1)))
            reason = str(data.get("reason", data.get("理由", "")))
            if 0 <= act <= 18:
                return {"action": act, "reason": reason, "parse_success": True}
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # 2) 纯数字
    nm = re.search(r"\b(\d{1,2})\b", response)
    if nm:
        act = int(nm.group(1))
        if 0 <= act <= 18:
            return {"action": act, "reason": response[:50], "parse_success": True}

    # 3) 关键词
    low = response.lower().strip()
    for kw, aid in ACTION_MAP.items():
        if kw in low:
            return {"action": aid, "reason": response[:50], "parse_success": True}

    # fallback
    return {"action": 0, "reason": f"解析失败: {response[:50]}", "parse_success": False}
