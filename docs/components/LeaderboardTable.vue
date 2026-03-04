<script setup>
import { computed } from 'vue'

const props = defineProps({
  leaderboardData: {
    type: Array,
    required: true
  }
})

// 为特定列进行格式化
const formatWinRate = (rate) => `${(rate * 100).toFixed(1)}%`
const formatLatency = (ms) => `${ms.toFixed(0)} ms`

// 排行榜颜色/图标映射
const getRankClass = (index) => {
  if (index === 0) return 'rank-1'
  if (index === 1) return 'rank-2'
  if (index === 2) return 'rank-3'
  return 'rank-other'
}

const getRankMedal = (index) => {
  if (index === 0) return '🏆'
  if (index === 1) return '🥈'
  if (index === 2) return '🥉'
  return `${index + 1}`
}
</script>

<template>
  <div class="leaderboard-wrapper">
    <div v-if="!leaderboardData || leaderboardData.length === 0" class="no-data">
        <p>暂无对局历史，快去运行打榜脚本吧！</p>
    </div>
    
    <div v-else class="table-container">
      <table>
        <thead>
          <tr>
            <th>排名</th>
            <th>🤖 模型 (Model)</th>
            <th>⚽ 进球胜率</th>
            <th>🌟 平均分 (Reward)</th>
            <th>⏳ 场均步数</th>
            <th>⚡ 响应延迟</th>
            <th>❌ 解析失败率</th>
            <th>场次</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in leaderboardData" :key="row.model_name" :class="getRankClass(i)">
            <td class="rank-col">
              <span class="medal" :class="'medal-' + (i+1)">{{ getRankMedal(i) }}</span>
            </td>
            <td class="model-col">{{ row.model_name }}</td>
            <td class="stat-col win-rate">{{ formatWinRate(row.score_rate) }}</td>
            <td class="stat-col reward">{{ row.avg_reward.toFixed(2) }}</td>
            <td class="stat-col steps">{{ row.avg_steps.toFixed(1) }}</td>
            <td class="stat-col latency">{{ formatLatency(row.avg_latency) }}</td>
            <td class="stat-col error">{{ formatWinRate(row.error_rate) }}</td>
            <td class="stat-col episodes">{{ row.episodes }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.leaderboard-wrapper {
  margin: 2rem 0;
  font-family: var(--vp-font-family-base);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  background: var(--vp-c-bg-soft);
  border: 1px solid var(--vp-c-divider);
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  text-align: center;
  margin: 0;
}

th {
  background: var(--vp-c-bg-mute);
  padding: 1rem;
  font-weight: 600;
  font-size: 0.9em;
  color: var(--vp-c-text-2);
  white-space: nowrap;
}

td {
  padding: 1.2rem 1rem;
  border-bottom: 1px solid var(--vp-c-divider);
  transition: background-color 0.2s;
}

tr:last-child td {
  border-bottom: none;
}

tr:hover td {
  background-color: var(--vp-c-bg-mute);
}

/* 奖牌列 */
.rank-col {
  width: 60px;
}
.medal {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  font-weight: bold;
  background: var(--vp-c-bg-alt);
}

/* 神仙特效 ✨ */
tr.rank-1 .medal {
  background: linear-gradient(135deg, #fef08a, #f59e0b);
  box-shadow: 0 0 15px rgba(245, 158, 11, 0.5);
  transform: scale(1.1);
}
tr.rank-2 .medal {
  background: linear-gradient(135deg, #f1f5f9, #94a3b8);
}
tr.rank-3 .medal {
  background: linear-gradient(135deg, #fcd34d, #b45309);
  color: white;
}

/* 模型名称强化 */
.model-col {
  font-weight: 600;
  text-align: left;
}
tr.rank-1 .model-col { color: #f59e0b; font-size: 1.1em; }
tr.rank-2 .model-col { color: #94a3b8; }
tr.rank-3 .model-col { color: #d97706; }

/* 关键数据高亮 */
.stat-col {
  font-family: 'Courier New', Courier, monospace;
  font-weight: bold;
}
tr.rank-1 .win-rate { color: #10b981; }

.no-data {
  padding: 3rem;
  text-align: center;
  color: var(--vp-c-text-2);
}
</style>
