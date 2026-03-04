# Quickstart

In this section, you will learn how to clone the project locally, configure the LLM APIs, and successfully run your first game!

## 1. Environment Installation

This repository depends on a Python environment and the underlying modified `gfootball` engine. Using a Conda isolated environment is highly recommended:

```bash
# Clone the repository
git clone https://github.com/HuangShengZeBlueSky/llm_GoogleFootball.git
cd llm_GoogleFootball

# Run the one-click environment setup script (automatically creates conda env and installs engine)
bash setup_conda_env.sh
```

## 2. Configure LLM API Keys

We isolate all sensitive configuration (API keys) in the `.env` file at the root of the project.

First, copy the real configuration template:
```bash
cp .env.example .env
```

Next, open `.env` and fill in your preferred LLM provider API details:
```ini
# OpenAI-compatible LLM endpoint
# e.g., https://api.openai.com/v1 or your proxy URL (do not append /chat/completions)
LLM_API_BASE=https://api.openai.com/v1

# Required: API Key
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxx

# Model Name (Must exactly match the provider's available models)
LLM_MODEL=gpt-4o
```

## 3. Run Your First Match!

### Mode A: Test the Demo Environment

If you just want to see if the model can output formatted tactical actions without crashing, use our quick config:

```bash
# Run 2 episodes using the quick config (fewer total steps), calling the LLM every 5 frames
python llm_football_agent/run_game.py --config configs/config.quick.yaml --episodes 2 --interval 5
```

### Mode B: Full Power (Authentic Game Match)

Start a real match test with comprehensive logging mounted (the script automatically handles headless server display driver edge cases):

```bash
# Format: bash run_real_game.sh <total_episodes> <decision_frame_skip_interval>
bash run_real_game.sh 5 5
```

When the match concludes, you will find all the model's stepping logs, final JSON report, and replay videos in the automatically generated `experiment_logs/exp_<timestamp>` folder!
