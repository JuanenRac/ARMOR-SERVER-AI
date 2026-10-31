<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="Banner di ARMOR-SERVER-AI" width="100%">
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
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 o successiva">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Linguaggio">
  <img src="https://img.shields.io/badge/Target-Jetson%20Orin%20NX-76b900.svg" alt="Target">
  <img src="https://img.shields.io/badge/Tests-130%20passing-2ea44f.svg" alt="Test">
  <img src="https://img.shields.io/badge/Version-0.2.8-0f6cbd.svg" alt="Versione">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturità">
</p>

---

**Controllo di onestà - cosa funziona oggi:** Lo strato decisionale e il rilevatore di movimento sono reali e provati (130 test), e il servizio di osservazione **gira sul banco di prova CM5**: a sistema inserito guarda minuscoli fotogrammi grigi delle vere telecamere IP e riferisce il movimento pesato con i radar. Non distingue una persona da un gatto o da un ramo: **non c'è ancora un modello di rilevamento**, e nulla ha girato sul Jetson, TensorRT o su un flusso RTSP decodificato lì.

---

## 📋 In breve

| | |
|---|---|
| Versione | `0.2.8` |
| Maturità | Consolidato |
| Ruolo | Servizio di osservazione: movimento pesato con i radar, solo raccomandazioni |
| Tecnologia | Python 3.11+, solo libreria standard |
| Test | 130 (`python -m unittest discover -s tests`) |
| Contratto | Client di ARMOR-SERVER: 3 rotte sotto `/api/v1/ai/`; nessuno lo chiama |
| Gira su | Il banco di prova CM5 (come servizio, vedi ARMOR-DEVOPS) o qualsiasi computer |
| Su hardware reale | Gira come servizio sul banco di prova CM5 con le vere telecamere IP (solo movimento); nulla su un Jetson |
| Licenza | GPL-3.0-or-later |

**Vai a:** [Panoramica](#-panoramica) · [Architettura](#-architettura) · [Sicurezza](#-sicurezza-e-protezione) · [Interfacce](#-interfacce) · [Configurazione](#-configurazione) · [Avvio rapido](#-avvio-rapido) · [Test](#-test) · [Problemi](#-risoluzione-dei-problemi) · [Struttura](#-struttura-del-repository) · [Correlati](#-progetti-correlati)

## 🚦 Stato del progetto

Ogni riga è una parte di questo repository e il semaforo dice a che punto è oggi. È scritta in base a ciò che il repository può mostrare (test, compilazioni, esecuzioni), non a ciò che è previsto.

🟢 Fatto e verificato · 🟡 Funziona, con limiti noti · 🟠 Fatto a metà o non ancora verificato · 🔴 Non fatto o non funzionante

| Area | Stato | Cosa significa qui |
|---|---|---|
| Software | 🟡 | Il rilevatore di movimento e il livello decisionale girano come servizio sul banco di prova CM5, ma non c'è ancora un modello di rilevamento: non distingue una persona da un gatto o da un ramo. |
| Test | 🟢 | Superano 130 test (`python -m unittest discover -s tests`). |
| Hardware | 🟡 | Mentre il sistema è inserito guarda minuscoli fotogrammi grigi delle telecamere IP reali del banco di prova CM5; nulla ha girato su una Jetson, con TensorRT o su un flusso RTSP decodificato. |
| Integrazione | 🟡 | Riferisce al server del banco di prova il movimento ponderato con i radar. |
| Sicurezza | 🟡 | Il servizio non agisce mai (ogni decisione porta `authorizes_action = false`), rifiuta un token sotto i 24 caratteri e un indirizzo di server che non sia `https://` o questa stessa macchina, e non salva mai un'immagine; provato, senza revisione indipendente. |
| Documentazione | 🟢 | Otto lingue e il registro delle modifiche sono aggiornati. |

## 🎯 Panoramica

* **Il servizio di osservazione:** `python -m armor_server_ai.service` non viene mai chiamato dal server (è lui a interrogare il server, con il proprio token): a sistema **inserito** prende un minuscolo fotogramma grigio (64 x 36, dal flusso della telecamera, mai salvato) di ogni telecamera ogni pochi secondi, misura quanta parte dell'immagine si è mossa e, quando le tracce radar concordano, lo riferisce ad ARMOR-SERVER con il suo token.
* **Zone dell'immagine da ignorare:** il server gli dà le zone da ignorare di ogni telecamera e i pixel al loro interno non contano (un albero che si muove, una strada); un'immagine quasi tutta ignorata non è giudicata e contano al massimo sedici zone.
* **Profilo giorno/notte con isteresi:** poca luce sotto 30 lux, torna al giorno solo sopra 60 lux e mai due volte in 30 s, così il crepuscolo non lo fa oscillare.
* **Fusione spiegabile:** ogni rilevamento o movimento e le tracce radar danno una gravità (`ignore`, `review`, `high`) con le ragioni; movimento forte **e** una traccia radar concorde è `high`, un movimento più debole è una `review`.
* **Solo raccomandazioni:** una decisione porta sempre `authorizes_action = false`. Il server centrale autentica e autorizza ogni azione.
* **Motori verificati con checksum:** i motori TensorRT precompilati sono accettati solo se presenti, non vuoti e, con un `engines.json`, coincidenti con il loro SHA-256. Nulla è compilato né scaricato.
* **Un servizio che dice cosa non va:** riferisce ogni nuovo problema quando cambia (`unreachable`, `unauthorized`…) e *il server risponde di nuovo* quando è finito; un worker JSONL conserva risultati numerati e spiegati e una riga errata non ferma mai il flusso.
* **Un riepilogo giornaliero degli eventi (facoltativo, spento per impostazione predefinita):** `--daily-summary FILE --summary-config IMPOSTAZIONI` trasforma gli eventi di un giorno (allarmi, perdite di collegamento, letture, consumo) in conteggi per tipo, zona e ora, gli allarmi gravi, i nodi che hanno perso il collegamento, le letture anomale e i picchi di consumo, un testo da modelli in otto lingue e cinque schemi spiegabili (lo stesso allarme nello stesso momento dell'ora, un sensore che si guasta a intermittenza, un nodo che perde il collegamento ripetutamente, falsi allarmi ricorrenti, consumo molto sopra la media mobile), ciascuno con le sue prove e tutte le soglie nel file di impostazioni. Anche una nota facoltativa di un fornitore di IA è spenta per impostazione predefinita: c'è solo un fornitore simulato, nulla esce senza un interruttore esplicito e nomi, indirizzi e credenziali vengono prima rimossi.

## 🧩 Ruolo in A.R.M.O.R.

ARMOR-SERVER-AI è la parte che sorveglia il movimento sulle telecamere mentre la casa è inserita. Non agisce mai: dice ad [ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER) cosa ha visto e perché (movimento e tracce radar concordi valgono `high`), e il server decide cosa fare. Un modello che riconosca una persona, eseguito su un Jetson, è il passo successivo; [ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION) tiene le zone, le maschere e le regole che quel modello userà.

| Parla con | Come | A che scopo |
|---|---|---|
| ARMOR-SERVER | interroga il server (`/api/v1/ai/*`, token `ARMOR_AI_TOKEN`) | le telecamere, i loro fotogrammi grigi e le zone da ignorare entrano; l'osservazione esce |
| ARMOR-NODE-RADAR | tramite il server | le tracce radar e la luce dei nodi che coprono ogni telecamera |
| ARMOR-VISION | regole e maschere (prossimo passo) | le zone, maschere e regole che userà il modello di rilevamento |
| ARMOR-DEVOPS | lo installa come servizio | distribuzione sul banco di prova CM5 |

## 🏛️ Architettura

<p align="center">
  <img src="images/architecture.svg" alt="ARMOR-SERVER-AI architecture: what it asks the server, the observation service with its modules, and what it tells" width="100%">
</p>

## 🔒 Sicurezza e protezione

| Minaccia | Difesa |
|---|---|
| Il servizio agisce di propria iniziativa | Mai: ogni decisione porta `authorizes_action = false`; il server centrale autentica e autorizza ogni azione |
| Il token attraversa una rete in chiaro | `ARMOR_AI_SERVER_URL` deve essere `https://`, o `http://` verso questa stessa macchina (`127.0.0.1`, `localhost`); altrimenti il servizio rifiuta di partire |
| Un token debole | `ARMOR_AI_TOKEN` di almeno 24 caratteri (lo richiede anche il server) |
| Risposte enormi dal server | Il contesto si legge fino a 1 000 000 di byte e la risposta a un'osservazione fino a 65 536; un fotogramma è esattamente 64 x 36 = 2304 byte |
| Immagini conservate | Il piccolo fotogramma grigio non viene mai salvato |
| Un motore TensorRT manomesso | Solo motori già costruiti (`daylight`, `low_light`) che esistono, non sono vuoti e, con un `engines.json`, coincidono con lo SHA-256; non si compila né si scarica nulla |
| Un falso allarme per un cambio di luce | Una variazione di oltre il 60 % dell'immagine è luce, non movimento; sotto l'1 % non è movimento; soglia di pixel 18; almeno 64 pixel contati; al massimo 16 zone da ignorare e un'immagine quasi tutta ignorata non viene giudicata |
| Sfarfallio giorno/notte; dati vecchi; una riga JSON ostile | Isteresi (poca luce sotto 30 lux, di nuovo giorno sopra 60 lux, mai due volte in 30 s, lux fino a 200 000); un'osservazione più vecchia di 10 s non dà mai allarme; una riga JSON oltre 4096 byte è rifiutata e il flusso continua |

## 🔌 Interfacce

| Rotta | Autenticazione | Cosa fa |
|---|---|---|
| `GET /api/v1/ai/context` | token `ARMOR_AI_TOKEN` | le case: nodi e telecamere, e le zone da ignorare di ogni telecamera |
| `GET /api/v1/ai/cameras/<id>/frame` | lo stesso | il fotogramma grigio 64 x 36 di una telecamera (2304 byte) |
| `POST /api/v1/ai/observations` | lo stesso | il rapporto: cosa ha visto, la gravità e i motivi |
| `python -m armor_server_ai.service [--once]` | - | il servizio di osservazione; `--once` fa un passaggio e termina |
| `python -m armor_server_ai.cli [--radar-tracks N]` | - | righe JSON sullo standard input (`{"label", "confidence", "lux", "radar_tracks"}`), una decisione numerata e spiegata per riga |

Una decisione è `{severity: ignore | review | high, reasons, authorizes_action: false}`. Etichette: `person`, `vehicle`, `animal`, `unknown`, `motion`. **Fusione:** `high` è una persona con confidenza di almeno 0,130 e almeno una traccia radar, oppure un forte movimento e una traccia radar concordi; `review` è un rilevamento sicuro (0,55 di giorno, 0,45 con poca luce) o una traccia radar senza nulla di visto; il semplice movimento conta una traccia radar solo con il 30 % di certezza (circa il 3 % dell'immagine).

## ⚙️ Configurazione

| Impostazione | Predefinito | Cosa fa |
|---|---|---|
| `ARMOR_AI_TOKEN` | sì (24+ caratteri) | il token che il server ha dato al servizio |
| `ARMOR_AI_SERVER_URL` | http://127.0.0.1:18080 | il server; `https://` o questa stessa macchina |
| `ARMOR_AI_INTERVAL_S` | 3 (1-60) | secondi tra i passaggi; con molte telecamere il passaggio si allunga per restare sotto 200 immagini al minuto |
| `ARMOR_AI_CONFIRM_FRAMES` | 2 (1-20) | fotogrammi consecutivi che devono mostrare movimento prima di segnalare |
| `ARMOR_AI_COOLDOWN_S` | 60 (0-3600) | secondi prima di segnalare di nuovo la stessa telecamera |

Un valore fuori intervallo ferma il servizio con `<NOME> must be between a and b`. Le soglie della decisione (0,130, 0,55, 0,45, la barra radar del 30 %) e del movimento (18, 1 %, 60 %) sono costanti del codice descritte in [docs/INFERENCE_BOUNDARY.md](docs/INFERENCE_BOUNDARY.md); le impostazioni del servizio sono in [docs/SERVICE.md](docs/SERVICE.md).

## 🚀 Avvio rapido

**Requisiti:** Python 3.11+ (solo libreria standard). Facoltativo: un Jetson Orin NX con motori TensorRT (non provato).

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests                                                                      # 130 test
echo '{"label":"person","confidence":0.9,"lux":4,"radar_tracks":1}' | python -m armor_server_ai.cli       # una decisione da una riga
python -m armor_server_ai.cli --daily-summary day.jsonl --summary-config docs/daily_summary.example.json  # rifiuta finché le impostazioni non dicono enabled; poi il riepilogo di un giorno
python -m armor_server_ai.service --once                                                                  # un passaggio del servizio di osservazione
```

Vedi il [confine dell'inferenza](docs/INFERENCE_BOUNDARY.md) e il [servizio](docs/SERVICE.md).

## 🧪 Test

```powershell
python -m unittest discover -s tests  # 130 test
python -I tools/armor_ci_validate.py
```

| File di test | Test | Cosa copre |
|---|---|---|
| `test_service.py` | 16 | movimento, il sorvegliante, il raffreddamento e quali radar contano |
| `test_service_http.py` | 21 | il collegamento col server, le regole sull'indirizzo, i passaggi e le impostazioni |
| `test_vision_profile.py` | 20 | giorno e notte con isteresi, la politica di fusione e il worker |
| `test_cli_worker.py` | 10 | il worker di righe JSON e le sue righe errate |
| `test_characterization_cli.py` | 9 | il worker e il servizio com'erano prima del riepilogo giornaliero |
| `test_daily_summary.py` | 41 | il riepilogo giornaliero: input rigoroso, conteggi che tornano, determinismo, schemi con prove, otto lingue, oscuramento e interruttore IA |
| `test_ignore_zones.py`, `test_registry.py` | 13 | zone da ignorare e motori TensorRT verificati |

GitHub Actions esegue la base A.R.M.O.R. a ogni push e pull request: la validazione di manifesto, versione, registro delle modifiche e parità dei README, poi la compilazione e i test del progetto. I sorgenti superano il controllo dei tipi: `python -m mypy src` non segnala nulla.

## 🏗️ Compilazione e rilascio

È Python puro: nulla da compilare. La versione risiede in `pyproject.toml`, in `armor.project.json` e nel badge del README (letto dal manifesto); ogni versione ha la sua voce in [CHANGELOG.md](CHANGELOG.md). Le versioni sono pubblicate su GitHub.

## 🩺 Risoluzione dei problemi

| Vedi | Perché | Fai |
|---|---|---|
| `armor-ai: watching, every N s` | il servizio è partito | niente da fare |
| `ARMOR_AI_TOKEN (at least 24 characters) is needed` | manca il token o è corto | imposta un token di 24+ caratteri, lo stesso del server |
| `ARMOR_AI_SERVER_URL must be https://...` | l'indirizzo manderebbe il token in chiaro su una rete | usa `https://`, o `http://127.0.0.1` sulla stessa macchina |
| `armor-ai: the observation of <camera> could not be told (<code>)` | il rapporto non è arrivato al server (`unreachable`, `unauthorized`...) | correggi la causa; il prossimo movimento viene segnalato senza attendere il raffreddamento; `armor-ai: the server answers again` dice quando è finita |
| `radar and light sensors not counted: the site design lists no nodes for this camera` | la telecamera non nomina nodi nel progetto del sito | nel progettista del sito di Studio, indica i nodi radar che coprono la telecamera |

## 📂 Struttura del repository

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of ARMOR-SERVER-AI" width="100%">
</p>

<details>
<summary>Versione testuale dell'albero</summary>

```text
ARMOR-SERVER-AI/
├── src/armor_server_ai/
│   ├── service.py                 il servizio di osservazione: un passaggio per intervallo
│   ├── motion.py                  fotogramma grigio, zone da ignorare, movimento
│   ├── profile.py                 giorno o poca luce, con isteresi
│   ├── policy.py                  fusione: ignore, review, high
│   ├── engine_registry.py         motori TensorRT verificati con SHA-256
│   ├── cli.py                     il worker di righe JSON
│   ├── daily.py                   il comando e il rapporto del riepilogo giornaliero
│   ├── daily_events.py            lettura rigorosa degli eventi di un giorno
│   ├── daily_summary.py           conteggi, allarmi gravi e schemi spiegabili
│   ├── daily_text.py              il testo in otto lingue, da modelli
│   ├── daily_ai.py                la nota facoltativa di un fornitore, spenta
│   ├── daily_config.py            il file di impostazioni, rigoroso
│   └── redact.py                  nomi, indirizzi e credenziali rimossi
├── tests/                         130 test: movimento, politica, servizio, worker, riepilogo giornaliero
├── docs/                          INFERENCE_BOUNDARY.md, SERVICE.md, DAILY_SUMMARY.md
├── tools/                         i controlli CI e gli strumenti condivisi
├── images/                        banner, icona e immagini del README
├── .github/                       workflow CI, avviso alla dashboard, modelli per issue e pull request
├── armor.project.json             manifesto: versione, ruolo, maturità
├── pyproject.toml                 metadati del pacchetto, ingressi
├── CHANGELOG.md                   cosa è cambiato in ogni versione
├── run.sh run.bat                 avvio, flusso condiviso
├── build.sh build.bat             compila e prova, flusso condiviso
├── build-test.sh build-test.bat   compila, prova e impacchetta
├── test.sh test.bat               solo i test, mai la versione
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE
```

</details>

## 🗺️ Roadmap e limiti noti

**Limiti noti oggi**

* Non esiste un modello di rilevamento: non distingue una persona da un gatto o da un ramo.
* Nulla ha girato su un Jetson, con TensorRT o su un flusso RTSP decodificato lì.
* Nessuna revisione di sicurezza indipendente.

**Prossimi passi**

* Un modello che riconosca una persona, eseguito su un Jetson Orin NX, con le zone, maschere e regole di ARMOR-VISION.

## 🌍 Lingue

Il README e i testi esistono in inglese, spagnolo, francese, italiano, tedesco, cinese, giapponese e portoghese europeo.

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

## 📚 Documentazione

* [Confine dell'inferenza](docs/INFERENCE_BOUNDARY.md): cosa si decide qui e cosa resta a un modello
* [Il riepilogo giornaliero](docs/DAILY_SUMMARY.md): gli eventi di un giorno, gli schemi e la nota IA facoltativa, spenta per impostazione predefinita
* [Il servizio](docs/SERVICE.md): il servizio di osservazione e le sue impostazioni
* [Matrice delle capacità: cosa è provato e cosa no](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catalogo dei progetti: versioni e dipendenze tra i repository](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Cronologia delle modifiche di questo repository](CHANGELOG.md)

## 🤝 Contribuire e comunità

* Prima di una pull request esegui `python -I tools/armor_ci_validate.py` e i test: devono passare entrambi. Vedi [CONTRIBUTING.md](CONTRIBUTING.md) e il [codice di condotta](CODE_OF_CONDUCT.md).
* Il README esiste in otto lingue ed è generato dalle sorgenti in ARMOR-DOCS: una modifica al testo si fa lì.
* Una modifica a un messaggio tra componenti parte da ARMOR-COMMON.
* Non descrivere come funzionante su una scheda ciò che è stato solo compilato.
* Segnala una vulnerabilità in privato: [SECURITY.md](SECURITY.md). Domande, idee e segnalazioni: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTORE

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENZA

GPL-3.0-or-later - vedi [LICENSE](LICENSE).
