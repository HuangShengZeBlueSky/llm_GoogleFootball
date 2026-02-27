"""
模拟 GRF 环境 — 当 gfootball 无法安装时（如 Windows），用此模块替代。

提供与真实环境相同的接口：reset() / step(action) / close()
返回与真实 raw observation 结构相同的 dict，使 LLM 管线可正常运行和调试。

用法：
    from mock_env import create_mock_environment
    env = create_mock_environment()
    obs = env.reset()
    obs, reward, done, info = env.step(action_id)
"""

import numpy as np


class MockFootballEnv:
    """模拟 academy_3_vs_1_with_keeper 环境。"""

    def __init__(self, max_steps: int = 400):
        self.max_steps = max_steps
        self.step_count = 0
        self._init_positions()

    # ─── 内部状态 ───────────────────────────────────────

    def _init_positions(self):
        """初始化球员和球的位置（模拟真实场景布局）"""
        # 左队（4人: GK + 3 进攻）
        self.left_team = np.array([
            [-1.0, 0.0],    # GK
            [0.50, 0.00],   # 持球进攻
            [0.60, 0.15],   # 跑位
            [0.60, -0.15],  # 跑位
        ], dtype=np.float32)
        self.left_dir = np.zeros_like(self.left_team)

        # 右队（2人: GK + 1 防守）
        self.right_team = np.array([
            [1.0, 0.0],     # GK
            [0.75, 0.0],    # 防守
        ], dtype=np.float32)
        self.right_dir = np.zeros_like(self.right_team)

        # 球
        self.ball = np.array([0.50, 0.00, 0.0], dtype=np.float32)
        self.ball_dir = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.ball_owned_team = 0
        self.ball_owned_player = 1  # 左队 1 号

        self.active = 1  # 控制 1 号
        self.score = [0, 0]
        self.game_mode = 0

    # ─── Gym 接口 ──────────────────────────────────────

    def reset(self):
        self.step_count = 0
        self._init_positions()
        return self._get_obs()

    def step(self, action: int):
        self.step_count += 1
        reward = 0.0
        done = False

        # 简化物理: 根据动作移动
        speed = 0.02
        dx, dy = 0, 0

        if action == 1:   dx = -speed           # left
        elif action == 2: dx, dy = -speed, -speed
        elif action == 3: dy = -speed            # top
        elif action == 4: dx, dy = speed, -speed
        elif action == 5: dx = speed             # right
        elif action == 6: dx, dy = speed, speed
        elif action == 7: dy = speed             # bottom
        elif action == 8: dx, dy = -speed, speed

        # 移动持球球员
        if self.ball_owned_team == 0:
            idx = self.ball_owned_player
            if action in range(1, 9):
                self.left_team[idx] += [dx, dy]
                self.ball[:2] = self.left_team[idx]
                self.left_dir[idx] = [dx, dy]

            elif action == 12:  # 射门
                shot_dist = abs(1.0 - self.ball[0])
                gk_dist = np.sqrt(
                    (self.right_team[0][0] - self.ball[0]) ** 2
                    + (self.right_team[0][1] - self.ball[1]) ** 2
                )
                # 简单进球概率
                if shot_dist < 0.3 and abs(self.ball[1]) < 0.15:
                    if np.random.random() < 0.6:
                        self.score[0] += 1
                        reward = 1.0
                        done = True
                elif shot_dist < 0.5:
                    if np.random.random() < 0.2:
                        self.score[0] += 1
                        reward = 1.0
                        done = True

            elif action == 11:  # 短传
                # 传给最近的队友
                candidates = [i for i in range(len(self.left_team))
                              if i != idx and i != 0]
                if candidates:
                    target = candidates[np.random.randint(len(candidates))]
                    self.ball_owned_player = target
                    self.ball[:2] = self.left_team[target]
                    self.active = target

            elif action == 9 or action == 10:  # 长传/高球
                candidates = [i for i in range(len(self.left_team))
                              if i != idx and i != 0]
                if candidates:
                    target = candidates[np.random.randint(len(candidates))]
                    self.ball_owned_player = target
                    self.ball[:2] = self.left_team[target]
                    self.active = target

        # Checkpoint 奖励：球越过 10% 线
        if self.ball[0] > 0.5 + self.step_count * 0.001:
            reward += 0.01

        # 防守者简单 AI：朝球移动
        def_idx = 1
        def_speed = 0.015
        diff = self.ball[:2] - self.right_team[def_idx]
        dist = np.linalg.norm(diff)
        if dist > 0.01:
            self.right_team[def_idx] += def_speed * diff / dist

        # 防守者抢断
        if self.ball_owned_team == 0:
            bp = self.left_team[self.ball_owned_player]
            if np.linalg.norm(self.right_team[1] - bp) < 0.05:
                if np.random.random() < 0.3:
                    self.ball_owned_team = 1
                    self.ball_owned_player = 1

        if self.step_count >= self.max_steps:
            done = True

        obs = self._get_obs()
        return obs, reward, done, {}

    def close(self):
        pass

    # ─── 观测构造 ──────────────────────────────────────

    def _get_obs(self) -> dict:
        return {
            "ball": self.ball.tolist(),
            "ball_direction": self.ball_dir.tolist(),
            "ball_rotation": [0.0, 0.0, 0.0],
            "ball_owned_team": self.ball_owned_team,
            "ball_owned_player": self.ball_owned_player,
            "left_team": self.left_team.tolist(),
            "left_team_direction": self.left_dir.tolist(),
            "left_team_tired_factor": [0.0] * len(self.left_team),
            "left_team_yellow_card": [0] * len(self.left_team),
            "left_team_active": [True] * len(self.left_team),
            "left_team_roles": [0, 5, 5, 9],  # GK, CM, CM, CF
            "right_team": self.right_team.tolist(),
            "right_team_direction": self.right_dir.tolist(),
            "right_team_tired_factor": [0.0] * len(self.right_team),
            "right_team_yellow_card": [0] * len(self.right_team),
            "right_team_active": [True] * len(self.right_team),
            "right_team_roles": [0, 1],  # GK, CB
            "active": self.active,
            "designated": self.active,
            "sticky_actions": [0] * 10,
            "score": list(self.score),
            "steps_left": self.max_steps - self.step_count,
            "game_mode": self.game_mode,
        }


def create_mock_environment(**kwargs):
    """兼容 gfootball.env.create_environment 的签名"""
    return MockFootballEnv(max_steps=kwargs.get("max_steps", 400))
