# 🏆 Clash of Gods · Leaderboard

Here is the latest evaluation record under the `academy_3_vs_1_with_keeper` scenario.

The leaderboard data on this page is dynamically rendered from the combat records after fully automated practical matchups (max 400 physics steps + 5 step intervals) executed by the large language models via `run_multiple_experiments.py`.

<script setup>
import LeaderboardTable from '../components/LeaderboardTable.vue'
import { data } from '../data.data.js'
</script>

<LeaderboardTable :leaderboardData="data" />

## 🎖️ Match Commentary

Through the real-time perspective data above, we observed the following conclusions within the decision space of Large Language Models:
- **Goal Terminator**: GLM-5 demonstrated an outstanding 80% goal rate and the dominant capability of a lightning strike on average 114 steps per match.
- **Speed of Thought**: Gemini-3.0-Flash utilized its miniature size to secure extremely fast response latency (millisecond level).
- **Absolute Zero Errors**: Thanks to the excellent regex fallback parser system in our engineering design, the instruction parsing crash rate for all tested contestants was `0.0%`.
