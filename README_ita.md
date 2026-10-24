<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-SERVER-AI banner" width="100%">
</p>

# 👁️ ARMOR-SERVER-AI

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  🇮🇹 <b>Italiano</b> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### Servizio di osservazione: il movimento sulle telecamere pesato con i radar; decide e spiega, non aziona mai

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Target-Jetson%20Orin%20NX-76b900.svg" alt="Target">
  <img src="https://img.shields.io/badge/Tests-80%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.2.7-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**Controllo di onestà - cosa funziona oggi:** Lo strato decisionale e il rilevatore di movimento sono reali e provati (80 test), e il servizio di osservazione **gira sul banco di prova CM5**: a sistema inserito guarda minuscoli fotogrammi grigi delle vere telecamere IP e riferisce il movimento pesato con i radar. Non distingue una persona da un gatto o da un ramo: **non c'è ancora un modello di rilevamento**, e nulla ha girato sul Jetson, TensorRT o su un flusso RTSP decodificato lì.

---

## 📋 In breve

| | |
|---|---|
| Versione | `0.2.7` |
| Maturità | Consolidato |
| Test | 80 (`python -m unittest discover -s tests`) |
| Tecnologia | Python 3.11+ (standard library) |
| Su hardware reale | Gira come servizio sul banco di prova CM5 con le vere telecamere IP (solo movimento); nulla su un Jetson |

## 🚦 Stato del progetto

Ogni riga è una parte di questo repository e il semaforo dice a che punto è oggi. È scritta in base a ciò che il repository può mostrare (test, compilazioni, esecuzioni), non a ciò che è previsto.

🟢 Fatto e verificato · 🟡 Funziona, con limiti noti · 🟠 Fatto a metà o non ancora verificato · 🔴 Non fatto o non funzionante

| Area | Stato | Cosa significa qui |
|---|---|---|
| Software | 🟡 | Il rilevatore di movimento e il livello decisionale girano come servizio sul banco di prova CM5, ma non c'è ancora un modello di rilevamento: non distingue una persona da un gatto o da un ramo. |
| Test | 🟢 | Superano 80 test (`python -m unittest discover -s tests`). |
| Hardware | 🟡 | Mentre il sistema è inserito guarda minuscoli fotogrammi grigi delle telecamere IP reali del banco di prova CM5; nulla ha girato su una Jetson, con TensorRT o su un flusso RTSP decodificato. |
| Integrazione | 🟡 | Riferisce al server del banco di prova il movimento ponderato con i radar. |
| Documentazione | 🟢 | Otto lingue e il registro delle modifiche sono aggiornati. |

## 🎯 Panoramica

* **Il servizio di osservazione:** `python -m armor_server_ai.service` non viene mai chiamato dal server (è lui a interrogare il server, con il proprio token): a sistema **inserito** prende un minuscolo fotogramma grigio (64 x 36, dal flusso della telecamera, mai salvato) di ogni telecamera ogni pochi secondi, misura quanta parte dell'immagine si è mossa e, quando le tracce radar concordano, lo riferisce ad ARMOR-SERVER con il suo token.
* **Zone dell'immagine da ignorare:** il server gli dà le zone da ignorare di ogni telecamera e i pixel al loro interno non contano (un albero che si muove, una strada); un'immagine quasi tutta ignorata non è giudicata e contano al massimo sedici zone.
* **Profilo giorno/notte con isteresi:** poca luce sotto 30 lux, torna al giorno solo sopra 60 lux e mai due volte in 30 s, così il crepuscolo non lo fa oscillare.
* **Fusione spiegabile:** ogni rilevamento o movimento e le tracce radar danno una gravità (`ignore`, `review`, `high`) con le ragioni; movimento forte **e** una traccia radar concorde è `high`, un movimento più debole è una `review`.
* **Solo raccomandazioni:** una decisione porta sempre `authorizes_action = false`. Il server centrale autentica e autorizza ogni azione.
* **Motori verificati con checksum:** i motori TensorRT precompilati sono accettati solo se presenti, non vuoti e, con un `engines.json`, coincidenti con il loro SHA-256. Nulla è compilato né scaricato.
* **Un servizio che dice cosa non va:** riferisce ogni nuovo problema quando cambia (`unreachable`, `unauthorized`…) e *il server risponde di nuovo* quando è finito; un worker JSONL conserva risultati numerati e spiegati e una riga errata non ferma mai il flusso.

## 🧩 Ruolo in A.R.M.O.R.

ARMOR-SERVER-AI è la parte che sorveglia il movimento sulle telecamere mentre la casa è inserita. Non agisce mai: dice ad [ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER) cosa ha visto e perché (movimento e tracce radar concordi valgono `high`), e il server decide cosa fare. Un modello che riconosca una persona, eseguito su un Jetson, è il passo successivo; [ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION) tiene le zone, le maschere e le regole che quel modello userà.

## 📂 Struttura del repository

```text
ARMOR-SERVER-AI/
├── src/armor_server_ai/   profile (day/night), policy (fusion), motion (movement and ignore zones), engine_registry, service (the observation service), cli
├── tests/                 80 tests
├── tools/                 the shared CI checks (armor_ci_validate.py, armor_project_tool.py, _armor_readme_parity.py)
└── docs/                  INFERENCE_BOUNDARY.md, SERVICE.md
```

## 🛠️ Ambiente di sviluppo

**Requisiti:** Python 3.11+, facoltativo: un Jetson Orin NX con motori TensorRT (non provato)

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests   # 80 tests
echo '{"label":"person","confidence":0.9,"lux":4,"radar_tracks":1}' | python -m armor_server_ai.cli
python -m armor_server_ai.service --once   # one pass of the observation service
```

Vedi il [confine dell'inferenza](docs/INFERENCE_BOUNDARY.md) e il [servizio](docs/SERVICE.md).

## 🔗 Progetti correlati

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) è un sistema di sicurezza perimetrale fatto di repository indipendenti. Ognuno ha la propria versione, i propri test e il proprio README; ecco la famiglia:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contratti dei messaggi, validatori, vettori di conformità e tipi generati
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - Firmware del nodo di campo per ESP32-S3 con tre radar e un proprio pannello web
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - Protocolli di inverter e batterie solari e messaggi di un nodo gateway
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - Nodo elettrico: contatori, il messaggio delle letture della rete e le regole di manovra
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - Nodo e centrale d'allarme: zone, inserimento, ritardi, sirena e PIN, con il server o senza
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - Pannello touch: lo stato del sistema su uno schermo a parete, attivare e riconoscere gli allarmi, e la casa dell'assistente vocale
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - La rete locale: i suoi dispositivi, internet e ciò che cambia
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordinatore centrale: telemetria, allarmi, dispositivi, letture solari e telecamere
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Console web: telecamere, radar, allarmi, energia solare e progettista del sito 2D/3D
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Client Android dell'operatore con radar 2D/3D in tempo reale
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - Client operatore per iPhone
* **ARMOR-SERVER-AI** (questo repository) - Politica di inferenza visiva che spiega le sue decisioni e non agisce mai
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Zone delle telecamere, maschere e regole di rilevamento per la Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intenti vocali offline con una conferma impossibile da falsificare
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Contenitori, elettronica e matrice di accettazione da banco
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Distribuzione, banco di prova CM5, backup e TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulatore di telemetria offline con guasti ripetibili
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - Rileva, installa e aggiorna i repository stessi dell'ecosistema
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Architettura, base di sicurezza e matrice delle capacità

## 📚 Documentazione e comunità

Dove leggere di più:

* [Matrice delle capacità: cosa è provato e cosa no](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catalogo dei progetti: versioni e dipendenze tra i repository](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Cronologia delle modifiche di questo repository](CHANGELOG.md)
* [Licenza (GPL-3.0-or-later)](LICENSE)
* Domande, idee e segnalazioni: electrohobby3d@gmail.com

## 👤 AUTORE

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENZA

GPL-3.0-or-later - vedi [LICENSE](LICENSE).
