<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-SERVER-AI banner" width="100%">
</p>

# 👁️ ARMOR-SERVER-AI

<p align="center">
  🇺🇸 <b>English</b> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### Observation service: movement on the cameras weighed with the radars; it decides and explains, never actuates

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Target-Jetson%20Orin%20NX-76b900.svg" alt="Target">
  <img src="https://img.shields.io/badge/Tests-130%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.2.9-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**Honesty check - what runs today:** The decision layer and the movement detector are real and tested (130 tests), and the observation service **runs on the CM5 test bench**: while the system is armed it looks at tiny grey frames of the real IP cameras and reports movement weighed with the radars. It cannot tell a person from a cat or a branch: **there is no detection model yet**, and nothing has run on the Jetson, TensorRT or an RTSP stream decoded there.

---

## 📋 At a glance

| | |
|---|---|
| Version | `0.2.9` |
| Maturity | Established |
| Role | Observation service: movement weighed with the radars, recommendations only |
| Stack | Python 3.11+, standard library only |
| Tests | 130 (`python -m unittest discover -s tests`) |
| Contract | Client of ARMOR-SERVER: 3 routes under `/api/v1/ai/`; it is never called |
| Runs on | The CM5 test bench (as a service, see ARMOR-DEVOPS) or any computer |
| On real hardware | Running as a service on the CM5 test bench with the real IP cameras (movement only); nothing on a Jetson |
| License | GPL-3.0-or-later |

**Jump to:** [Overview](#-overview) · [Architecture](#-architecture) · [Security](#-security--safety) · [Interfaces](#-interfaces) · [Configuration](#-configuration) · [Quick start](#-quick-start) · [Testing](#-testing) · [Troubleshooting](#-troubleshooting) · [Structure](#-repository-structure) · [Related](#-related-projects)

## 🚦 Project status

Each line is one part of this repository and the light says how far it is today. It is written from what the repository can show (tests, builds, runs), not from what is planned.

🟢 Done and verified · 🟡 Works, with known limits · 🟠 Partly done or not verified yet · 🔴 Not done or not working

| Area | State | What it means here |
|---|---|---|
| Software | 🟡 | The movement detector and the decision layer run as a service on the CM5 test bench, but there is no detection model yet: it cannot tell a person from a cat or a branch. |
| Tests | 🟢 | 130 tests pass (`python -m unittest discover -s tests`). |
| Hardware | 🟡 | While the system is armed it looks at tiny grey frames of the real IP cameras of the CM5 test bench; nothing has run on a Jetson, with TensorRT or on a decoded RTSP stream. |
| Integration | 🟡 | It reports movement weighed with the radars to the server of the CM5 test bench. |
| Security | 🟡 | The service never acts (every decision carries `authorizes_action = false`), refuses a token under 24 characters and a server address that is not `https://` or this same machine, and never stores a picture; tested, with no independent review. |
| Documentation | 🟢 | Eight languages and the changelog are up to date. |

## 🎯 Overview

* **The observation service:** `python -m armor_server_ai.service` is never called by the server (it asks the server, with its own token): while the system is **armed** it takes one tiny grey frame (64 x 36, from the camera's stream, never stored) of each camera every few seconds, measures how much of the picture moved and, when radar tracks agree, reports it to ARMOR-SERVER with its token.
* **Zones of the picture to ignore:** the server hands it the ignore zones of each camera and the pixels inside them count for nothing (a tree that waves, a road); a picture that is almost all ignored is not judged and at most sixteen zones count.
* **Day/night profile with hysteresis:** low-light below 30 lux, back to daylight only above 60 lux and never twice within 30 s, so dusk cannot make it flap.
* **Explainable fusion:** each detection or movement and the radar tracks give a severity (`ignore`, `review`, `high`) with the reasons behind it; strong movement **and** a radar track agree is `high`, weaker movement is a `review`.
* **Recommendations only:** a decision always carries `authorizes_action = false`. The central server authenticates and authorises every action.
* **Checksum-verified engines:** pre-built TensorRT engines are accepted only if present, non-empty and, with an `engines.json`, matching their SHA-256. Nothing is compiled or downloaded.
* **A service that says what is wrong:** it reports every new problem when it changes (`unreachable`, `unauthorized`…) and *the server answers again* when it is over; a JSONL worker keeps numbered, explained results and a bad line never stops the stream.
* **A daily summary of the events (optional, off by default):** `--daily-summary FILE --summary-config CONFIG` turns the events of a day (alarms, link losses, readings, power) into counts by type, zone and hour, the serious alarms, the nodes that lost their link, the outlying readings and the consumption peaks, a text from templates in the eight languages, and five explainable patterns (the same alarm at the same time of the hour, a sensor that fails on and off, a node that keeps losing its link, recurring false alarms, consumption far above its moving average), each with its evidence and every threshold in the settings file. An optional note from an AI provider is also off by default: only a simulated provider ships, nothing is sent away without an explicit switch, and names, addresses and credentials are redacted first.

## 🧩 Role in A.R.M.O.R.

ARMOR-SERVER-AI is the part that watches the cameras for movement while the house is armed. It never acts: it tells [ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER) what it saw and why (movement and radar tracks agreeing is `high`), and the server decides what to do. A model that recognises a person, run on a Jetson, is the next step; [ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION) holds the zones, masks and rules that model will use.

| It talks to | How | What for |
|---|---|---|
| ARMOR-SERVER | it asks the server (`/api/v1/ai/*`, token `ARMOR_AI_TOKEN`) | the cameras, their grey frames and the zones to ignore in; the observation out |
| ARMOR-NODE-RADAR | through the server | the radar tracks and the light of the nodes that cover each camera |
| ARMOR-VISION | rules and masks (next step) | the zones, masks and rules the detection model will use |
| ARMOR-DEVOPS | installs it as a service | deployment on the CM5 test bench |

## 🏛️ Architecture

<p align="center">
  <img src="images/architecture.svg" alt="ARMOR-SERVER-AI architecture: what it asks the server, the observation service with its modules, and what it tells" width="100%">
</p>

## 🔒 Security & Safety

| Threat | Defence |
|---|---|
| The service acts on its own | Never: every decision carries `authorizes_action = false`; the central server authenticates and authorises every action |
| The token crosses a network in clear | `ARMOR_AI_SERVER_URL` must be `https://`, or `http://` to this same machine (`127.0.0.1`, `localhost`); otherwise the service refuses to start |
| A weak token | `ARMOR_AI_TOKEN` of at least 24 characters (the server asks the same) |
| Huge answers from the server | The context is read up to 1 000 000 bytes and an answer to an observation up to 65 536; a frame is exactly 64 x 36 = 2304 bytes |
| Pictures kept | The tiny grey frame is never stored |
| A tampered TensorRT engine | Only pre-built engines (`daylight`, `low_light`) that exist, are not empty and, with an `engines.json`, match their SHA-256; nothing is compiled or downloaded |
| A false alarm from a change of light | A change of more than 60 % of the picture is light, not movement; less than 1 % is not movement; pixel threshold 18; at least 64 pixels counted; at most 16 zones to ignore and a picture that is almost all ignored is not judged |
| Day and night flicker; stale data; a hostile JSON line | Hysteresis (low light under 30 lux, daylight again over 60 lux, never twice within 30 s, lux up to 200 000); an observation older than 10 s never raises an alert; a JSON line over 4096 bytes is refused and the stream goes on |

## 🔌 Interfaces

| Route | Auth | What it does |
|---|---|---|
| `GET /api/v1/ai/context` | token `ARMOR_AI_TOKEN` | the houses: nodes and cameras, and the zones to ignore of each camera |
| `GET /api/v1/ai/cameras/<id>/frame` | same | the 64 x 36 grey frame of a camera (2304 bytes) |
| `POST /api/v1/ai/observations` | same | the report: what it saw, the severity and the reasons |
| `python -m armor_server_ai.service [--once]` | - | the observation service; `--once` makes one pass and ends |
| `python -m armor_server_ai.cli [--radar-tracks N]` | - | JSON lines on standard input (`{"label", "confidence", "lux", "radar_tracks"}`), one numbered and explained decision per line |

A decision is `{severity: ignore | review | high, reasons, authorizes_action: false}`. Labels: `person`, `vehicle`, `animal`, `unknown`, `motion`. **Fusion:** `high` is a person with confidence of 0.80 or more and at least one radar track, or strong movement and a radar track that agree; `review` is a confident detection (0.55 in daylight, 0.45 in low light) or a radar track with nothing seen; simple movement counts a radar track only with 30 % of certainty (about 3 % of the picture).

## ⚙️ Configuration

| Setting | Default | What it does |
|---|---|---|
| `ARMOR_AI_TOKEN` | yes (24+ characters) | the token the server gave the service |
| `ARMOR_AI_SERVER_URL` | http://127.0.0.1:18080 | the server; `https://` or this same machine |
| `ARMOR_AI_INTERVAL_S` | 3 (1-60) | seconds between passes; with many cameras the pass is spaced out to stay under 200 frames a minute |
| `ARMOR_AI_CONFIRM_FRAMES` | 2 (1-20) | frames in a row that must show movement before it is told |
| `ARMOR_AI_COOLDOWN_S` | 60 (0-3600) | seconds before the same camera is told again |

A value out of range stops the service with `<NAME> must be between a and b`. The thresholds of the decision (0.80, 0.55, 0.45, the radar bar of 30 %) and of the movement (18, 1 %, 60 %) are constants of the code described in [docs/INFERENCE_BOUNDARY.md](docs/INFERENCE_BOUNDARY.md); the settings of the service are in [docs/SERVICE.md](docs/SERVICE.md).

## 🚀 Quick start

**Requirements:** Python 3.11+ (standard library only). Optional: a Jetson Orin NX with TensorRT engines (not proven).

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests                                                                      # 130 tests
echo '{"label":"person","confidence":0.9,"lux":4,"radar_tracks":1}' | python -m armor_server_ai.cli       # one decision from a line
python -m armor_server_ai.cli --daily-summary day.jsonl --summary-config docs/daily_summary.example.json  # refuses until the settings say enabled; then the summary of a day
python -m armor_server_ai.service --once                                                                  # one pass of the observation service
```

See the [inference boundary](docs/INFERENCE_BOUNDARY.md) and the [service](docs/SERVICE.md).

## 🧪 Testing

```powershell
python -m unittest discover -s tests  # 130 tests
python -I tools/armor_ci_validate.py
```

| Test file | Tests | What it covers |
|---|---|---|
| `test_service.py` | 16 | movement, the watcher, cooldown and which radars count |
| `test_service_http.py` | 21 | the link to the server, the address rules, the passes and the settings |
| `test_vision_profile.py` | 20 | day and night with hysteresis, the fusion policy and the worker |
| `test_cli_worker.py` | 10 | the JSON-lines worker and its bad lines |
| `test_characterization_cli.py` | 9 | the worker and the service as they were before the daily summary |
| `test_daily_summary.py` | 41 | the daily summary: strict input, counts that add up, determinism, patterns with evidence, the eight languages, redaction and the AI switch |
| `test_ignore_zones.py`, `test_registry.py` | 13 | zones to ignore, and the checked TensorRT engines |

GitHub Actions runs the A.R.M.O.R. baseline on every push and pull request: the validation of the manifest, version, changelog and README parity, then the project's own build and tests. The sources pass the type checker: `python -m mypy src` reports nothing.

## 🏗️ Build & Release

It is plain Python: nothing to compile. The version lives in `pyproject.toml`, in `armor.project.json` and in the README badge (read from the manifest); each version has its entry in [CHANGELOG.md](CHANGELOG.md). Releases are published on GitHub.

## 🩺 Troubleshooting

| You see | Because | Do |
|---|---|---|
| `armor-ai: watching, every N s` | the service started | nothing to do |
| `ARMOR_AI_TOKEN (at least 24 characters) is needed` | the token is missing or short | set a token of 24+ characters, the same one the server has |
| `ARMOR_AI_SERVER_URL must be https://...` | the address would send the token in clear over a network | use `https://`, or `http://127.0.0.1` on the same machine |
| `armor-ai: the observation of <camera> could not be told (<code>)` | the report did not reach the server (`unreachable`, `unauthorized`...) | fix the cause; the next movement is told without waiting for the cooldown; `armor-ai: the server answers again` says when it is over |
| `radar and light sensors not counted: the site design lists no nodes for this camera` | the camera names no nodes in the site design | in the Site Designer of Studio, list the radar nodes that cover the camera |

## 📂 Repository Structure

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of ARMOR-SERVER-AI" width="100%">
</p>

<details>
<summary>Text version of the tree</summary>

```text
ARMOR-SERVER-AI/
├── src/armor_server_ai/
│   ├── service.py                 the observation service: one pass per interval
│   ├── motion.py                  grey frame, zones to ignore, movement share
│   ├── profile.py                 day or low light, with hysteresis
│   ├── policy.py                  fusion: ignore, review, high
│   ├── engine_registry.py         TensorRT engines checked by SHA-256
│   ├── cli.py                     the JSON-lines worker
│   ├── daily.py                   the daily summary command and report
│   ├── daily_events.py            strict reading of the events of a day
│   ├── daily_summary.py           counts, serious alarms and explainable patterns
│   ├── daily_text.py              the text in eight languages, from templates
│   ├── daily_ai.py                the optional note of a provider, off by default
│   ├── daily_config.py            the settings file, strict
│   └── redact.py                  names, addresses and credentials removed
├── tests/                         130 tests: motion, policy, service, worker, daily summary
├── docs/                          INFERENCE_BOUNDARY.md, SERVICE.md, DAILY_SUMMARY.md
├── tools/                         the shared CI checks and project tooling
├── images/                        banner, icon and the pictures of the README
├── .github/                       CI workflow, dashboard notice, issue and pull-request templates
├── armor.project.json             manifest: version, role, maturity
├── pyproject.toml                 package metadata, entry points
├── CHANGELOG.md                   what changed in each version
├── run.sh run.bat                 start, shared workflow
├── build.sh build.bat             build and test, shared workflow
├── build-test.sh build-test.bat   build, test and package
├── test.sh test.bat               only the tests, never the version
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE
```

</details>

## 🗺️ Roadmap & Known limits

**Known limits today**

* There is no detection model: it cannot tell a person from a cat or a branch.
* Nothing has run on a Jetson, with TensorRT or on a decoded RTSP stream there.
* No independent security review.

**Next**

* A model that recognises a person, run on a Jetson Orin NX, using the zones, masks and rules of ARMOR-VISION.

## 🌍 Languages

README and texts exist in English, Spanish, French, Italian, German, Chinese, Japanese and European Portuguese.

## 🔗 Related Projects

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) is a perimeter-security system made of independent repositories. Each one has its own version, its own tests and its own README; this is the family:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Message contracts, validators, conformance vectors and generated types
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - Field-node firmware for ESP32-S3 with three radars and its own web panel
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - Solar inverter and battery protocols and the messages of a gateway node
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - Electrical node: meters, the message of the network's readings and the rules for switching
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - Alarm node and panel: zones, arming, delays, siren and PIN, with the server or without it
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - Touch panel: the state of the system on a wall screen, arming and acknowledging, and the home of the voice assistant
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - The local network: its devices, the internet and what changes
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Central coordinator: telemetry, alarms, devices, solar readings and cameras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Web console: cameras, radar, alarms, solar energy and the 2D/3D site designer
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Android operator client with a live 2D/3D radar
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - iPhone operator client
* **ARMOR-SERVER-AI** (this repository) - Visual inference policy that explains its decisions and never actuates
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Camera zones, masks and detection rules for the Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Offline voice intents with a confirmation that cannot be forged
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Enclosures, electronics and the bench acceptance matrix
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Deployment, the CM5 test bench, backup and TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Offline telemetry simulator with repeatable faults
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - Detects, installs and updates the ecosystem's own repositories
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Architecture, security baseline and the capability matrix

## 📚 Documentation

* [Inference boundary](docs/INFERENCE_BOUNDARY.md): what is decided here and what is left to a model
* [The daily summary](docs/DAILY_SUMMARY.md): the events of a day, the patterns and the optional AI note, off by default
* [The service](docs/SERVICE.md): the observation service and its settings
* [Capability matrix: what is proven and what is not](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Project catalogue: versions and how the repositories depend on each other](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Changelog of this repository](CHANGELOG.md)

## 🤝 Contributing & Community

* Before a pull request run `python -I tools/armor_ci_validate.py` and the tests: both must pass. See [CONTRIBUTING.md](CONTRIBUTING.md) and the [code of conduct](CODE_OF_CONDUCT.md).
* The README exists in eight languages and is generated from the sources in ARMOR-DOCS: a change to the text is made there.
* A change to a message between components starts in ARMOR-COMMON.
* Do not describe as working on a board what has only been built.
* Report a vulnerability privately: [SECURITY.md](SECURITY.md). Questions, ideas and reports: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTHOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENSE

GPL-3.0-or-later - see [LICENSE](LICENSE).
