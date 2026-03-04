# Bulk Racing Testing

When you've successfully run locally and tweaked your prompts, you undoubtedly want to know: **Which large model is truly the smartest and performs best under the current settings?**

We need automated racing lanes, not just manually opening ten terminal windows.

## 1. Principle & Configuration

The core logic of the ranking engine `run_multiple_experiments.py` is to loop through your registered `MODELS_TO_TEST`. It will:
1. Generate a unique Session ID (`exp_2026xxxx_xxxxxx`) for every gladiatorial bout.
2. Forcibly replace environment hyperparameters with your specified constants (like `interval=5`, `epsiodes=5`), guaranteeing fair competition.
3. Iteratively pull up sub-processes to execute `run_game.py`, and elegantly archive previously scattered JSON logs by model category under the same large directory, making it easy for you to investigate exactly which model made a bad move on which step in which game.

## 2. Registering Draft Models

Open `run_multiple_experiments.py` and register your large model APIs:

```python
MODELS_TO_TEST = [
    {
        "name": "GLM_5",
        "model": "GLM-5",
        "provider": "openai_compatible"
    },
    {
        "name": "Gemini_3_0_Flash",
        "model": "Gemini-3.0-Flash",
        "provider": "openai_compatible"
    }
]
```
*(API keys and Base URLs are automatically loaded from your `.env` file.)*

## 3. Firing the Starting Gun

In the console, type:

```bash
python run_multiple_experiments.py
```

The terminal will print a progress bar in real-time similar to `[1/4] Model: GLM_5 (Model: GLM-5) ... [OK] Model GLM_5 finished in: xxx s`. Once all models have completed their participation, the ranking test concludes.

## 4. Crowning the Leaderboard

To directly demonstrate the effects to mentors and the outside world, the project comes with a scanner that one-click parses all the benchmark JSONs and purifies them into a leaderboard function:

```bash
python parse_leaderboard.py
```

It will scan every contestant in the latest batch's `experiment_logs` root directory, throw a `LEADERBOARD.md` static text document into the current directory, and update the `data.json` used to maintain the site's real-time dynamic data. At this point, you can head over to the left sidebar to view the visual **Leaderboard**.
