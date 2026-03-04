# Project Overview

## What is this?

**LLM Google Football** is a fully automated benchmarking framework that explores the potential of Large Language Models (LLMs) to perform "zero-shot real-time game playing". We convert the complex 3D physical combat environment of "Google Research Football" into a text space that language models can easily grasp.

## Why build this?

Traditional Reinforcement Learning often requires tens of millions of frames of trial and error to train an AI capable of scoring in specific scenarios.
However, in the LLM era, models are pre-equipped with a massive "world knowledge" library (they know what offside means, what a cutback pass is, and what one-two passing entails).

This project aims to answer a core scientific question:
**If inspired merely by a simple Prompt, can LLMs directly direct players to position themselves, shoot, and win games on the pitch?**

## Core Features

- 🎯 **Out-of-the-box Sandbox**: Comes with the pre-configured `academy_3_vs_1_with_keeper` test scenario, pitting three attackers against one defender and a goalkeeper.
- 👁 **Situational Text Translation**: Discards heavy pixel streams to extract the X/Y coordinates of all actors on the pitch, possession status, and distance between friend and foe, condensing them into a highly-prioritized situational "battle report" of under 50 tokens.
- 🧠 **Highly Decoupled Brain Gateway**: Built-in retry and concurrency management strategies. You can seamlessly run tests against major APIs like OpenAI, Qwen, GLM, and Kimi.
- 📈 **One-Click Racing Experiment (Leaderboard)**: Supports parallel execution of match evaluations across multiple LLMs, automatically extracting win rates, average duration, and response latency to render a static roll of honor.
