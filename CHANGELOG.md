# Changelog

All notable changes to this project are documented here.

## [0.2.3] - The service says when its problem changes and when it is over

- The log said a problem once and then nothing, so a server that was down for a moment and one that refused the token looked the same. It now says every new problem when it changes (`unreachable`, `unauthorized`...) and *the server answers again* when it is over.

## [0.2.2] - It runs: movement on the cameras, weighed with the radars

- **`python -m armor_server_ai.service`**, the observation service the server asks nothing of and which asks the server (with its own token, `ARMOR_AI_TOKEN`): while the system is **armed** it takes one tiny grey frame (64 x 36, from the camera's stream, never stored) of each camera every few seconds, measures how much of the picture moved (`motion.py`: no neural network, no GPU), and - when the movement is seen in several frames in a row, is not the whole picture changing (a light switched on), and the policy finds it worth a review - tells the server, which raises a `camera_motion` alarm (once until it is closed) that goes to the notifications, Telegram and Home Assistant. Disarmed, it looks at nothing. It holds no camera address or password and cannot arm, disarm or change anything.
- **The policy** knows a new label, `motion` (something moved, not what it is): strong movement (80 % of what moving fully means) **and** a radar track agree is `high`; weaker movement is a `review`; the radar alone is not reported by this service. It cannot tell a person from a cat or a branch: that needs the Jetson and a detector. The day/night profile comes from the radar nodes' light sensor, or from how bright the picture is when none says.
- Settings from the environment: `ARMOR_AI_TOKEN`, `ARMOR_AI_SERVER_URL`, `ARMOR_AI_INTERVAL_S` (3), `ARMOR_AI_CONFIRM_FRAMES` (2), `ARMOR_AI_COOLDOWN_S` (60); `--once` makes one pass and prints what it saw. 35 tests (9 new).

## [0.2.1]

- A GitHub Actions CI baseline (`.github/workflows/ci.yml`): validates the manifest, the version, CHANGELOG.md's heading, the seven README translations' structure and its own local Markdown links, then runs this project's real build/test through `tools/armor_project_tool.py build-test .` (vendored from ARMOR-COMMON, alongside `tools/armor_ci_validate.py` and `tools/_armor_readme_parity.py`, which do the manifest/docs checking).

## [0.2.0]

- Day/night profile with hysteresis, explainable fusion of detections and radar tracks, and checksum-verified engine registry.
- Decisions never authorise an action.
- 26 tests.
