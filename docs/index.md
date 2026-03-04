---
layout: home

hero:
  name: "LLM Google Football"
  text: "探月指北"
  tagline: 让大语言模型接管足球场的决策大脑，实现纯文本态下的端到端战术执行与批量化平行评估。
  actions:
    - theme: brand
      text: 快速开始
      link: /guide/quickstart
    - theme: alt
      text: 什么是 LLM-Football？
      link: /guide/introduction

features:
  - title: 👁 态势感知转译 (Obs-to-Text)
    details: 无需处理复杂像素流，将 GRF 的原始 3D 坐标转换为对齐的人类自然语言，大模型瞬间看懂球场局势。
    icon: 🧠
  - title: ⚡ 并行打榜测试
    details: 内置一键赛马脚本 run_multiple_experiments.py。轻松配置四家主流大模型，自动打榜评估。
    icon: 🎮
  - title: 📊 炫酷的可视化报表
    details: 生成并一键部署包含胜率、场均推进分、延迟等高价值指标的多维度赛事排行榜 (Leaderboard)。
    icon: 🏆
---

<div class="custom-home-content">
  <h2>大模型真能踢球吗？</h2>
  <p>在传统的强化学习（RL）领域，训练一个游戏 AI 往往需要消耗数千万帧的经验碎片。而在 LLM 时代，借助世界知识与 Zero-shot 推理能力，我们能否用一段 Prompt 就让通用大语言模型（如 GPT-4 / Qwen / GLM / Kimi）直接统治球场？</p>
  <p>本项目提供了一套完全开箱即用的实验框架，现已支持在 <code>academy_3_vs_1_with_keeper</code> 场景下全自动评测各路 AI 选手的战斗力。</p>
</div>

<style>
.custom-home-content {
  max-width: 900px;
  margin: 40px auto;
  text-align: center;
  padding: 0 20px;
}
.custom-home-content h2 {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 20px;
}
.custom-home-content p {
  color: var(--vp-c-text-2);
  line-height: 1.8;
  margin-bottom: 1em;
}
</style>
