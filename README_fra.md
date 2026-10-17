<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-SERVER-AI banner" width="100%">
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
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Target-Jetson%20Orin%20NX-76b900.svg" alt="Target">
  <img src="https://img.shields.io/badge/Tests-46%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.2.6-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**Vérification d'honnêteté - ce qui fonctionne aujourd'hui:** La couche de décision et le détecteur de mouvement sont réels et testés (46 tests), et le service d'observation **tourne sur le banc de test CM5** : système armé, il regarde de minuscules images grises des vraies caméras IP et signale le mouvement pesé avec les radars. Il ne distingue pas une personne d'un chat ou d'une branche : **il n'y a pas encore de modèle de détection**, et rien n'a tourné sur le Jetson, TensorRT ni un flux RTSP décodé là.

---

## 📋 En un coup d'œil

| | |
|---|---|
| Version | `0.2.6` |
| Maturité | Établi |
| Tests | 46 (`python -m unittest discover -s tests`) |
| Technologie | Python 3.11+ (standard library) |
| Sur matériel réel | Tourne comme service sur le banc de test CM5 avec les vraies caméras IP (mouvement seulement) ; rien sur un Jetson |

## 🎯 Présentation

* **Le service d'observation :** `python -m armor_server_ai.service` n'est jamais appelé par le serveur (c'est lui qui interroge le serveur, avec son propre jeton) : système **armé**, il prend une minuscule image grise (64 x 36, du flux de la caméra, jamais stockée) de chaque caméra toutes les quelques secondes, mesure quelle part de l'image a bougé et, quand des pistes radar concordent, le signale à ARMOR-SERVER avec son jeton.
* **Zones de l'image à ignorer :** le serveur lui donne les zones à ignorer de chaque caméra et les pixels qu'elles contiennent ne comptent pas (un arbre qui bouge, une route) ; une image presque entièrement ignorée n'est pas jugée et seize zones au plus comptent.
* **Profil jour/nuit avec hystérésis :** faible lumière sous 30 lux, retour au jour seulement au-dessus de 60 lux et jamais deux fois en 30 s, pour que le crépuscule ne le fasse pas osciller.
* **Fusion explicable :** chaque détection ou mouvement et les pistes radar donnent une gravité (`ignore`, `review`, `high`) avec les raisons ; un mouvement fort **et** une piste radar concordante est `high`, un mouvement plus faible est un `review`.
* **Des recommandations seulement :** une décision porte toujours `authorizes_action = false`. Le serveur central authentifie et autorise chaque action.
* **Moteurs vérifiés par somme de contrôle :** les moteurs TensorRT précompilés ne sont acceptés que s'ils existent, ne sont pas vides et, avec un `engines.json`, correspondent à leur SHA-256. Rien n'est compilé ni téléchargé.
* **Un service qui dit ce qui ne va pas :** il signale chaque nouveau problème quand il change (`unreachable`, `unauthorized`…) et *le serveur répond de nouveau* quand c'est fini ; un travailleur JSONL garde des résultats numérotés et expliqués et une mauvaise ligne n'arrête jamais le flux.

## 🧩 Rôle dans A.R.M.O.R.

ARMOR-SERVER-AI est la partie qui surveille le mouvement sur les caméras pendant que la maison est armée. Il n'agit jamais : il dit à [ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER) ce qu'il a vu et pourquoi (mouvement et pistes radar concordants valent `high`), et le serveur décide quoi faire. Un modèle qui reconnaît une personne, exécuté sur un Jetson, est l'étape suivante ; [ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION) garde les zones, masques et règles que ce modèle utilisera.

## 📂 Structure du dépôt

```text
ARMOR-SERVER-AI/
├── src/armor_server_ai/   profile (day/night), policy (fusion), motion (movement and ignore zones), engine_registry, service (the observation service), cli
├── tests/                 46 tests
└── docs/                  INFERENCE_BOUNDARY.md, SERVICE.md
```

## 🛠️ Environnement de développement

**Prérequis:** Python 3.11+, optional: a Jetson Orin NX with TensorRT engines (not proven)

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests   # 46 tests
echo '{"label":"person","confidence":0.9,"lux":4,"radar_tracks":1}' | python -m armor_server_ai.cli
python -m armor_server_ai.service --once   # one pass of the observation service
```

Voir la [frontière de l'inférence](docs/INFERENCE_BOUNDARY.md) et le [service](docs/SERVICE.md).

## 🔗 Projets liés

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) est un système de sécurité périmétrique composé de dépôts indépendants. Chacun a sa propre version, ses propres tests et son propre README ; voici la famille :

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contrats de messages, validateurs, vecteurs de conformité et types générés
* **[ARMOR-RADAR](https://github.com/JuanenRac/ARMOR-RADAR)** - Firmware du nœud de terrain pour ESP32-S3 avec trois radars et son propre panneau web
* **[ARMOR-SOLAR](https://github.com/JuanenRac/ARMOR-SOLAR)** - Protocoles des onduleurs et batteries solaires et messages d'un nœud passerelle
* **[ARMOR-ELECTRICAL](https://github.com/JuanenRac/ARMOR-ELECTRICAL)** - Nœud électrique : compteurs, le message des mesures du réseau et les règles de commutation
* **[ARMOR-ALARM](https://github.com/JuanenRac/ARMOR-ALARM)** - Nœud et centrale d'alarme : zones, armement, temporisations, sirène et PIN, avec ou sans le serveur
* **[ARMOR-HMI](https://github.com/JuanenRac/ARMOR-HMI)** - Panneau tactile : l'état du système sur un écran mural, armer et acquitter, et la maison de l'assistant vocal
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - Le réseau local : ses appareils, internet et ce qui change
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordinateur central : télémétrie, alarmes, appareils, relevés solaires et caméras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Console web : caméras, radar, alarmes, énergie solaire et concepteur de site 2D/3D
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Client Android de l'opérateur avec radar 2D/3D en direct
* **ARMOR-SERVER-AI** (ce dépôt) - Politique d'inférence visuelle qui explique ses décisions et n'agit jamais
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Zones de caméra, masques et règles de détection pour la Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intentions vocales hors ligne avec une confirmation impossible à falsifier
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Boîtiers, électronique et matrice d'acceptation sur banc
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Déploiement, banc d'essai CM5, sauvegarde et TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulateur de télémétrie hors ligne avec des pannes reproductibles
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - Détecte, installe et met à jour les propres dépôts de l'écosystème
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Architecture, base de sécurité et matrice des capacités

## 📚 Documentation et communauté

Pour en savoir plus :

* [Matrice des capacités : ce qui est prouvé et ce qui ne l'est pas](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catalogue des projets : versions et dépendances entre les dépôts](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Historique des modifications de ce dépôt](CHANGELOG.md)
* [Licence (GPL-3.0-or-later)](LICENSE)
* Questions, idées et rapports : electrohobby3d@gmail.com

## 👤 AUTEUR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENCE

GPL-3.0-or-later - voir [LICENSE](LICENSE).
