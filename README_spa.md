<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-SERVER-AI banner" width="100%">
</p>

# 👁️ ARMOR-SERVER-AI

<p align="center"><a href="README.md">🇺🇸 English</a> | 🇪🇸 <b>Español</b></p>

### Política de inferencia visual: decide y explica, nunca actúa

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Target-Jetson%20Orin%20NX-76b900.svg" alt="Target">
  <img src="https://img.shields.io/badge/Maturity-functional%20baseline-00E5FF.svg" alt="Maturity">
</p>

---

**Comprobación de honestidad - qué funciona hoy:** La capa de decisión es real y está probada (26 tests). **Nada de esto ejecuta todavía una cámara, RTSP ni TensorRT**: eso necesita la Jetson y no está demostrado.

---

## 1. 🛠️ DESCRIPCIÓN

* **Perfil día/noche con histéresis:** poca luz por debajo de 30 lux, vuelve a luz diurna solo por encima de 60 lux y nunca dos veces en 30 s, de modo que el anochecer no lo hace oscilar.
* **Fusión explicable:** cada detección y las pistas de radar dan una severidad (`ignore`, `review`, `high`) con sus motivos. Una persona vista al 80 % o más **y** una pista de radar es `high`; con poca luz solo baja el umbral de revisión; una detección de más de 10 s se ignora.
* **Solo recomendaciones:** una decisión lleva siempre `authorizes_action = false`. El servidor central autentica y autoriza cada acción.
* **Motores verificados por hash:** los motores TensorRT precompilados solo se aceptan si existen, no están vacíos y, con un `engines.json`, coinciden con su SHA-256. No se compila ni se descarga nada.
* **Trabajador JSONL:** resultados numerados y explicados; una línea errónea indica su número y nunca detiene el flujo.

---

## 2. 🔧 COMPILAR Y EJECUTAR

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests
echo '{"label":"person","confidence":0.9,"lux":4,"radar_tracks":1}' | python -m armor_server_ai.cli
```

Véase el [límite de inferencia](docs/INFERENCE_BOUNDARY.md).

---

## 📂 ESTRUCTURA DE DIRECTORIOS

```text
ARMOR-SERVER-AI/
├── src/armor_server_ai/   profile, policy, engine_registry, cli
├── tests/
└── docs/INFERENCE_BOUNDARY.md
```

---

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENCIA

GPL-3.0-or-later - véase [LICENSE](LICENSE).
