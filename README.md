<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-SERVER-AI banner" width="100%">
</p>

# 👁️ ARMOR-SERVER-AI

<p align="center">🇺🇸 <b>English</b> | <a href="README_spa.md">🇪🇸 Español</a></p>

### Visual inference policy: decides and explains, never actuates

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Target-Jetson%20Orin%20NX-76b900.svg" alt="Target">
  <img src="https://img.shields.io/badge/Maturity-functional%20baseline-00E5FF.svg" alt="Maturity">
</p>

---

**Honesty check - what runs today:** The decision layer is real and tested (26 tests). **Nothing here runs a camera, RTSP or TensorRT yet**: that needs the Jetson, and it is not proven.

---

## 1. 🛠️ OVERVIEW

* **Day/night profile with hysteresis:** low-light below 30 lux, back to daylight only above 60 lux and never twice within 30 s, so dusk cannot make it flap.
* **Explainable fusion:** each detection and the radar tracks give a severity (`ignore`, `review`, `high`) with the reasons behind it. A person seen at 80 % or more **and** a radar track is `high`; low light lowers only the review bar; a detection older than 10 s is ignored.
* **Recommendations only:** a decision always carries `authorizes_action = false`. The central server authenticates and authorises every action.
* **Checksum-verified engines:** pre-built TensorRT engines are accepted only if present, non-empty and, with an `engines.json`, matching their SHA-256. Nothing is compiled or downloaded.
* **JSONL worker:** numbered, explained results; a bad line reports its number and never stops the stream.

---

## 2. 🔧 BUILD & RUN

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests
echo '{"label":"person","confidence":0.9,"lux":4,"radar_tracks":1}' | python -m armor_server_ai.cli
```

See the [inference boundary](docs/INFERENCE_BOUNDARY.md).

---

## 📂 DIRECTORY STRUCTURE

```text
ARMOR-SERVER-AI/
├── src/armor_server_ai/   profile, policy, engine_registry, cli
├── tests/
└── docs/INFERENCE_BOUNDARY.md
```

---

## 👤 AUTHOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENSE

GPL-3.0-or-later - see [LICENSE](LICENSE).
