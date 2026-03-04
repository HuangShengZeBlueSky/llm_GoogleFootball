# Code Architecture & IPO

Our agent testbed follows a consistent **(I) Input - (P) Process - (O) Output** decoupled backbone throughout:

## 1. Physical Environment Layer (run_game.py)

This is the divine hand that truly controls the fate of the underlying Google Football sandbox, bearing the execution efficacy of every physical move.

- **(I) Input**: Receives the `action_id (0-18)` sent back from the gateway.
- **(P) Process**: The engine computes internal physics according to Newton's laws of motion. To ensure the LLM doesn't have to operate every frame like muscle memory, we introduced an `interval` (frame skipping). During the blank frames where the LLM offers no new instructions, it continuously reuses (or resets to 0) the current action ID.
- **(O) Output**: Spits out the `reward` (scoring signal) and the **Raw Observation Dict** containing the XYZ coordinates of all 22 players on the pitch and current ball possession.


## 2. Situational Awareness Module (obs_to_text.py)

LLMs lack visual perception, so we must act as their eyes here. We convert rigid mathematical coordinate arrays into emotional, human-like situation reports.

- **(I) Input**: The Raw Observation coordinate dictionary output by the environment layer.
- **(P) Process**: The code traverses our possession status, the distance of the nearest defender, and the formation structure of friend and foe. Concurrently, it applies heuristic prior rules to determine if a passing lane is blocked by defenders and if teammates are in the attacking half ready to receive.
- **(O) Output**: Distilled into a highly condensed **Text Description** of the situation. e.g., "Player 1 is far from the goal, surrounded by 2 defenders..."


## 3. Decision Brain Gateway (llm_client.py)

This module acts as the hub for deploying an endless pool of cloud compute, supporting stubbed calls to various standardized RESTful APIs like those compatible with OpenAI.

- **(I) Input**: Splices the solidified "Football Tactical Guide (System Prompt)" with the freshly baked "Situation String" from above, combining them with the most recent Working Memory.
- **(P) Process**: Makes outbound calls to the LLM via HTTPS. Accounting for API network fluctuations, we implemented a concurrency retry mechanism based on exponential backoff (defaults to 5 retries, avoiding occasional 429 and 5xx faults).
- **(O) Output**: The LLM returns either pure text containing complex internal deliberations or a JSON string from the cloud.


## 4. Fault-Tolerant Parser (action_parser.py)

To counter Large Language Models that are highly prone to "playing tricks" in the final mile (outputting non-standard structures), three lines of defense are established here.

- **(I) Input**: The messy output stream `raw_response_string` returned by the LLM.
- **(P) Process**: 
  - First Line of Defense: Regex extracts pure JSON blocks `{...}` for deserialization.
  - Second Line of Defense: If the first fails, it forcibly searches the context for isolated numeric values formatted like `action: 11`.
  - Third Line of Defense: If the first two crash, it attempts to match semantic keyword pools like "pass", "shoot".
  - Fallback: If totally annihilated, the player stands idle (`action_id = 0`).
- **(O) Output**: A safe, legal `action_id (0-18)`.


## 5. Multi-Model Evaluation Console (run_multiple_experiments.py)

If a single successful run isn't enough, this is the ultimate evaluation testing room for mass-producing robots!

- **(I) Input**: A configured roster of candidate models `MODELS_TO_TEST`.
- **(P) Process**: The script establishes sandboxed YAML configuration files for every contestant, sequentially launching isolated Python processes for bouts, while the built-in Logger meticulously records their exact inference latency and response text.
- **(O) Output**: Spits out a `final_report.json` in each isolated space, which after merging, translates into the entire ecosystem's `data.json` and the static frontend Leaderboard.
