<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-SERVER-AI banner" width="100%">
</p>

# 👁️ ARMOR-SERVER-AI

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  🇩🇪 <b>Deutsch</b> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a>
</p>

### Visuelle Inferenzrichtlinie: entscheidet und erklärt, handelt nie

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Target-Jetson%20Orin%20NX-76b900.svg" alt="Target">
  <img src="https://img.shields.io/badge/Maturity-functional%20baseline-00E5FF.svg" alt="Maturity">
</p>

---

**Ehrlichkeitsprüfung - was heute läuft:** Die Entscheidungsschicht ist real und getestet (35 Tests). **Hier läuft noch kein neuronaler Detektor und kein TensorRT** (dafür braucht es den Jetson, und das ist nicht belegt): der beobachtende Dienst vergleicht nur Bilder, um Bewegung zu erkennen, auf der CM5, und wurde nicht mit einem echten Alarm erprobt.

---

## 🎯 Überblick

* **Tag/Nacht-Profil mit Hysterese:** Schwachlicht unter 30 Lux, zurück zum Tag nur über 60 Lux und nie zweimal innerhalb von 30 s, damit die Dämmerung es nicht flattern lässt.
* **Erklärbare Fusion:** jede Erkennung und die Radarspuren ergeben einen Schweregrad (`ignore`, `review`, `high`) samt Gründen. Eine Person mit 80 % oder mehr **und** eine Radarspur ergeben `high`; Schwachlicht senkt nur die Prüfschwelle; eine Erkennung, die älter als 10 s ist, wird ignoriert.
* **Nur Empfehlungen:** eine Entscheidung trägt immer `authorizes_action = false`. Der zentrale Server authentifiziert und autorisiert jede Aktion.
* **Prüfsummengeprüfte Engines:** vorgebaute TensorRT-Engines werden nur akzeptiert, wenn sie vorhanden und nicht leer sind und mit einer `engines.json` ihrem SHA-256 entsprechen. Nichts wird kompiliert oder heruntergeladen.
* **JSONL-Worker:** nummerierte, erklärte Ergebnisse; eine fehlerhafte Zeile meldet ihre Nummer und stoppt den Strom nie.
* **Ein beobachtender Dienst:** `armor-server-ai` sieht alle paar Sekunden die Kameras an, die der Server auflistet (graue 64x36-Bilder über ffmpeg), und fragt bei Bewegung die Richtlinie; bei scharfem System löst er einen Alarm `camera_motion` aus. Er spricht mit einem eigenen Token mit dem Server und meldet im Log, wann sich sein Problem ändert und wann es vorbei ist; siehe [der Dienst](docs/SERVICE.md).

## 📂 Struktur des Repositorys

```text
ARMOR-SERVER-AI/
├── src/armor_server_ai/   profile, policy, motion, service, engine_registry, cli
├── tests/
└── docs/INFERENCE_BOUNDARY.md, SERVICE.md
```

## 🛠️ Entwicklungsumgebung

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests
echo '{"label":"person","confidence":0.9,"lux":4,"radar_tracks":1}' | python -m armor_server_ai.cli
```

Siehe die [Inferenzgrenze](docs/INFERENCE_BOUNDARY.md).

## 🔗 Verwandte Projekte

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) ist ein Perimeter-Sicherheitssystem aus unabhängigen Repositorys. Jedes hat eine eigene Version, eigene Tests und ein eigenes README; hier ist die Familie:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Nachrichtenverträge, Validierer, Konformitätsvektoren und generierte Typen
* **[ARMOR-RADAR](https://github.com/JuanenRac/ARMOR-RADAR)** - Feldknoten-Firmware für ESP32-S3 mit drei Radaren und eigenem Web-Panel
* **[ARMOR-SOLAR](https://github.com/JuanenRac/ARMOR-SOLAR)** - Protokolle für Solar-Wechselrichter und -Batterien und die Nachrichten eines Gateway-Knotens
* **[ARMOR-ELECTRICAL](https://github.com/JuanenRac/ARMOR-ELECTRICAL)** - Elektroknoten: Zähler, die Nachricht der Netzmesswerte und die Regeln fürs Schalten
* **[ARMOR-HMI](https://github.com/JuanenRac/ARMOR-HMI)** - Touch-Panel: der Systemzustand auf einem Wandbildschirm, Scharf- und Quittieren sowie das Zuhause des Sprachassistenten
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - Das lokale Netzwerk: seine Geräte, das Internet und was sich ändert
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Zentraler Koordinator: Telemetrie, Alarme, Geräte, Solarmesswerte und Kameras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Web-Konsole: Kameras, Radar, Alarme, Solarenergie und 2D/3D-Standortdesigner
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Android-Bedienclient mit Live-Radar in 2D/3D
* **ARMOR-SERVER-AI** (dieses Repository) - Visuelle Inferenzrichtlinie, die ihre Entscheidungen erklärt und nie handelt
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Offline-Sprachabsichten mit einer nicht fälschbaren Bestätigung
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Gehäuse, Elektronik und die Abnahmematrix am Prüfstand
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Bereitstellung, CM5-Prüfstand, Backup und TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Offline-Telemetriesimulator mit wiederholbaren Fehlern
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - Erkennt, installiert und aktualisiert die eigenen Repositories des Ökosystems
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Architektur, Sicherheitsgrundlage und die Fähigkeitsmatrix

## 📚 Dokumentation und Community

Hier gibt es mehr zu lesen:

* [Fähigkeitsmatrix: was belegt ist und was nicht](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Projektkatalog: Versionen und wie die Repositorys voneinander abhängen](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Änderungsverlauf dieses Repositorys](CHANGELOG.md)
* [Lizenz (GPL-3.0-or-later)](LICENSE)
* Fragen, Ideen und Meldungen: electrohobby3d@gmail.com

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LIZENZ

GPL-3.0-or-later - siehe [LICENSE](LICENSE).
