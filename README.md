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
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Target-Jetson%20Orin%20NX-76b900.svg" alt="Target">
  <img src="https://img.shields.io/badge/Tests-80%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.2.7-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**Honesty check - what runs today:** The decision layer and the movement detector are real and tested (80 tests), and the observation service **runs on the CM5 test bench**: while the system is armed it looks at tiny grey frames of the real IP cameras and reports movement weighed with the radars. It cannot tell a person from a cat or a branch: **there is no detection model yet**, and nothing has run on the Jetson, TensorRT or an RTSP stream decoded there.

---

## 📋 At a glance

| | |
|---|---|
| Version | `0.2.7` |
| Maturity | Established |
| Tests | 80 (`python -m unittest discover -s tests`) |
| Stack | Python 3.11+ (standard library) |
| On real hardware | Running as a service on the CM5 test bench with the real IP cameras (movement only); nothing on a Jetson |

## 🚦 Project status

Each line is one part of this repository and the light says how far it is today. It is written from what the repository can show (tests, builds, runs), not from what is planned.

🟢 Done and verified · 🟡 Works, with known limits · 🟠 Partly done or not verified yet · 🔴 Not done or not working

| Area | State | What it means here |
|---|---|---|
| Software | 🟡 | The movement detector and the decision layer run as a service on the CM5 test bench, but there is no detection model yet: it cannot tell a person from a cat or a branch. |
| Tests | 🟢 | 80 tests pass (`python -m unittest discover -s tests`). |
| Hardware | 🟡 | While the system is armed it looks at tiny grey frames of the real IP cameras of the CM5 test bench; nothing has run on a Jetson, with TensorRT or on a decoded RTSP stream. |
| Integration | 🟡 | It reports movement weighed with the radars to the server of the CM5 test bench. |
| Documentation | 🟢 | Eight languages and the changelog are up to date. |

## 🎯 Overview

* **The observation service:** `python -m armor_server_ai.service` is never called by the server (it asks the server, with its own token): while the system is **armed** it takes one tiny grey frame (64 x 36, from the camera's stream, never stored) of each camera every few seconds, measures how much of the picture moved and, when radar tracks agree, reports it to ARMOR-SERVER with its token.
* **Zones of the picture to ignore:** the server hands it the ignore zones of each camera and the pixels inside them count for nothing (a tree that waves, a road); a picture that is almost all ignored is not judged and at most sixteen zones count.
* **Day/night profile with hysteresis:** low-light below 30 lux, back to daylight only above 60 lux and never twice within 30 s, so dusk cannot make it flap.
* **Explainable fusion:** each detection or movement and the radar tracks give a severity (`ignore`, `review`, `high`) with the reasons behind it; strong movement **and** a radar track agree is `high`, weaker movement is a `review`.
* **Recommendations only:** a decision always carries `authorizes_action = false`. The central server authenticates and authorises every action.
* **Checksum-verified engines:** pre-built TensorRT engines are accepted only if present, non-empty and, with an `engines.json`, matching their SHA-256. Nothing is compiled or downloaded.
* **A service that says what is wrong:** it reports every new problem when it changes (`unreachable`, `unauthorized`…) and *the server answers again* when it is over; a JSONL worker keeps numbered, explained results and a bad line never stops the stream.

## 🧩 Role in A.R.M.O.R.

ARMOR-SERVER-AI is the part that watches the cameras for movement while the house is armed. It never acts: it tells [ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER) what it saw and why (movement and radar tracks agreeing is `high`), and the server decides what to do. A model that recognises a person, run on a Jetson, is the next step; [ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION) holds the zones, masks and rules that model will use.

## 📂 Repository Structure

```text
ARMOR-SERVER-AI/
├── src/armor_server_ai/   profile (day/night), policy (fusion), motion (movement and ignore zones), engine_registry, service (the observation service), cli
├── tests/                 80 tests
├── tools/                 the shared CI checks (armor_ci_validate.py, armor_project_tool.py, _armor_readme_parity.py)
└── docs/                  INFERENCE_BOUNDARY.md, SERVICE.md
```

## 🛠️ Development Environment

**Requirements:** Python 3.11+, optional: a Jetson Orin NX with TensorRT engines (not proven)

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests   # 80 tests
echo '{"label":"person","confidence":0.9,"lux":4,"radar_tracks":1}' | python -m armor_server_ai.cli
python -m armor_server_ai.service --once   # one pass of the observation service
```

See the [inference boundary](docs/INFERENCE_BOUNDARY.md) and the [service](docs/SERVICE.md).

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

## 📚 Documentation & Community

Where to read more:

* [Capability matrix: what is proven and what is not](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Project catalogue: versions and how the repositories depend on each other](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Changelog of this repository](CHANGELOG.md)
* [License (GPL-3.0-or-later)](LICENSE)
* Questions, ideas and reports: electrohobby3d@gmail.com

## 👤 AUTHOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENSE

GPL-3.0-or-later - see [LICENSE](LICENSE).
