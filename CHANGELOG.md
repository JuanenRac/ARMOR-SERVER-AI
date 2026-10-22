# Changelog

All notable changes to this project are documented here.

## [Unreleased]

- The tests find the source folder by themselves wherever they are started from (two of them failed unless the path was set by hand), and a ruff configuration (errors, unused names and whitespace) is in `pyproject.toml` with the code clean under it.

## [0.2.6] - A hiccup of the server no longer silences a camera, and odd answers do not end the service

- **An observation the server never received** (it was restarting, a limit, a timeout) gives the cooldown back: the next movement is told at once instead of after a minute of silence.
- **A camera that fails to answer keeps what is remembered of it** (its cooldown and its day/night choice); only the previous picture is forgotten. A failure of a camera or of the picture is said once on stderr, and said again when it comes back.
- **The service survives whatever the server sends:** a context that is not an object, nodes that are not objects, targets as a list, and one camera that cannot be judged no longer end the pass for all the others or the process; `--once` says the problem in a line instead of a traceback.
- **A radar track no longer turns a trace of movement into a review:** a plain movement counts a radar track only when it is at least 30 % sure; the reason now says what is true.
- **The server limit on pictures is respected:** the pass is spaced out so that many cameras never exceed 200 pictures a minute.
- `ARMOR_AI_SERVER_URL` must be `https://` or `http://` to this same machine; answers are read up to a limit.
- Engines need an `engines.json` by default (`require_manifest=False` to accept them unverified) and a link is not an engine; the JSONL worker refuses a `radar_tracks` that is not a whole number; the `armor-ai` command runs the service.
- The manifest says what this is (functional movement service for the CM5, not a Jetson inference service), the documents say three routes and how the failures are reported. Tests: 46 (before 42).

## [0.2.5] - Zones of the picture to ignore

- The movement detector can leave out parts of a camera's picture: the server hands it the ignore zones of each camera (rectangles as fractions of the picture) and the pixels inside them count for nothing, neither the changes, nor the median that is taken away, nor the share that is measured.
- A picture that is almost all ignored (under about three per cent left) is not judged, and a zone that is not a rectangle inside the picture is left out; at most sixteen zones count.
- Tests hold the mask, a tree that waves inside a zone, a person outside it (a bigger share of the smaller picture) and the limits.

## [0.2.4] - Motion and service fixes

- Fixes in the motion handling and in the service, with tests.

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
