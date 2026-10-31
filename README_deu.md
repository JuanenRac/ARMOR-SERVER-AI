<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-SERVER-AI-Banner" width="100%">
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
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 oder neuer">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Sprache">
  <img src="https://img.shields.io/badge/Target-Jetson%20Orin%20NX-76b900.svg" alt="Target">
  <img src="https://img.shields.io/badge/Tests-80%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.2.8-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Reifegrad">
</p>

---

**Ehrlichkeitsprüfung - was heute läuft:** Die Entscheidungsschicht und der Bewegungsdetektor sind real und getestet (80 Tests), und der Beobachtungsdienst **läuft am CM5-Testaufbau**: Bei scharfem System sieht er winzige Graubilder der echten IP-Kameras an und meldet Bewegung, gegen die Radare abgewogen. Er kann eine Person nicht von einer Katze oder einem Ast unterscheiden: **Es gibt noch kein Erkennungsmodell**, und nichts lief auf dem Jetson, mit TensorRT oder einem dort dekodierten RTSP-Strom.

---

## 📋 Auf einen Blick

| | |
|---|---|
| Version | `0.2.8` |
| Reifegrad | Etabliert |
| Rolle | Beobachtungsdienst: Bewegung, mit den Radaren gewichtet, nur Empfehlungen |
| Technik | Python 3.11+, nur Standardbibliothek |
| Tests | 80 (`python -m unittest discover -s tests`) |
| Vertrag | Client von ARMOR-SERVER: 3 Routen unter `/api/v1/ai/`; er wird nie aufgerufen |
| Läuft auf | Der CM5-Prüfstand (als Dienst, siehe ARMOR-DEVOPS) oder jeder Computer |
| Auf echter Hardware | Läuft als Dienst am CM5-Testaufbau mit den echten IP-Kameras (nur Bewegung); nichts auf einem Jetson |
| Lizenz | GPL-3.0-or-later |

**Springe zu:** [Überblick](#-überblick) · [Architektur](#-architektur) · [Sicherheit](#-sicherheit-und-schutz) · [Schnittstellen](#-schnittstellen) · [Konfiguration](#-konfiguration) · [Schnellstart](#-schnellstart) · [Tests](#-tests) · [Probleme](#-fehlerbehebung) · [Struktur](#-struktur-des-repositorys) · [Verwandte](#-verwandte-projekte)

## 🚦 Projektstatus

Jede Zeile ist ein Teil dieses Repositorys, und die Ampel sagt, wie weit er heute ist. Sie beruht auf dem, was das Repository zeigen kann (Tests, Builds, Läufe), nicht auf dem, was geplant ist.

🟢 Fertig und überprüft · 🟡 Funktioniert, mit bekannten Grenzen · 🟠 Teilweise fertig oder noch nicht überprüft · 🔴 Nicht gemacht oder funktioniert nicht

| Bereich | Stand | Was das hier bedeutet |
|---|---|---|
| Software | 🟡 | Der Bewegungsmelder und die Entscheidungsschicht laufen als Dienst auf dem CM5-Prüfstand, aber es gibt noch kein Erkennungsmodell: Er unterscheidet keine Person von einer Katze oder einem Ast. |
| Tests | 🟢 | 80 Tests bestehen (`python -m unittest discover -s tests`). |
| Hardware | 🟡 | Solange das System scharf ist, betrachtet er winzige Graubilder der echten IP-Kameras des CM5-Prüfstands; nichts lief auf einem Jetson, mit TensorRT oder auf einem dekodierten RTSP-Strom. |
| Integration | 🟡 | Er meldet die mit den Radaren gewichtete Bewegung an den Server des Prüfstands. |
| Sicherheit | 🟡 | Der Dienst handelt nie (jede Entscheidung trägt `authorizes_action = false`), lehnt ein Token unter 24 Zeichen und eine Serveradresse ab, die nicht `https://` oder dieselbe Maschine ist, und speichert nie ein Bild; getestet, ohne unabhängige Prüfung. |
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

| Er spricht mit | Wie | Wozu |
|---|---|---|
| ARMOR-SERVER | er fragt den Server (`/api/v1/ai/*`, Token `ARMOR_AI_TOKEN`) | die Kameras, ihre Graubilder und die Ignorierzonen hinein; die Beobachtung hinaus |
| ARMOR-NODE-RADAR | über den Server | die Radarspuren und das Licht der Knoten, die jede Kamera abdecken |
| ARMOR-VISION | Regeln und Masken (nächster Schritt) | die Zonen, Masken und Regeln, die das Erkennungsmodell nutzen wird |
| ARMOR-DEVOPS | installiert ihn als Dienst | Bereitstellung auf dem CM5-Prüfstand |

## 🏛️ Architektur

<p align="center">
  <img src="images/architecture.svg" alt="ARMOR-SERVER-AI architecture: what it asks the server, the observation service with its modules, and what it tells" width="100%">
</p>

## 🔒 Sicherheit und Schutz

| Bedrohung | Abwehr |
|---|---|
| Der Dienst handelt eigenmächtig | Nie: jede Entscheidung trägt `authorizes_action = false`; der zentrale Server authentifiziert und autorisiert jede Aktion |
| Das Token läuft unverschlüsselt durchs Netz | `ARMOR_AI_SERVER_URL` muss `https://` sein oder `http://` zur selben Maschine (`127.0.0.1`, `localhost`); sonst startet der Dienst nicht |
| Ein schwaches Token | `ARMOR_AI_TOKEN` mit mindestens 24 Zeichen (der Server verlangt dasselbe) |
| Riesige Antworten des Servers | Der Kontext wird bis 1 000 000 Bytes gelesen, die Antwort auf eine Beobachtung bis 65 536; ein Bild hat genau 64 x 36 = 2304 Bytes |
| Gespeicherte Bilder | Das kleine Graubild wird nie gespeichert |
| Eine manipulierte TensorRT-Engine | Nur fertig gebaute Engines (`daylight`, `low_light`), die existieren, nicht leer sind und mit einer `engines.json` ihrem SHA-256 entsprechen; nichts wird kompiliert oder geladen |
| Ein Fehlalarm durch Lichtwechsel | Eine Änderung von über 60 % des Bildes ist Licht, keine Bewegung; unter 1 % ist keine Bewegung; Pixelschwelle 18; mindestens 64 gezählte Pixel; höchstens 16 Ignorierzonen, und ein fast ganz ignoriertes Bild wird nicht beurteilt |
| Tag/Nacht-Flackern; veraltete Daten; eine feindliche JSON-Zeile | Hysterese (wenig Licht unter 30 Lux, wieder Tag über 60 Lux, nie zweimal in 30 s, Lux bis 200 000); eine Beobachtung über 10 s löst nie einen Alarm aus; eine JSON-Zeile über 4096 Bytes wird abgelehnt, der Strom läuft weiter |

## 🔌 Schnittstellen

| Route | Authentifizierung | Was sie tut |
|---|---|---|
| `GET /api/v1/ai/context` | Token `ARMOR_AI_TOKEN` | die Häuser: Knoten und Kameras sowie die Ignorierzonen jeder Kamera |
| `GET /api/v1/ai/cameras/<id>/frame` | dasselbe | das 64 x 36 Graubild einer Kamera (2304 Bytes) |
| `POST /api/v1/ai/observations` | dasselbe | der Bericht: was sie sah, der Schweregrad und die Gründe |
| `python -m armor_server_ai.service [--once]` | - | der Beobachtungsdienst; `--once` macht einen Durchgang und endet |
| `python -m armor_server_ai.cli [--radar-tracks N]` | - | JSON-Zeilen auf der Standardeingabe (`{"label", "confidence", "lux", "radar_tracks"}`), je Zeile eine nummerierte, erklärte Entscheidung |

Eine Entscheidung ist `{severity: ignore | review | high, reasons, authorizes_action: false}`. Labels: `person`, `vehicle`, `animal`, `unknown`, `motion`. **Fusion:** `high` ist eine Person mit Konfidenz ab 0,80 und mindestens einer Radarspur oder starke Bewegung und eine übereinstimmende Radarspur; `review` ist eine sichere Erkennung (0,55 bei Tag, 0,45 bei wenig Licht) oder eine Radarspur ohne Sichtung; einfache Bewegung zählt eine Radarspur nur ab 30 % Sicherheit (etwa 3 % des Bildes).

## ⚙️ Konfiguration

| Einstellung | Standard | Was sie tut |
|---|---|---|
| `ARMOR_AI_TOKEN` | ja (24+ Zeichen) | das Token, das der Server dem Dienst gab |
| `ARMOR_AI_SERVER_URL` | http://127.0.0.1:18080 | der Server; `https://` oder dieselbe Maschine |
| `ARMOR_AI_INTERVAL_S` | 3 (1-60) | Sekunden zwischen Durchgängen; bei vielen Kameras wird der Durchgang gestreckt, um unter 200 Bildern pro Minute zu bleiben |
| `ARMOR_AI_CONFIRM_FRAMES` | 2 (1-20) | aufeinanderfolgende Bilder, die Bewegung zeigen müssen, bevor gemeldet wird |
| `ARMOR_AI_COOLDOWN_S` | 60 (0-3600) | Sekunden, bevor dieselbe Kamera erneut gemeldet wird |

Ein Wert außerhalb des Bereichs stoppt den Dienst mit `<NAME> must be between a and b`. Die Schwellen der Entscheidung (0,80, 0,55, 0,45, die Radarschwelle von 30 %) und der Bewegung (18, 1 %, 60 %) sind Konstanten im Code, beschrieben in [docs/INFERENCE_BOUNDARY.md](docs/INFERENCE_BOUNDARY.md); die Einstellungen des Dienstes stehen in [docs/SERVICE.md](docs/SERVICE.md).

## 🚀 Schnellstart

**Voraussetzungen:** Python 3.11+ (nur Standardbibliothek). Optional: ein Jetson Orin NX mit TensorRT-Engines (nicht erprobt).

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests                                                                 # 80 Tests
echo '{"label":"person","confidence":0.9,"lux":4,"radar_tracks":1}' | python -m armor_server_ai.cli  # eine Entscheidung aus einer Zeile
python -m armor_server_ai.service --once                                                             # ein Durchgang des Beobachtungsdienstes
```

Siehe die [Grenze der Inferenz](docs/INFERENCE_BOUNDARY.md) und den [Dienst](docs/SERVICE.md).

## 🧪 Tests

```powershell
python -m unittest discover -s tests  # 80 Tests
python -I tools/armor_ci_validate.py
```

| Testdatei | Tests | Was sie abdeckt |
|---|---|---|
| `test_service.py` | 16 | Bewegung, der Beobachter, Abkühlzeit und welche Radare zählen |
| `test_service_http.py` | 21 | die Verbindung zum Server, Adressregeln, Durchgänge und Einstellungen |
| `test_vision_profile.py` | 20 | Tag und Nacht mit Hysterese, die Fusionsrichtlinie und der Arbeiter |
| `test_cli_worker.py` | 10 | der JSON-Lines-Arbeiter und seine fehlerhaften Zeilen |
| `test_ignore_zones.py`, `test_registry.py` | 13 | Ignorierzonen und geprüfte TensorRT-Engines |

GitHub Actions führt bei jedem Push und Pull Request die A.R.M.O.R.-Basis aus: die Prüfung von Manifest, Version, Änderungsprotokoll und README-Parität, dann den eigenen Build und die eigenen Tests des Projekts. Die Quellen bestehen die Typprüfung: `python -m mypy src` meldet nichts.

## 🏗️ Build und Veröffentlichung

Es ist reines Python: Es gibt nichts zu kompilieren. Die Version steht in `pyproject.toml`, in `armor.project.json` und im README-Badge (aus dem Manifest gelesen); jede Version hat ihren Eintrag in [CHANGELOG.md](CHANGELOG.md). Releases werden auf GitHub veröffentlicht.

## 🩺 Fehlerbehebung

| Du siehst | Weil | Tu |
|---|---|---|
| `armor-ai: watching, every N s` | der Dienst ist gestartet | nichts zu tun |
| `ARMOR_AI_TOKEN (at least 24 characters) is needed` | das Token fehlt oder ist kurz | ein Token mit 24+ Zeichen setzen, dasselbe wie am Server |
| `ARMOR_AI_SERVER_URL must be https://...` | die Adresse würde das Token unverschlüsselt durchs Netz senden | `https://` verwenden oder `http://127.0.0.1` auf derselben Maschine |
| `armor-ai: the observation of <camera> could not be told (<code>)` | der Bericht erreichte den Server nicht (`unreachable`, `unauthorized`...) | die Ursache beheben; die nächste Bewegung wird ohne Abkühlzeit gemeldet; `armor-ai: the server answers again` meldet das Ende |
| `radar and light sensors not counted: the site design lists no nodes for this camera` | die Kamera nennt im Standortentwurf keine Knoten | im Standort-Designer von Studio die Radar-Knoten eintragen, die die Kamera abdecken |

## 📂 Struktur des Repositorys

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of ARMOR-SERVER-AI" width="100%">
</p>

<details>
<summary>Textversion des Baums</summary>

```text
ARMOR-SERVER-AI/
├── src/armor_server_ai/
│   ├── service.py                 der Beobachtungsdienst: ein Durchgang je Intervall
│   ├── motion.py                  Graubild, Ignorierzonen, Bewegungsanteil
│   ├── profile.py                 Tag oder wenig Licht, mit Hysterese
│   ├── policy.py                  Fusion: ignore, review, high
│   ├── engine_registry.py         TensorRT-Engines per SHA-256 geprüft
│   └── cli.py                     der JSON-Lines-Arbeiter
├── tests/                         80 Tests: Bewegung, Richtlinie, Dienst, Arbeiter
├── docs/                          INFERENCE_BOUNDARY.md, SERVICE.md
├── tools/                         die gemeinsamen CI-Prüfungen und Werkzeuge
├── images/                        Banner, Symbol und die Bilder des READMEs
├── .github/                       CI-Workflow, Dashboard-Hinweis, Vorlagen für Issues und Pull Requests
├── armor.project.json             Manifest: Version, Rolle, Reife
├── pyproject.toml                 Paket-Metadaten, Einstiege
├── CHANGELOG.md                   was sich in jeder Version geändert hat
├── run.sh run.bat                 Start, gemeinsamer Ablauf
├── build.sh build.bat             Bauen und Testen, gemeinsamer Ablauf
├── build-test.sh build-test.bat   Bauen, Testen und Verpacken
├── test.sh test.bat               nur die Tests, nie die Version
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE
```

</details>

## 🗺️ Roadmap und bekannte Grenzen

**Bekannte Grenzen heute**

* Es gibt kein Erkennungsmodell: Es kann eine Person nicht von einer Katze oder einem Ast unterscheiden.
* Nichts lief auf einem Jetson, mit TensorRT oder auf einem dort dekodierten RTSP-Strom.
* Keine unabhängige Sicherheitsprüfung.

**Als Nächstes**

* Ein Modell, das eine Person erkennt, auf einem Jetson Orin NX mit den Zonen, Masken und Regeln von ARMOR-VISION.

## 🌍 Sprachen

README und Texte gibt es auf Englisch, Spanisch, Französisch, Italienisch, Deutsch, Chinesisch, Japanisch und europäischem Portugiesisch.

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
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - Erkennt, installiert und aktualisiert die eigenen Repositorys des Ökosystems
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Architektur, Sicherheitsgrundlage und die Fähigkeitsmatrix

## 📚 Dokumentation

* [Grenze der Inferenz](docs/INFERENCE_BOUNDARY.md): was hier entschieden wird und was einem Modell bleibt
* [Der Dienst](docs/SERVICE.md): der Beobachtungsdienst und seine Einstellungen
* [Fähigkeitsmatrix: was belegt ist und was nicht](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Projektkatalog: Versionen und wie die Repositorys voneinander abhängen](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Änderungsverlauf dieses Repositorys](CHANGELOG.md)

## 🤝 Mitwirken und Community

* Führe vor einem Pull Request `python -I tools/armor_ci_validate.py` und die Tests aus: Beide müssen bestehen. Siehe [CONTRIBUTING.md](CONTRIBUTING.md) und den [Verhaltenskodex](CODE_OF_CONDUCT.md).
* Das README gibt es in acht Sprachen, und es wird aus den Quellen in ARMOR-DOCS erzeugt: Eine Textänderung erfolgt dort.
* Eine Änderung an einer Nachricht zwischen Komponenten beginnt in ARMOR-COMMON.
* Beschreibe nichts als auf einer Platine funktionierend, was nur gebaut wurde.
* Melde eine Schwachstelle privat: [SECURITY.md](SECURITY.md). Fragen, Ideen und Meldungen: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LIZENZ

GPL-3.0-or-later - siehe [LICENSE](LICENSE).
