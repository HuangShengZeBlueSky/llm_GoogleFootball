# 🏆 诸神之战 · 排行榜

这里是 `academy_3_vs_1_with_keeper` 场景下的最新评测全记录。

本页面的排行榜数据均是由大语言模型通过 `run_multiple_experiments.py` 全自动实机（最多400物理步+间隔5步）对垒后的战绩动态渲染而成。

<script setup>
import LeaderboardTable from './components/LeaderboardTable.vue'
import { data } from './data.data.js'
</script>

<LeaderboardTable :leaderboardData="data" />

## 🎖️ 赛况短评

通过以上实时数据透视，我们在大语言模型的决策空间下看到了以下结论：
- **进球终结者**: GLM-5 展示了 80% 的卓越进球率与场均 114 步即闪电破门的统治力。
- **神速大脑**: Gemini-3.0-Flash 用微缩版体量斩获极快响应延迟（毫秒级）。
- **全部零失误**: 得益于我们在工程设计中优异的正则降级 parser 系统，所有测试选手的指令解析崩溃率皆为 `0.0%`。
