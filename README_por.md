<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-SERVER-AI banner" width="100%">
</p>

# 👁️ ARMOR-SERVER-AI

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  🇵🇹 <b>Português</b>
</p>

### Serviço de observação: o movimento nas câmaras pesado com os radares; decide e explica, nunca aciona

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Target-Jetson%20Orin%20NX-76b900.svg" alt="Target">
  <img src="https://img.shields.io/badge/Tests-77%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.2.6-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**Verificação de honestidade - o que funciona hoje:** A camada de decisão e o detetor de movimento são reais e estão testados (77 testes), e o serviço de observação **corre na bancada de testes do CM5**: com o sistema armado olha para pequenas imagens cinzentas das câmaras IP reais e comunica o movimento pesado com os radares. Não distingue uma pessoa de um gato ou de um ramo: **ainda não há modelo de deteção**, e nada correu no Jetson, no TensorRT nem num fluxo RTSP descodificado aí.

---

## 📋 Num relance

| | |
|---|---|
| Versão | `0.2.6` |
| Maturidade | Estabelecido |
| Testes | 77 (`python -m unittest discover -s tests`) |
| Tecnologia | Python 3.11+ (standard library) |
| Em hardware real | A correr como serviço na bancada de testes do CM5 com as câmaras IP reais (só movimento); nada num Jetson |

## 🎯 Visão geral

* **O serviço de observação:** `python -m armor_server_ai.service` nunca é chamado pelo servidor (é ele que pergunta ao servidor, com o seu próprio token): com o sistema **armado** tira uma pequena imagem cinzenta (64 x 36, do fluxo da câmara, nunca guardada) de cada câmara de poucos em poucos segundos, mede quanto da imagem se moveu e, quando as pistas de radar coincidem, comunica-o ao ARMOR-SERVER com o seu token.
* **Zonas da imagem a ignorar:** o servidor dá-lhe as zonas a ignorar de cada câmara e os píxeis dentro delas não contam (uma árvore que se mexe, uma estrada); uma imagem quase toda ignorada não é julgada e contam no máximo dezasseis zonas.
* **Perfil dia/noite com histerese:** pouca luz abaixo de 30 lux, volta ao dia só acima de 60 lux e nunca duas vezes em 30 s, para que o crepúsculo não o faça oscilar.
* **Fusão explicável:** cada deteção ou movimento e as pistas de radar dão uma gravidade (`ignore`, `review`, `high`) com as razões; movimento forte **e** uma pista de radar coincidente é `high`, um movimento mais fraco é um `review`.
* **Só recomendações:** uma decisão leva sempre `authorizes_action = false`. O servidor central autentica e autoriza cada ação.
* **Motores verificados por soma de verificação:** os motores TensorRT pré-compilados só são aceites se existirem, não estiverem vazios e, com um `engines.json`, coincidirem com o seu SHA-256. Nada é compilado nem descarregado.
* **Um serviço que diz o que está mal:** comunica cada novo problema quando muda (`unreachable`, `unauthorized`…) e *o servidor responde outra vez* quando acaba; um trabalhador JSONL guarda resultados numerados e explicados e uma linha má nunca para o fluxo.

## 🧩 Papel no A.R.M.O.R.

O ARMOR-SERVER-AI é a parte que vigia o movimento nas câmaras enquanto a casa está armada. Nunca age: diz ao [ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER) o que viu e porquê (movimento e pistas de radar coincidentes é `high`), e o servidor decide o que fazer. Um modelo que reconheça uma pessoa, executado num Jetson, é o passo seguinte; o [ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION) guarda as zonas, máscaras e regras que esse modelo usará.

## 📂 Estrutura do repositório

```text
ARMOR-SERVER-AI/
├── src/armor_server_ai/   profile (day/night), policy (fusion), motion (movement and ignore zones), engine_registry, service (the observation service), cli
├── tests/                 77 tests
└── docs/                  INFERENCE_BOUNDARY.md, SERVICE.md
```

## 🛠️ Ambiente de desenvolvimento

**Requisitos:** Python 3.11+, optional: a Jetson Orin NX with TensorRT engines (not proven)

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests   # 77 tests
echo '{"label":"person","confidence":0.9,"lux":4,"radar_tracks":1}' | python -m armor_server_ai.cli
python -m armor_server_ai.service --once   # one pass of the observation service
```

Veja o [limite da inferência](docs/INFERENCE_BOUNDARY.md) e o [serviço](docs/SERVICE.md).

## 🔗 Projetos relacionados

O **A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) é um sistema de segurança perimetral feito de repositórios independentes. Cada um tem a sua própria versão, os seus próprios testes e o seu próprio README; esta é a família:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contratos de mensagens, validadores, vetores de conformidade e tipos gerados
* **[ARMOR-RADAR](https://github.com/JuanenRac/ARMOR-RADAR)** - Firmware de nó de campo para ESP32-S3 com três radares e o seu próprio painel web
* **[ARMOR-SOLAR](https://github.com/JuanenRac/ARMOR-SOLAR)** - Protocolos de inversores e baterias solares e as mensagens de um nó de ligação
* **[ARMOR-ELECTRICAL](https://github.com/JuanenRac/ARMOR-ELECTRICAL)** - Nó elétrico: contadores, a mensagem das leituras da rede e as regras de comutação
* **[ARMOR-ALARM](https://github.com/JuanenRac/ARMOR-ALARM)** - Nó e central de alarme: zonas, armar, atrasos, sirene e PIN, com o servidor ou sem ele
* **[ARMOR-HMI](https://github.com/JuanenRac/ARMOR-HMI)** - Painel tátil: o estado do sistema num ecrã de parede, armar e reconhecer, e a casa do assistente de voz
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - A rede local: os seus dispositivos, a internet e o que muda
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordenador central: telemetria, alarmes, dispositivos, leituras solares e câmaras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Consola web: câmaras, radar, alarmes, energia solar e o desenhador de local 2D/3D
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Cliente Android de operador com um radar 2D/3D em direto
* **ARMOR-SERVER-AI** (este repositório) - Política de inferência visual que explica as suas decisões e nunca atua
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Zonas de câmara, máscaras e regras de deteção para o Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intenções de voz offline com uma confirmação que não se pode falsificar
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Caixas, eletrónica e a matriz de aceitação de bancada
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Implementação, a bancada de testes CM5, cópias de segurança e TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulador de telemetria offline com falhas repetíveis
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - Deteta, instala e atualiza os próprios repositórios do ecossistema
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Arquitetura, linha de base de segurança e a matriz de capacidades

## 📚 Documentação e comunidade

Onde ler mais:

* [Matriz de capacidades: o que está provado e o que não](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catálogo de projetos: versões e como os repositórios dependem uns dos outros](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Registo de alterações deste repositório](CHANGELOG.md)
* [Licença (GPL-3.0-or-later)](LICENSE)
* Perguntas, ideias e relatórios: electrohobby3d@gmail.com

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENÇA

GPL-3.0-or-later - veja [LICENSE](LICENSE).
