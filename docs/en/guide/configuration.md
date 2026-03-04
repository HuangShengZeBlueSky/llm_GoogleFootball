# Experimental Configuration Guide

All major racing hyperparameters and engine attribute settings are under the core governance of `configs/config.yaml`. Even if you use overrides in batch processing codes, it remains the foundational dictionary you must understand.

## `config.yaml` Quick Reference

### 🤖 LLM (Model Behavior Base)
| Parameter Name | Description | Default / Suggestion |
| :--- | :--- | :--- |
| `model` | Core participating model name (e.g., qwen-max, gpt-4o) | `gpt-4o` |
| `provider` | API call provider adapter | `openai_compatible` |
| `temperature` | Controls divergence and imagination. Higher is wilder | `0.1` (Safe playing) |
| `max_tokens` | Maximum word count output allowed per response | `800` |
| `max_retries` | Allowed persistent retry attempts for errors like 429 rate limiting | `5` |

### 🎮 Env (Football Physics Field Params)
| Parameter Name | Description | Default / Suggestion |
| :--- | :--- | :--- |
| `scenario_name` | Map level name | `academy_3_vs_1_with_keeper` |
| `render` | Whether to pull up a GUI animation pop-up on the local machine (Linux server heavily recommended no) | `false` |
| `write_video` | Whether to save every match as a high-definition battle recording for post-match review | `true` |
| `write_full_episode_dumps` | Whether to retain `.dump` replay files | `true` |

### 🔬 Experiment (Ranking Format)
| Parameter Name | Description | Default / Suggestion |
| :--- | :--- | :--- |
| `num_episodes` | How many ranked matches to play per startup test | `5` |
| `max_steps_per_episode` | The upper limit of physical steps before the engine pulls the plug (timeout draw) | `400` |
| `interval_steps` | LLM frame-skipping frequency, how many steps to skip before waking up the LLM brain to issue commands | `5` |

## The Onion Architecture of Environment Overrides

You don't need to touch the YAML to modify your secret keys! At the execution layer of `run_game.py`, the system employs an **onion-style overloaded merge model**:

1. **Bottom Fallback**: Gulps down all the setting attributes inside `config.yaml` first.
2. **Intermediate Tampering**: The engine sniffs your workspace's `.env`. If you wrote `LLM_MODEL=xxx`, it forcibly overwrites the bottom layer.
3. **Top Veto Power**: If you directly hit the entry point via Bash Shell commands like `--episodes 10`, the CLI possesses the supreme interpretive and overwrite authority.
