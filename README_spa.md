<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="Banner de ARMOR-SERVER-AI" width="100%">
</p>

# 👁️ ARMOR-SERVER-AI

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  🇪🇸 <b>Español</b> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### Servicio de observación: el movimiento en las cámaras sopesado con los radares; decide y explica, nunca actúa

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 o posterior">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Lenguaje">
  <img src="https://img.shields.io/badge/Target-Jetson%20Orin%20NX-76b900.svg" alt="Target">
  <img src="https://img.shields.io/badge/Tests-80%20passing-2ea44f.svg" alt="Pruebas">
  <img src="https://img.shields.io/badge/Version-0.2.8-0f6cbd.svg" alt="Versión">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Madurez">
</p>

---

**Comprobación de honestidad - qué funciona hoy:** La capa de decisión y el detector de movimiento son reales y están probados (80 tests), y el servicio de observación **corre en el banco de pruebas de la CM5**: con el sistema armado mira pequeños fotogramas grises de las cámaras IP reales e informa del movimiento sopesado con los radares. No distingue a una persona de un gato o una rama: **todavía no hay modelo de detección**, y nada ha corrido en la Jetson, TensorRT ni un flujo RTSP decodificado allí.

---

## 📋 De un vistazo

| | |
|---|---|
| Versión | `0.2.8` |
| Madurez | Establecido |
| Función | Servicio de observación: movimiento ponderado con los radares, solo recomienda |
| Tecnología | Python 3.11+, solo biblioteca estándar |
| Pruebas | 80 (`python -m unittest discover -s tests`) |
| Contrato | Cliente de ARMOR-SERVER: 3 rutas bajo `/api/v1/ai/`; nadie lo llama |
| Funciona en | El banco de la CM5 (como servicio, ver ARMOR-DEVOPS) o cualquier ordenador |
| En hardware real | Corriendo como servicio en el banco de pruebas de la CM5 con las cámaras IP reales (solo movimiento); nada en una Jetson |
| Licencia | GPL-3.0-or-later |

**Ir a:** [Resumen](#-resumen) · [Arquitectura](#-arquitectura) · [Seguridad](#-seguridad-y-protección) · [Interfaces](#-interfaces) · [Configuración](#-configuración) · [Inicio rápido](#-inicio-rápido) · [Pruebas](#-pruebas) · [Problemas](#-resolución-de-problemas) · [Estructura](#-estructura-del-repositorio) · [Relacionados](#-proyectos-relacionados)

## 🚦 Estado del proyecto

Cada línea es una parte de este repositorio y la luz dice hasta dónde llega hoy. Está escrito con lo que el repositorio puede demostrar (pruebas, compilaciones, ejecuciones), no con lo que está planeado.

🟢 Hecho y verificado · 🟡 Funciona, con límites conocidos · 🟠 Parcial o sin verificar todavía · 🔴 No hecho o no funciona

| Área | Estado | Qué significa aquí |
|---|---|---|
| Software | 🟡 | El detector de movimiento y la capa de decisión funcionan como servicio en el banco de pruebas CM5, pero aún no hay modelo de detección: no distingue una persona de un gato o una rama. |
| Pruebas | 🟢 | Pasan 80 pruebas (`python -m unittest discover -s tests`). |
| Hardware | 🟡 | Mientras el sistema está armado mira fotogramas grises diminutos de las cámaras IP reales del banco de pruebas CM5; nada ha funcionado en una Jetson, con TensorRT ni sobre un flujo RTSP decodificado. |
| Integración | 🟡 | Informa del movimiento ponderado con los radares al servidor del banco de pruebas. |
| Seguridad | 🟡 | El servicio nunca actúa (toda decisión lleva `authorizes_action = false`), rechaza un token de menos de 24 caracteres y una dirección de servidor que no sea `https://` ni esta misma máquina, y nunca guarda una imagen; probado, sin revisión independiente. |
| Documentación | 🟢 | Ocho idiomas y el historial de cambios están al día. |

## 🎯 Resumen

* **El servicio de observación:** `python -m armor_server_ai.service` el servidor nunca lo llama (es él quien le pregunta al servidor, con su propio token): con el sistema **armado** toma un diminuto fotograma gris (64 x 36, del flujo de la cámara, nunca guardado) de cada cámara cada pocos segundos, mide cuánto de la imagen se movió y, cuando las pistas de radar coinciden, lo comunica a ARMOR-SERVER con su token.
* **Zonas de la imagen que se ignoran:** el servidor le da las zonas a ignorar de cada cámara y los píxeles dentro de ellas no cuentan (un árbol que se mueve, una carretera); una imagen casi toda ignorada no se juzga y cuentan como mucho dieciséis zonas.
* **Perfil día/noche con histéresis:** poca luz por debajo de 30 lux, vuelve a día solo por encima de 60 lux y nunca dos veces en 30 s, para que el crepúsculo no lo haga oscilar.
* **Fusión explicable:** cada detección o movimiento y las pistas de radar dan una gravedad (`ignore`, `review`, `high`) con las razones; movimiento fuerte **y** una pista de radar coincidente es `high`, un movimiento más débil es un `review`.
* **Solo recomendaciones:** una decisión siempre lleva `authorizes_action = false`. El servidor central autentica y autoriza cada acción.
* **Motores verificados por suma de comprobación:** los motores TensorRT precompilados solo se aceptan si existen, no están vacíos y, con un `engines.json`, coinciden con su SHA-256. No se compila ni descarga nada.
* **Un servicio que dice qué va mal:** informa de cada problema nuevo cuando cambia (`unreachable`, `unauthorized`…) y *el servidor responde otra vez* cuando termina; un trabajador JSONL guarda resultados numerados y explicados y una línea mala nunca detiene el flujo.

## 🧩 Papel en A.R.M.O.R.

ARMOR-SERVER-AI es la parte que vigila el movimiento en las cámaras mientras la casa está armada. Nunca actúa: dice a [ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER) qué vio y por qué (movimiento y pistas de radar coincidentes es `high`), y el servidor decide qué hacer. Un modelo que reconozca a una persona, ejecutado en una Jetson, es el siguiente paso; [ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION) guarda las zonas, máscaras y reglas que usará ese modelo.

| Habla con | Cómo | Para qué |
|---|---|---|
| ARMOR-SERVER | pregunta al servidor (`/api/v1/ai/*`, token `ARMOR_AI_TOKEN`) | las cámaras, sus fotogramas grises y las zonas a ignorar entran; la observación sale |
| ARMOR-NODE-RADAR | a través del servidor | las pistas de radar y la luz de los nodos que cubren cada cámara |
| ARMOR-VISION | reglas y máscaras (siguiente paso) | las zonas, máscaras y reglas que usará el modelo de detección |
| ARMOR-DEVOPS | lo instala como servicio | despliegue en el banco de la CM5 |

## 🏛️ Arquitectura

<p align="center">
  <img src="images/architecture.svg" alt="ARMOR-SERVER-AI architecture: what it asks the server, the observation service with its modules, and what it tells" width="100%">
</p>

## 🔒 Seguridad y protección

| Amenaza | Defensa |
|---|---|
| El servicio actúa por su cuenta | Nunca: toda decisión lleva `authorizes_action = false`; el servidor central autentica y autoriza cada acción |
| El token cruza una red en claro | `ARMOR_AI_SERVER_URL` debe ser `https://`, o `http://` a esta misma máquina (`127.0.0.1`, `localhost`); si no, el servicio se niega a arrancar |
| Un token débil | `ARMOR_AI_TOKEN` de al menos 24 caracteres (el servidor exige lo mismo) |
| Respuestas enormes del servidor | El contexto se lee hasta 1 000 000 bytes y la respuesta a una observación hasta 65 536; un fotograma son exactamente 64 x 36 = 2304 bytes |
| Imágenes guardadas | El fotograma gris pequeño no se guarda nunca |
| Un motor TensorRT manipulado | Solo motores ya construidos (`daylight`, `low_light`) que existen, no están vacíos y, con un `engines.json`, coinciden en SHA-256; no se compila ni descarga nada |
| Una falsa alarma por un cambio de luz | Un cambio de más del 60 % de la imagen es luz, no movimiento; menos del 1 % no es movimiento; umbral de píxel 18; mínimo 64 píxeles contados; como mucho 16 zonas a ignorar y una imagen casi toda ignorada no se juzga |
| Parpadeo día/noche; datos viejos; una línea JSON hostil | Histéresis (poca luz bajo 30 lux, luz de día de nuevo sobre 60 lux, nunca dos veces en 30 s, lux hasta 200 000); una observación de más de 10 s nunca da alerta; una línea JSON de más de 4096 bytes se rechaza y el flujo sigue |

## 🔌 Interfaces

| Ruta | Autenticación | Qué hace |
|---|---|---|
| `GET /api/v1/ai/context` | token `ARMOR_AI_TOKEN` | las casas: nodos y cámaras, y las zonas a ignorar de cada cámara |
| `GET /api/v1/ai/cameras/<id>/frame` | el mismo | el fotograma gris de 64 x 36 de una cámara (2304 bytes) |
| `POST /api/v1/ai/observations` | el mismo | el informe: lo que vio, la gravedad y las razones |
| `python -m armor_server_ai.service [--once]` | - | el servicio de observación; `--once` hace una pasada y termina |
| `python -m armor_server_ai.cli [--radar-tracks N]` | - | líneas JSON por la entrada estándar (`{"label", "confidence", "lux", "radar_tracks"}`), una decisión numerada y explicada por línea |

Una decisión es `{severity: ignore | review | high, reasons, authorizes_action: false}`. Etiquetas: `person`, `vehicle`, `animal`, `unknown`, `motion`. **Fusión:** `high` es una persona con confianza de 0,80 o más y al menos una pista de radar, o un movimiento fuerte y una pista de radar que coinciden; `review` es una detección confiada (0,55 de día, 0,45 con poca luz) o una pista de radar sin nada visto; el movimiento simple cuenta una pista de radar solo con un 30 % de certeza (cerca del 3 % de la imagen).

## ⚙️ Configuración

| Ajuste | Por defecto | Qué hace |
|---|---|---|
| `ARMOR_AI_TOKEN` | sí (24+ caracteres) | el token que el servidor dio al servicio |
| `ARMOR_AI_SERVER_URL` | http://127.0.0.1:18080 | el servidor; `https://` o esta misma máquina |
| `ARMOR_AI_INTERVAL_S` | 3 (1-60) | segundos entre pasadas; con muchas cámaras la pasada se alarga para no pasar de 200 imágenes por minuto |
| `ARMOR_AI_CONFIRM_FRAMES` | 2 (1-20) | fotogramas seguidos que deben mostrar movimiento antes de avisar |
| `ARMOR_AI_COOLDOWN_S` | 60 (0-3600) | segundos antes de avisar otra vez de la misma cámara |

Un valor fuera de rango detiene el servicio con `<NOMBRE> must be between a and b`. Los umbrales de la decisión (0,80, 0,55, 0,45, la barra del radar del 30 %) y del movimiento (18, 1 %, 60 %) son constantes del código descritas en [docs/INFERENCE_BOUNDARY.md](docs/INFERENCE_BOUNDARY.md); los ajustes del servicio están en [docs/SERVICE.md](docs/SERVICE.md).

## 🚀 Inicio rápido

**Requisitos:** Python 3.11+ (solo biblioteca estándar). Opcional: una Jetson Orin NX con motores TensorRT (no probado).

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests                                                                 # 80 pruebas
echo '{"label":"person","confidence":0.9,"lux":4,"radar_tracks":1}' | python -m armor_server_ai.cli  # una decisión desde una línea
python -m armor_server_ai.service --once                                                             # una pasada del servicio de observación
```

Mira el [límite de la inferencia](docs/INFERENCE_BOUNDARY.md) y el [servicio](docs/SERVICE.md).

## 🧪 Pruebas

```powershell
python -m unittest discover -s tests  # 80 pruebas
python -I tools/armor_ci_validate.py
```

| Fichero de pruebas | Pruebas | Qué cubre |
|---|---|---|
| `test_service.py` | 16 | movimiento, el vigilante, el enfriamiento y qué radares cuentan |
| `test_service_http.py` | 21 | el enlace con el servidor, las reglas de dirección, las pasadas y los ajustes |
| `test_vision_profile.py` | 20 | día y noche con histéresis, la política de fusión y el trabajador |
| `test_cli_worker.py` | 10 | el trabajador de líneas JSON y sus líneas malas |
| `test_ignore_zones.py`, `test_registry.py` | 13 | zonas a ignorar y motores TensorRT comprobados |

GitHub Actions ejecuta la base de A.R.M.O.R. en cada push y pull request: la validación del manifiesto, la versión, el registro de cambios y la paridad de los README, y luego la compilación y las pruebas del propio proyecto.

## 🏗️ Compilación y publicación

Es Python puro: no hay nada que compilar. La versión vive en `pyproject.toml`, en `armor.project.json` y en la insignia del README (leída del manifiesto); cada versión tiene su entrada en [CHANGELOG.md](CHANGELOG.md). Las versiones se publican en GitHub.

## 🩺 Resolución de problemas

| Ves | Porque | Haz |
|---|---|---|
| `armor-ai: watching, every N s` | el servicio arrancó | nada que hacer |
| `ARMOR_AI_TOKEN (at least 24 characters) is needed` | falta el token o es corto | define un token de 24+ caracteres, el mismo que tiene el servidor |
| `ARMOR_AI_SERVER_URL must be https://...` | la dirección enviaría el token en claro por una red | usa `https://`, o `http://127.0.0.1` en la misma máquina |
| `armor-ai: the observation of <camera> could not be told (<code>)` | el informe no llegó al servidor (`unreachable`, `unauthorized`...) | arregla la causa; el siguiente movimiento se avisa sin esperar al enfriamiento; `armor-ai: the server answers again` dice cuándo termina |
| `radar and light sensors not counted: the site design lists no nodes for this camera` | la cámara no nombra nodos en el diseño del emplazamiento | en el Diseñador de emplazamiento de Studio, indica los nodos de radar que cubren la cámara |

## 📂 Estructura del repositorio

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of ARMOR-SERVER-AI" width="100%">
</p>

<details>
<summary>Versión en texto del árbol</summary>

```text
ARMOR-SERVER-AI/
├── src/armor_server_ai/
│   ├── service.py                 el servicio de observación: una pasada por intervalo
│   ├── motion.py                  fotograma gris, zonas a ignorar, movimiento
│   ├── profile.py                 día o poca luz, con histéresis
│   ├── policy.py                  fusión: ignore, review, high
│   ├── engine_registry.py         motores TensorRT comprobados por SHA-256
│   └── cli.py                     el trabajador de líneas JSON
├── tests/                         80 pruebas: movimiento, política, servicio, trabajador
├── docs/                          INFERENCE_BOUNDARY.md, SERVICE.md
├── tools/                         las comprobaciones de CI y las herramientas compartidas
├── images/                        banner, icono y las imágenes del README
├── .github/                       flujo de CI, aviso al panel, plantillas de incidencias y pull requests
├── armor.project.json             manifiesto: versión, función, madurez
├── pyproject.toml                 metadatos del paquete, entradas
├── CHANGELOG.md                   qué cambió en cada versión
├── run.sh run.bat                 arrancar, flujo compartido
├── build.sh build.bat             construir y probar, flujo compartido
├── build-test.sh build-test.bat   construir, probar y empaquetar
├── test.sh test.bat               solo las pruebas, nunca la versión
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE
```

</details>

## 🗺️ Hoja de ruta y límites conocidos

**Límites conocidos hoy**

* No hay modelo de detección: no distingue una persona de un gato o de una rama.
* Nada ha corrido en una Jetson, con TensorRT ni con un flujo RTSP decodificado allí.
* Sin revisión de seguridad independiente.

**Lo siguiente**

* Un modelo que reconozca a una persona, ejecutado en una Jetson Orin NX, con las zonas, máscaras y reglas de ARMOR-VISION.

## 🌍 Idiomas

El README y los textos existen en inglés, español, francés, italiano, alemán, chino, japonés y portugués de Portugal.

## 🔗 Proyectos relacionados

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) es un sistema de seguridad perimetral hecho de repositorios independientes. Cada uno tiene su propia versión, sus propias pruebas y su propio README; esta es la familia:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contratos de mensajes, validadores, vectores de conformidad y tipos generados
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - Firmware de nodo de campo para ESP32-S3 con tres radares y su propio panel web
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - Protocolos de inversores y baterías solares y los mensajes de un nodo pasarela
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - Nodo eléctrico: medidores, el mensaje de las lecturas de la red y las reglas de maniobra
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - Nodo y panel de alarma: zonas, armado, retardos, sirena y PIN, con el servidor o sin él
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - Panel táctil: el estado del sistema en una pantalla de pared, armar y reconocer, y el hogar del asistente de voz
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - La red local: sus dispositivos, internet y lo que cambia
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordinador central: telemetría, alarmas, dispositivos, lecturas solares y cámaras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Consola web: cámaras, radar, alarmas, energía solar y el diseñador 2D/3D del emplazamiento
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Cliente de operador Android con radar 2D/3D en vivo
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - Cliente de operador para iPhone
* **ARMOR-SERVER-AI** (este repositorio) - Política de inferencia visual que explica sus decisiones y nunca actúa
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Zonas de cámara, máscaras y reglas de detección para la Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intenciones de voz sin conexión con una confirmación que no se puede falsificar
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Cajas, electrónica y la matriz de aceptación en banco
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Despliegue, el banco de pruebas de la CM5, copias de seguridad y TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulador de telemetría sin conexión con fallos repetibles
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - Detecta, instala y actualiza los repositorios del propio ecosistema
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Arquitectura, base de seguridad y la matriz de capacidades

## 📚 Documentación

* [Límite de la inferencia](docs/INFERENCE_BOUNDARY.md): qué se decide aquí y qué se deja a un modelo
* [El servicio](docs/SERVICE.md): el servicio de observación y sus ajustes
* [Matriz de capacidades: qué está demostrado y qué no](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catálogo de proyectos: versiones y cómo dependen unos repositorios de otros](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Registro de cambios de este repositorio](CHANGELOG.md)

## 🤝 Contribuir y comunidad

* Antes de un pull request ejecuta `python -I tools/armor_ci_validate.py` y las pruebas: ambos deben pasar. Mira [CONTRIBUTING.md](CONTRIBUTING.md) y el [código de conducta](CODE_OF_CONDUCT.md).
* El README existe en ocho idiomas y se genera desde las fuentes de ARMOR-DOCS: un cambio de texto se hace allí.
* Un cambio en un mensaje entre componentes empieza en ARMOR-COMMON.
* No describas como funcionando en una placa lo que solo se ha compilado.
* Informa de una vulnerabilidad en privado: [SECURITY.md](SECURITY.md). Preguntas, ideas e informes: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENCIA

GPL-3.0-or-later - véase [LICENSE](LICENSE).
