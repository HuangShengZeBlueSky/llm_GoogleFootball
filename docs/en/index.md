---
layout: home

hero:
  name: "LLM Google Football"
  text: "Moonshot Guide"
  tagline: Let Large Language Models take over the decision-making brain on the football pitch, enabling pure text-based end-to-end tactical execution and bulk parallel evaluation.
  actions:
    - theme: brand
      text: Quick Start
      link: /en/guide/quickstart
    - theme: alt
      text: What is LLM-Football?
      link: /en/guide/introduction

features:
  - title: 👁 Situational Awareness Translation (Obs-to-Text)
    details: No need to process complex pixel streams. Converts GRF's raw 3D coordinates into aligned natural language, letting the LLM instantly understand the pitch situation.
    icon: 🧠
  - title: ⚡ Parallel Leaderboard Testing
    details: Built-in one-click racing script run_multiple_experiments.py. Easily configure 4 mainstream LLMs and automatically evaluate them against each other.
    icon: 🎮
  - title: 📊 Cool Visual Reports
    details: Generates and deploys a multi-dimensional tournament Leaderboard highlighting high-value metrics like win rate, average advance score, and latency.
    icon: 🏆
---

<div class="custom-home-content">
  <h2>Can Large Language Models Really Play Football?</h2>
  <p>In traditional Reinforcement Learning (RL), training a game AI often consumes tens of millions of frames of experience fragments. In the LLM era, leveraging world knowledge and Zero-shot reasoning capabilities, can we use a single Prompt to let a general LLM (like GPT-4 / Qwen / GLM / Kimi) directly command players to run, shoot, and win matches?</p>
  <p>This project provides an out-of-the-box experimental framework, currently supporting the <code>academy_3_vs_1_with_keeper</code> scenario to automatically evaluate the combat power of various AI contestants.</p>
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
