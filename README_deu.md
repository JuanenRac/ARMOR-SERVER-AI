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
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### Beobachtungsdienst: Bewegung auf den Kameras, gegen die Radare abgewogen; er entscheidet und erklärt, schaltet nie

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Target-Jetson%20Orin%20NX-76b900.svg" alt="Target">
  <img src="https://img.shields.io/badge/Tests-80%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.2.7-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**Ehrlichkeitsprüfung - was heute läuft:** Die Entscheidungsschicht und der Bewegungsdetektor sind real und getestet (80 Tests), und der Beobachtungsdienst **läuft am CM5-Testaufbau**: Bei scharfem System sieht er winzige Graubilder der echten IP-Kameras an und meldet Bewegung, gegen die Radare abgewogen. Er kann eine Person nicht von einer Katze oder einem Ast unterscheiden: **Es gibt noch kein Erkennungsmodell**, und nichts lief auf dem Jetson, mit TensorRT oder einem dort dekodierten RTSP-Strom.

---

## 📋 Auf einen Blick

| | |
|---|---|
| Version | `0.2.7` |
| Reifegrad | Etabliert |
| Tests | 80 (`python -m unittest discover -s tests`) |
| Technik | Python 3.11+ (standard library) |
| Auf echter Hardware | Läuft als Dienst am CM5-Testaufbau mit den echten IP-Kameras (nur Bewegung); nichts auf einem Jetson |

## 🚦 Projektstatus

Jede Zeile ist ein Teil dieses Repositorys, und die Ampel sagt, wie weit er heute ist. Sie beruht auf dem, was das Repository zeigen kann (Tests, Builds, Läufe), nicht auf dem, was geplant ist.

🟢 Fertig und überprüft · 🟡 Funktioniert, mit bekannten Grenzen · 🟠 Teilweise fertig oder noch nicht überprüft · 🔴 Nicht gemacht oder funktioniert nicht

| Bereich | Stand | Was das hier bedeutet |
|---|---|---|
| Software | 🟡 | Der Bewegungsmelder und die Entscheidungsschicht laufen als Dienst auf dem CM5-Prüfstand, aber es gibt noch kein Erkennungsmodell: Er unterscheidet keine Person von einer Katze oder einem Ast. |
| Tests | 🟢 | 80 Tests bestehen (`python -m unittest discover -s tests`). |
| Hardware | 🟡 | Solange das System scharf ist, betrachtet er winzige Graubilder der echten IP-Kameras des CM5-Prüfstands; nichts lief auf einem Jetson, mit TensorRT oder auf einem dekodierten RTSP-Strom. |
| Integration | 🟡 | Er meldet die mit den Radaren gewichtete Bewegung an den Server des Prüfstands. |
| Dokumentation | 🟢 | Acht Sprachen und das Änderungsprotokoll sind aktuell. |

## 🎯 Überblick

* **Der Beobachtungsdienst:** `python -m armor_server_ai.service` wird nie vom Server aufgerufen (er fragt den Server, mit seinem eigenen Token): Bei **scharfem** System nimmt er alle paar Sekunden ein winziges Graubild (64 x 36, aus dem Kamerastrom, nie gespeichert) jeder Kamera auf, misst, wie viel vom Bild sich bewegt hat, und meldet es, wenn Radarspuren übereinstimmen, mit seinem Token an ARMOR-SERVER.
* **Zu ignorierende Bildzonen:** der Server gibt ihm die zu ignorierenden Zonen jeder Kamera, und die Pixel darin zählen nicht (ein wehender Baum, eine Straße); ein fast ganz ignoriertes Bild wird nicht beurteilt, und höchstens sechzehn Zonen zählen.
* **Tag/Nacht-Profil mit Hysterese:** Dunkelheit unter 30 Lux, zurück zu Tageslicht erst über 60 Lux und nie zweimal innerhalb von 30 s, damit die Dämmerung es nicht flattern lässt.
* **Erklärbare Fusion:** jede Erkennung oder Bewegung und die Radarspuren ergeben eine Stufe (`ignore`, `review`, `high`) mit den Gründen; starke Bewegung **und** eine übereinstimmende Radarspur ist `high`, schwächere Bewegung ist `review`.
* **Nur Empfehlungen:** eine Entscheidung trägt immer `authorizes_action = false`. Der zentrale Server authentifiziert und autorisiert jede Aktion.
* **Per Prüfsumme verifizierte Engines:** vorgebaute TensorRT-Engines werden nur akzeptiert, wenn sie vorhanden, nicht leer und, mit einer `engines.json`, passend zu ihrem SHA-256 sind. Nichts wird kompiliert oder heruntergeladen.
* **Ein Dienst, der sagt, was falsch ist:** er meldet jedes neue Problem, wenn es sich ändert (`unreachable`, `unauthorized`…), und *der Server antwortet wieder*, wenn es vorbei ist; ein JSONL-Worker liefert nummerierte, erklärte Ergebnisse, und eine fehlerhafte Zeile stoppt nie den Strom.

## 🧩 Rolle in A.R.M.O.R.

ARMOR-SERVER-AI ist der Teil, der die Kameras auf Bewegung beobachtet, solange das Haus scharf ist. Er handelt nie: Er sagt [ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER), was er gesehen hat und warum (übereinstimmende Bewegung und Radarspuren ergeben `high`), und der Server entscheidet, was zu tun ist. Ein Modell, das eine Person erkennt, auf einem Jetson ausgeführt, ist der nächste Schritt; [ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION) hält die Zonen, Masken und Regeln, die dieses Modell nutzen wird.

## 📂 Struktur des Repositorys

```text
ARMOR-SERVER-AI/
├── src/armor_server_ai/   profile (day/night), policy (fusion), motion (movement and ignore zones), engine_registry, service (the observation service), cli
├── tests/                 80 tests
└── docs/                  INFERENCE_BOUNDARY.md, SERVICE.md
```

## 🛠️ Entwicklungsumgebung

**Voraussetzungen:** Python 3.11+, optional: ein Jetson Orin NX mit TensorRT-Engines (nicht erprobt)

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests   # 80 tests
echo '{"label":"person","confidence":0.9,"lux":4,"radar_tracks":1}' | python -m armor_server_ai.cli
python -m armor_server_ai.service --once   # one pass of the observation service
```

Siehe die [Inferenzgrenze](docs/INFERENCE_BOUNDARY.md) und den [Dienst](docs/SERVICE.md).

## 🔗 Verwandte Projekte

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) ist ein Perimeter-Sicherheitssystem aus unabhängigen Repositorys. Jedes hat eine eigene Version, eigene Tests und ein eigenes README; hier ist die Familie:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Nachrichtenverträge, Validierer, Konformitätsvektoren und generierte Typen
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - Feldknoten-Firmware für ESP32-S3 mit drei Radaren und eigenem Web-Panel
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - Protokolle für Solar-Wechselrichter und -Batterien und die Nachrichten eines Gateway-Knotens
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - Elektroknoten: Zähler, die Nachricht der Netzmesswerte und die Regeln fürs Schalten
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - Alarmknoten und Alarmzentrale: Zonen, Scharfschalten, Verzögerungen, Sirene und PIN, mit dem Server oder ohne ihn
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - Touch-Panel: der Systemzustand auf einem Wandbildschirm, Scharf- und Quittieren sowie das Zuhause des Sprachassistenten
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - Das lokale Netzwerk: seine Geräte, das Internet und was sich ändert
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Zentraler Koordinator: Telemetrie, Alarme, Geräte, Solarmesswerte und Kameras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Web-Konsole: Kameras, Radar, Alarme, Solarenergie und 2D/3D-Standortdesigner
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Android-Bedienclient mit Live-Radar in 2D/3D
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - iPhone-Bedienclient
* **ARMOR-SERVER-AI** (dieses Repository) - Visuelle Inferenzrichtlinie, die ihre Entscheidungen erklärt und nie handelt
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Kamerazonen, Masken und Erkennungsregeln für den Jetson Orin NX
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
