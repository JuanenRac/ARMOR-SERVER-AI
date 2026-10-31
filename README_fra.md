<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="Bannière d'ARMOR-SERVER-AI" width="100%">
</p>

# 👁️ ARMOR-SERVER-AI

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  🇫🇷 <b>Français</b> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### Service d'observation : le mouvement sur les caméras pesé avec les radars ; il décide et explique, n'actionne jamais

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 ou ultérieure">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Langage">
  <img src="https://img.shields.io/badge/Target-Jetson%20Orin%20NX-76b900.svg" alt="Target">
  <img src="https://img.shields.io/badge/Tests-130%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.2.9-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturité">
</p>

---

**Vérification d'honnêteté - ce qui fonctionne aujourd'hui :** La couche de décision et le détecteur de mouvement sont réels et testés (130 tests), et le service d'observation **tourne sur le banc de test CM5** : système armé, il regarde de minuscules images grises des vraies caméras IP et signale le mouvement pesé avec les radars. Il ne distingue pas une personne d'un chat ou d'une branche : **il n'y a pas encore de modèle de détection**, et rien n'a tourné sur le Jetson, TensorRT ni un flux RTSP décodé là.

---

## 📋 En un coup d'œil

| | |
|---|---|
| Version | `0.2.9` |
| Maturité | Établi |
| Rôle | Service d'observation : mouvement pondéré avec les radars, recommandations seulement |
| Technologie | Python 3.11+, bibliothèque standard seule |
| Tests | 130 (`python -m unittest discover -s tests`) |
| Contrat | Client d'ARMOR-SERVER : 3 routes sous `/api/v1/ai/` ; personne ne l'appelle |
| Fonctionne sur | Le banc d'essai CM5 (en service, voir ARMOR-DEVOPS) ou tout ordinateur |
| Sur matériel réel | Tourne comme service sur le banc de test CM5 avec les vraies caméras IP (mouvement seulement) ; rien sur un Jetson |
| Licence | GPL-3.0-or-later |

**Aller à :** [Présentation](#-présentation) · [Architecture](#-architecture) · [Sécurité](#-sécurité-et-protection) · [Interfaces](#-interfaces) · [Configuration](#-configuration) · [Démarrage rapide](#-démarrage-rapide) · [Tests](#-tests) · [Dépannage](#-dépannage) · [Structure](#-structure-du-dépôt) · [Liés](#-projets-liés)

## 🚦 État du projet

Chaque ligne est une partie de ce dépôt et le feu dit où elle en est aujourd'hui. Elle est écrite d'après ce que le dépôt peut montrer (tests, compilations, exécutions), pas d'après ce qui est prévu.

🟢 Fait et vérifié · 🟡 Fonctionne, avec des limites connues · 🟠 À moitié fait ou pas encore vérifié · 🔴 Pas fait ou ne fonctionne pas

| Domaine | État | Ce que cela veut dire ici |
|---|---|---|
| Logiciel | 🟡 | Le détecteur de mouvement et la couche de décision tournent comme service sur le banc d'essai CM5, mais il n'y a pas encore de modèle de détection : il ne distingue pas une personne d'un chat ou d'une branche. |
| Tests | 🟢 | 130 tests réussissent (`python -m unittest discover -s tests`). |
| Matériel | 🟡 | Tant que le système est armé, il regarde de minuscules images grises des vraies caméras IP du banc d'essai CM5 ; rien n'a tourné sur un Jetson, avec TensorRT ni sur un flux RTSP décodé. |
| Intégration | 🟡 | Il rend compte au serveur du banc d'essai du mouvement pondéré par les radars . |
| Sécurité | 🟡 | Le service n'agit jamais (chaque décision porte `authorizes_action = false`), refuse un jeton de moins de 24 caractères et une adresse de serveur qui n'est ni `https://` ni cette même machine, et ne stocke jamais d'image ; testé, sans revue indépendante. |
| Documentation | 🟢 | Huit langues et le journal des modifications sont à jour. |

## 🎯 Présentation

* **Le service d'observation :** `python -m armor_server_ai.service` n'est jamais appelé par le serveur (c'est lui qui interroge le serveur, avec son propre jeton) : système **armé**, il prend une minuscule image grise (64 x 36, du flux de la caméra, jamais stockée) de chaque caméra toutes les quelques secondes, mesure quelle part de l'image a bougé et, quand des pistes radar concordent, le signale à ARMOR-SERVER avec son jeton.
* **Zones de l'image à ignorer :** le serveur lui donne les zones à ignorer de chaque caméra et les pixels qu'elles contiennent ne comptent pas (un arbre qui bouge, une route) ; une image presque entièrement ignorée n'est pas jugée et seize zones au plus comptent.
* **Profil jour/nuit avec hystérésis :** faible lumière sous 30 lux, retour au jour seulement au-dessus de 60 lux et jamais deux fois en 30 s, pour que le crépuscule ne le fasse pas osciller.
* **Fusion explicable :** chaque détection ou mouvement et les pistes radar donnent une gravité (`ignore`, `review`, `high`) avec les raisons ; un mouvement fort **et** une piste radar concordante est `high`, un mouvement plus faible est un `review`.
* **Des recommandations seulement :** une décision porte toujours `authorizes_action = false`. Le serveur central authentifie et autorise chaque action.
* **Moteurs vérifiés par somme de contrôle :** les moteurs TensorRT précompilés ne sont acceptés que s'ils existent, ne sont pas vides et, avec un `engines.json`, correspondent à leur SHA-256. Rien n'est compilé ni téléchargé.
* **Un service qui dit ce qui ne va pas :** il signale chaque nouveau problème quand il change (`unreachable`, `unauthorized`…) et *le serveur répond de nouveau* quand c'est fini ; un travailleur JSONL garde des résultats numérotés et expliqués et une mauvaise ligne n'arrête jamais le flux.
* **Un résumé quotidien des événements (facultatif, désactivé par défaut) :** `--daily-summary FICHIER --summary-config RÉGLAGES` transforme les événements d'un jour (alarmes, pertes de liaison, mesures, consommation) en comptages par type, zone et heure, les alarmes graves, les nœuds ayant perdu leur liaison, les mesures aberrantes et les pics de consommation, un texte par modèles en huit langues et cinq motifs explicables (la même alarme au même moment de l'heure, un capteur qui tombe en panne par intermittence, un nœud qui perd sa liaison à répétition, des fausses alarmes récurrentes, une consommation très au-dessus de sa moyenne mobile), chacun avec ses preuves et tous les seuils dans le fichier de réglages. Une note facultative d'un fournisseur d'IA est aussi désactivée par défaut : seul un fournisseur simulé est fourni, rien ne sort sans interrupteur explicite, et noms, adresses et identifiants sont d'abord retirés.

## 🧩 Rôle dans A.R.M.O.R.

ARMOR-SERVER-AI est la partie qui surveille le mouvement sur les caméras pendant que la maison est armée. Il n'agit jamais : il dit à [ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER) ce qu'il a vu et pourquoi (mouvement et pistes radar concordants valent `high`), et le serveur décide quoi faire. Un modèle qui reconnaît une personne, exécuté sur un Jetson, est l'étape suivante ; [ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION) garde les zones, masques et règles que ce modèle utilisera.

| Il parle à | Comment | Pour quoi faire |
|---|---|---|
| ARMOR-SERVER | il interroge le serveur (`/api/v1/ai/*`, jeton `ARMOR_AI_TOKEN`) | les caméras, leurs images grises et les zones à ignorer entrent ; l'observation sort |
| ARMOR-NODE-RADAR | via le serveur | les pistes radar et la lumière des nœuds qui couvrent chaque caméra |
| ARMOR-VISION | règles et masques (prochaine étape) | les zones, masques et règles que le modèle de détection utilisera |
| ARMOR-DEVOPS | l'installe comme service | déploiement sur le banc d'essai CM5 |

## 🏛️ Architecture

<p align="center">
  <img src="images/architecture.svg" alt="ARMOR-SERVER-AI architecture: what it asks the server, the observation service with its modules, and what it tells" width="100%">
</p>

## 🔒 Sécurité et protection

| Menace | Défense |
|---|---|
| Le service agit de lui-même | Jamais : chaque décision porte `authorizes_action = false` ; le serveur central authentifie et autorise chaque action |
| Le jeton traverse un réseau en clair | `ARMOR_AI_SERVER_URL` doit être `https://`, ou `http://` vers cette même machine (`127.0.0.1`, `localhost`) ; sinon le service refuse de démarrer |
| Un jeton faible | `ARMOR_AI_TOKEN` d'au moins 24 caractères (le serveur exige la même chose) |
| Réponses énormes du serveur | Le contexte est lu jusqu'à 1 000 000 d'octets et une réponse à une observation jusqu'à 65 536 ; une image fait exactement 64 x 36 = 2304 octets |
| Images conservées | La petite image grise n'est jamais conservée |
| Un moteur TensorRT altéré | Seulement des moteurs déjà construits (`daylight`, `low_light`) qui existent, ne sont pas vides et, avec un `engines.json`, correspondent à leur SHA-256 ; rien n'est compilé ni téléchargé |
| Une fausse alarme due à un changement de lumière | Un changement de plus de 60 % de l'image est de la lumière, pas du mouvement ; moins de 1 % n'est pas du mouvement ; seuil de pixel 18 ; au moins 64 pixels comptés ; au plus 16 zones à ignorer et une image presque entièrement ignorée n'est pas jugée |
| Papillotement jour/nuit ; données périmées ; une ligne JSON hostile | Hystérésis (faible lumière sous 30 lux, jour de nouveau au-dessus de 60 lux, jamais deux fois en 30 s, lux jusqu'à 200 000) ; une observation de plus de 10 s ne déclenche jamais d'alerte ; une ligne JSON de plus de 4096 octets est refusée et le flux continue |

## 🔌 Interfaces

| Route | Authentification | Ce qu'elle fait |
|---|---|---|
| `GET /api/v1/ai/context` | jeton `ARMOR_AI_TOKEN` | les maisons : nœuds et caméras, et les zones à ignorer de chaque caméra |
| `GET /api/v1/ai/cameras/<id>/frame` | le même | l'image grise 64 x 36 d'une caméra (2304 octets) |
| `POST /api/v1/ai/observations` | le même | le rapport : ce qu'elle a vu, la gravité et les raisons |
| `python -m armor_server_ai.service [--once]` | - | le service d'observation ; `--once` fait une passe et s'arrête |
| `python -m armor_server_ai.cli [--radar-tracks N]` | - | lignes JSON sur l'entrée standard (`{"label", "confidence", "lux", "radar_tracks"}`), une décision numérotée et expliquée par ligne |

Une décision est `{severity: ignore | review | high, reasons, authorizes_action: false}`. Étiquettes : `person`, `vehicle`, `animal`, `unknown`, `motion`. **Fusion :** `high` est une personne avec une confiance d'au moins 0,130 et au moins une piste radar, ou un fort mouvement et une piste radar qui concordent ; `review` est une détection confiante (0,55 de jour, 0,45 en faible lumière) ou une piste radar sans rien de vu ; le simple mouvement ne compte une piste radar qu'à 30 % de certitude (environ 3 % de l'image).

## ⚙️ Configuration

| Réglage | Par défaut | Ce qu'il fait |
|---|---|---|
| `ARMOR_AI_TOKEN` | oui (24+ caractères) | le jeton que le serveur a donné au service |
| `ARMOR_AI_SERVER_URL` | http://127.0.0.1:18080 | le serveur ; `https://` ou cette même machine |
| `ARMOR_AI_INTERVAL_S` | 3 (1-60) | secondes entre les passes ; avec beaucoup de caméras la passe s'allonge pour rester sous 200 images par minute |
| `ARMOR_AI_CONFIRM_FRAMES` | 2 (1-20) | images consécutives qui doivent montrer du mouvement avant d'avertir |
| `ARMOR_AI_COOLDOWN_S` | 60 (0-3600) | secondes avant de signaler à nouveau la même caméra |

Une valeur hors plage arrête le service avec `<NOM> must be between a and b`. Les seuils de la décision (0,130, 0,55, 0,45, la barre radar de 30 %) et du mouvement (18, 1 %, 60 %) sont des constantes du code décrites dans [docs/INFERENCE_BOUNDARY.md](docs/INFERENCE_BOUNDARY.md) ; les réglages du service sont dans [docs/SERVICE.md](docs/SERVICE.md).

## 🚀 Démarrage rapide

**Prérequis :** Python 3.11+ (bibliothèque standard seule). Facultatif : un Jetson Orin NX avec des moteurs TensorRT (non éprouvé).

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests                                                                      # 130 tests
echo '{"label":"person","confidence":0.9,"lux":4,"radar_tracks":1}' | python -m armor_server_ai.cli       # une décision depuis une ligne
python -m armor_server_ai.cli --daily-summary day.jsonl --summary-config docs/daily_summary.example.json  # refuse tant que les réglages ne disent pas enabled ; ensuite le résumé d'un jour
python -m armor_server_ai.service --once                                                                  # une passe du service d'observation
```

Voir la [frontière de l'inférence](docs/INFERENCE_BOUNDARY.md) et le [service](docs/SERVICE.md).

## 🧪 Tests

```powershell
python -m unittest discover -s tests  # 130 tests
python -I tools/armor_ci_validate.py
```

| Fichier de tests | Tests | Ce qu'il couvre |
|---|---|---|
| `test_service.py` | 16 | mouvement, le surveillant, le délai et quels radars comptent |
| `test_service_http.py` | 21 | la liaison avec le serveur, les règles d'adresse, les passes et les réglages |
| `test_vision_profile.py` | 20 | jour et nuit avec hystérésis, la politique de fusion et le travailleur |
| `test_cli_worker.py` | 10 | le travailleur JSON lignes et ses lignes erronées |
| `test_characterization_cli.py` | 9 | le travailleur et le service tels qu'avant le résumé quotidien |
| `test_daily_summary.py` | 41 | le résumé quotidien : entrée stricte, comptages cohérents, déterminisme, motifs avec preuves, les huit langues, masquage et l'interrupteur d'IA |
| `test_ignore_zones.py`, `test_registry.py` | 13 | zones à ignorer et moteurs TensorRT vérifiés |

GitHub Actions exécute la base A.R.M.O.R. à chaque push et pull request : la validation du manifeste, de la version, du journal des modifications et de la parité des README, puis le build et les tests propres au projet. Les sources passent le vérificateur de types : `python -m mypy src` ne signale rien.

## 🏗️ Compilation et publication

C'est du Python pur : rien à compiler. La version se trouve dans `pyproject.toml`, dans `armor.project.json` et dans le badge du README (lu depuis le manifeste) ; chaque version a son entrée dans [CHANGELOG.md](CHANGELOG.md). Les versions sont publiées sur GitHub.

## 🩺 Dépannage

| Vous voyez | Parce que | Faites |
|---|---|---|
| `armor-ai: watching, every N s` | le service a démarré | rien à faire |
| `ARMOR_AI_TOKEN (at least 24 characters) is needed` | le jeton manque ou est court | définissez un jeton de 24+ caractères, le même que celui du serveur |
| `ARMOR_AI_SERVER_URL must be https://...` | l'adresse enverrait le jeton en clair sur un réseau | utilisez `https://`, ou `http://127.0.0.1` sur la même machine |
| `armor-ai: the observation of <camera> could not be told (<code>)` | le rapport n'a pas atteint le serveur (`unreachable`, `unauthorized`...) | corrigez la cause ; le mouvement suivant est signalé sans attendre le délai ; `armor-ai: the server answers again` dit quand c'est fini |
| `radar and light sensors not counted: the site design lists no nodes for this camera` | la caméra ne nomme aucun nœud dans la conception du site | dans le concepteur de site de Studio, indiquez les nœuds radar qui couvrent la caméra |

## 📂 Structure du dépôt

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of ARMOR-SERVER-AI" width="100%">
</p>

<details>
<summary>Version texte de l'arborescence</summary>

```text
ARMOR-SERVER-AI/
├── src/armor_server_ai/
│   ├── service.py                 le service d'observation : une passe par intervalle
│   ├── motion.py                  image grise, zones à ignorer, mouvement
│   ├── profile.py                 jour ou faible lumière, avec hystérésis
│   ├── policy.py                  fusion : ignore, review, high
│   ├── engine_registry.py         moteurs TensorRT vérifiés par SHA-256
│   ├── cli.py                     le travailleur JSON lignes
│   ├── daily.py                   la commande et le rapport du résumé quotidien
│   ├── daily_events.py            lecture stricte des événements d'un jour
│   ├── daily_summary.py           comptages, alarmes graves et motifs explicables
│   ├── daily_text.py              le texte en huit langues, par modèles
│   ├── daily_ai.py                la note facultative d'un fournisseur, désactivée
│   ├── daily_config.py            le fichier de réglages, strict
│   └── redact.py                  noms, adresses et identifiants retirés
├── tests/                         130 tests : mouvement, politique, service, travailleur, résumé quotidien
├── docs/                          INFERENCE_BOUNDARY.md, SERVICE.md, DAILY_SUMMARY.md
├── tools/                         les vérifications CI et les outils partagés
├── images/                        bannière, icône et images du README
├── .github/                       workflow CI, avis au tableau de bord, modèles d'issues et de pull requests
├── armor.project.json             manifeste : version, rôle, maturité
├── pyproject.toml                 métadonnées du paquet, entrées
├── CHANGELOG.md                   ce qui a changé à chaque version
├── run.sh run.bat                 démarrer, flux partagé
├── build.sh build.bat             construire et tester, flux partagé
├── build-test.sh build-test.bat   construire, tester, empaqueter
├── test.sh test.bat               seulement les tests, jamais la version
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE
```

</details>

## 🗺️ Feuille de route et limites connues

**Limites connues aujourd'hui**

* Il n'y a pas de modèle de détection : il ne distingue pas une personne d'un chat ou d'une branche.
* Rien n'a tourné sur un Jetson, avec TensorRT ni sur un flux RTSP décodé là-bas.
* Pas de revue de sécurité indépendante.

**Prochainement**

* Un modèle qui reconnaît une personne, exécuté sur un Jetson Orin NX, avec les zones, masques et règles d'ARMOR-VISION.

## 🌍 Langues

Le README et les textes existent en anglais, espagnol, français, italien, allemand, chinois, japonais et portugais européen.

## 🔗 Projets liés

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) est un système de sécurité périmétrique composé de dépôts indépendants. Chacun a sa propre version, ses propres tests et son propre README ; voici la famille :

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contrats de messages, validateurs, vecteurs de conformité et types générés
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - Firmware du nœud de terrain pour ESP32-S3 avec trois radars et son propre panneau web
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - Protocoles des onduleurs et batteries solaires et messages d'un nœud passerelle
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - Nœud électrique : compteurs, le message des mesures du réseau et les règles de commutation
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - Nœud et centrale d'alarme : zones, armement, temporisations, sirène et PIN, avec ou sans le serveur
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - Panneau tactile : l'état du système sur un écran mural, armer et acquitter, et la maison de l'assistant vocal
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - Le réseau local : ses appareils, internet et ce qui change
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordinateur central : télémétrie, alarmes, appareils, relevés solaires et caméras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Console web : caméras, radar, alarmes, énergie solaire et concepteur de site 2D/3D
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Client Android de l'opérateur avec radar 2D/3D en direct
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - Client opérateur iPhone
* **ARMOR-SERVER-AI** (ce dépôt) - Politique d'inférence visuelle qui explique ses décisions et n'agit jamais
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Zones de caméra, masques et règles de détection pour la Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intentions vocales hors ligne avec une confirmation impossible à falsifier
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Boîtiers, électronique et matrice d'acceptation sur banc
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Déploiement, banc d'essai CM5, sauvegarde et TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulateur de télémétrie hors ligne avec des pannes reproductibles
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - Détecte, installe et met à jour les propres dépôts de l'écosystème
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Architecture, base de sécurité et matrice des capacités

## 📚 Documentation

* [Frontière de l'inférence](docs/INFERENCE_BOUNDARY.md) : ce qui se décide ici et ce qui est laissé à un modèle
* [Le résumé quotidien](docs/DAILY_SUMMARY.md) : les événements d'un jour, les motifs et la note d'IA facultative, désactivée par défaut
* [Le service](docs/SERVICE.md) : le service d'observation et ses réglages
* [Matrice des capacités : ce qui est prouvé et ce qui ne l'est pas](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catalogue des projets : versions et dépendances entre les dépôts](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Historique des modifications de ce dépôt](CHANGELOG.md)

## 🤝 Contribuer et communauté

* Avant une pull request, exécutez `python -I tools/armor_ci_validate.py` et les tests : les deux doivent réussir. Voir [CONTRIBUTING.md](CONTRIBUTING.md) et le [code de conduite](CODE_OF_CONDUCT.md).
* Le README existe en huit langues et est généré à partir des sources d'ARMOR-DOCS : une modification du texte se fait là-bas.
* Une modification d'un message entre composants commence dans ARMOR-COMMON.
* Ne décrivez pas comme fonctionnant sur une carte ce qui a seulement été compilé.
* Signalez une vulnérabilité en privé : [SECURITY.md](SECURITY.md). Questions, idées et rapports : electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTEUR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENCE

GPL-3.0-or-later - voir [LICENSE](LICENSE).
