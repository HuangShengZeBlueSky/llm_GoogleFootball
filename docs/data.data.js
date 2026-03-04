import fs from 'fs'
import path from 'path'

export default {
    watch: ['../../data.json'],
    load() {
        try {
            // 动态读取项目根目录的最新产出 data.json
            const configPath = path.resolve(process.cwd(), '../data.json')
            const file = fs.readFileSync(configPath, 'utf8')
            return JSON.parse(file)
        } catch (e) {
            console.warn("未能读取真实 data.json，返回默认空数组或兜底 mock。请确保跑过 parse_leaderboard.py")
            return [
                {
                    "model_name": "GLM_5 (Mock)",
                    "score_rate": 0.8,
                    "avg_reward": 1.28,
                    "avg_steps": 114.4,
                    "avg_latency": 6611,
                    "error_rate": 0.0,
                    "episodes": 5
                },
                {
                    "model_name": "Gemini_3_0_Flash (Mock)",
                    "score_rate": 0.4,
                    "avg_reward": 1.19,
                    "avg_steps": 258.4,
                    "avg_latency": 4611,
                    "error_rate": 0.0,
                    "episodes": 5
                }
            ]
        }
    }
}
