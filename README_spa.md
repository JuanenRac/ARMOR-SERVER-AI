<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-SERVER-AI banner" width="100%">
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
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Target-Jetson%20Orin%20NX-76b900.svg" alt="Target">
  <img src="https://img.shields.io/badge/Tests-42%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.2.5-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**Comprobación de honestidad - qué funciona hoy:** La capa de decisión y el detector de movimiento son reales y están probados (42 tests), y el servicio de observación **corre en el banco de pruebas de la CM5**: con el sistema armado mira pequeños fotogramas grises de las cámaras IP reales e informa del movimiento sopesado con los radares. No distingue a una persona de un gato o una rama: **todavía no hay modelo de detección**, y nada ha corrido en la Jetson, TensorRT ni un flujo RTSP decodificado allí.

---

## 📋 De un vistazo

| | |
|---|---|
| Versión | `0.2.5` |
| Madurez | Establecido |
| Tests | 42 (`python -m unittest discover -s tests`) |
| Tecnología | Python 3.11+ / Docker |
| En hardware real | Corriendo como servicio en el banco de pruebas de la CM5 con las cámaras IP reales (solo movimiento); nada en una Jetson |

## 🎯 Descripción general

* **El servicio de observación:** `python -m armor_server_ai.service` no pide nada al servidor y nadie le pide nada: con el sistema **armado** toma un diminuto fotograma gris (64 x 36, del flujo de la cámara, nunca guardado) de cada cámara cada pocos segundos, mide cuánto de la imagen se movió y, cuando las pistas de radar coinciden, lo comunica a ARMOR-SERVER con su token.
* **Zonas de la imagen que se ignoran:** el servidor le da las zonas a ignorar de cada cámara y los píxeles dentro de ellas no cuentan (un árbol que se mueve, una carretera); una imagen casi toda ignorada no se juzga y cuentan como mucho dieciséis zonas.
* **Perfil día/noche con histéresis:** poca luz por debajo de 30 lux, vuelve a día solo por encima de 60 lux y nunca dos veces en 30 s, para que el crepúsculo no lo haga oscilar.
* **Fusión explicable:** cada detección o movimiento y las pistas de radar dan una gravedad (`ignore`, `review`, `high`) con las razones; movimiento fuerte **y** una pista de radar coincidente es `high`, un movimiento más débil es un `review`.
* **Solo recomendaciones:** una decisión siempre lleva `authorizes_action = false`. El servidor central autentica y autoriza cada acción.
* **Motores verificados por suma de comprobación:** los motores TensorRT precompilados solo se aceptan si existen, no están vacíos y, con un `engines.json`, coinciden con su SHA-256. No se compila ni descarga nada.
* **Un servicio que dice qué va mal:** informa de cada problema nuevo cuando cambia (`unreachable`, `unauthorized`…) y *el servidor responde otra vez* cuando termina; un trabajador JSONL guarda resultados numerados y explicados y una línea mala nunca detiene el flujo.

## 🧩 Papel en A.R.M.O.R.

ARMOR-SERVER-AI es la parte que vigila el movimiento en las cámaras mientras la casa está armada. Nunca actúa: dice a [ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER) qué vio y por qué (movimiento y pistas de radar coincidentes es `high`), y el servidor decide qué hacer. Un modelo que reconozca a una persona, ejecutado en una Jetson, es el siguiente paso; [ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION) guarda las zonas, máscaras y reglas que usará ese modelo.

## 📂 Estructura del repositorio

```text
ARMOR-SERVER-AI/
├── src/armor_server_ai/   profile (day/night), policy (fusion), motion (movement and ignore zones), engine_registry, service (the observation service), cli
├── tests/                 42 tests
└── docs/                  INFERENCE_BOUNDARY.md, SERVICE.md
```

## 🛠️ Entorno de desarrollo

**Requisitos:** Python 3.11+, optional: a Jetson Orin NX with TensorRT engines (not proven)

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests   # 42 tests
echo '{"label":"person","confidence":0.9,"lux":4,"radar_tracks":1}' | python -m armor_server_ai.cli
python -m armor_server_ai.service --once   # one pass of the observation service
```

Véanse el [límite de la inferencia](docs/INFERENCE_BOUNDARY.md) y el [servicio](docs/SERVICE.md).

## 🔗 Proyectos relacionados

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) es un sistema de seguridad perimetral hecho de repositorios independientes. Cada uno tiene su propia versión, sus propias pruebas y su propio README; esta es la familia:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contratos de mensajes, validadores, vectores de conformidad y tipos generados
* **[ARMOR-RADAR](https://github.com/JuanenRac/ARMOR-RADAR)** - Firmware del nodo de campo para ESP32-S3 con tres radares y su propio panel web
* **[ARMOR-SOLAR](https://github.com/JuanenRac/ARMOR-SOLAR)** - Protocolos de inversores y baterías solares y los mensajes de un nodo pasarela
* **[ARMOR-ELECTRICAL](https://github.com/JuanenRac/ARMOR-ELECTRICAL)** - Nodo eléctrico: contadores, el mensaje de las lecturas de la red y las reglas para maniobrar
* **[ARMOR-ALARM](https://github.com/JuanenRac/ARMOR-ALARM)** - Nodo y central de alarma: zonas, armado, retardos, sirena y PIN, con el servidor o sin él
* **[ARMOR-HMI](https://github.com/JuanenRac/ARMOR-HMI)** - Panel táctil: el estado del sistema en una pantalla de pared, armar y reconocer alarmas, y el hogar del asistente de voz
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - La red local: sus dispositivos, internet y lo que cambia
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordinador central: telemetría, alarmas, dispositivos, lecturas solares y cámaras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Consola web: cámaras, radar, alarmas, energía solar y el diseñador de sitio 2D/3D
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Cliente Android del operador con radar 2D/3D en vivo
* **ARMOR-SERVER-AI** (este repositorio) - Política de inferencia visual que explica sus decisiones y nunca actúa
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Zonas de cámara, máscaras y reglas de detección para la Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intenciones de voz sin conexión con una confirmación imposible de falsificar
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Cajas, electrónica y la matriz de aceptación en banco
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Despliegue, el banco de pruebas de la CM5, copias de seguridad y TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulador de telemetría sin conexión con fallos repetibles
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - Detecta, instala y actualiza los propios repositorios del ecosistema
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Arquitectura, base de seguridad y la matriz de capacidades

## 📚 Documentación y comunidad

Dónde leer más:

* [Matriz de capacidades: qué está probado y qué no](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catálogo de proyectos: versiones y cómo dependen unos de otros](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Historial de cambios de este repositorio](CHANGELOG.md)
* [Licencia (GPL-3.0-or-later)](LICENSE)
* Preguntas, ideas e informes: electrohobby3d@gmail.com

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENCIA

GPL-3.0-or-later - véase [LICENSE](LICENSE).
