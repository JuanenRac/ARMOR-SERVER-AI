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
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Target-Jetson%20Orin%20NX-76b900.svg" alt="Target">
  <img src="https://img.shields.io/badge/Tests-80%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.2.8-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**Verificação de honestidade - o que funciona hoje:** A camada de decisão e o detetor de movimento são reais e estão testados (80 testes), e o serviço de observação **corre na bancada de testes do CM5**: com o sistema armado olha para pequenas imagens cinzentas das câmaras IP reais e comunica o movimento pesado com os radares. Não distingue uma pessoa de um gato ou de um ramo: **ainda não há modelo de deteção**, e nada correu no Jetson, no TensorRT nem num fluxo RTSP descodificado aí.

---

## 📋 Num relance

| | |
|---|---|
| Versão | `0.2.8` |
| Maturidade | Estabelecido |
| Função | Serviço de observação: movimento ponderado com os radares, só recomenda |
| Tecnologia | Python 3.11+, só biblioteca padrão |
| Testes | 80 (`python -m unittest discover -s tests`) |
| Contrato | Cliente do ARMOR-SERVER: 3 rotas sob `/api/v1/ai/`; ninguém o chama |
| Funciona em | A bancada do CM5 (como serviço, ver ARMOR-DEVOPS) ou qualquer computador |
| Em hardware real | A correr como serviço na bancada de testes do CM5 com as câmaras IP reais (só movimento); nada num Jetson |
| Licença | GPL-3.0-or-later |

**Ir para:** [Visão geral](#-visão-geral) · [Arquitetura](#-arquitetura) · [Segurança](#-segurança-e-proteção) · [Interfaces](#-interfaces) · [Configuração](#-configuração) · [Início rápido](#-início-rápido) · [Testes](#-testes) · [Problemas](#-resolução-de-problemas) · [Estrutura](#-estrutura-do-repositório) · [Relacionados](#-projetos-relacionados)

## 🚦 Estado do projeto

Cada linha é uma parte deste repositório e a luz diz até onde chega hoje. É escrita com o que o repositório consegue demonstrar (testes, compilações, execuções), não com o que está previsto.

🟢 Feito e verificado · 🟡 Funciona, com limites conhecidos · 🟠 Feito a meio ou ainda por verificar · 🔴 Por fazer ou a não funcionar

| Área | Estado | O que significa aqui |
|---|---|---|
| Software | 🟡 | O detetor de movimento e a camada de decisão funcionam como serviço na bancada de testes CM5, mas ainda não há modelo de deteção: não distingue uma pessoa de um gato ou de um ramo. |
| Testes | 🟢 | Passam 80 testes (`python -m unittest discover -s tests`). |
| Hardware | 🟡 | Enquanto o sistema está armado, olha para pequenas imagens cinzentas das câmaras IP reais da bancada de testes CM5; nada funcionou num Jetson, com TensorRT ou sobre um fluxo RTSP descodificado. |
| Integração | 🟡 | Reporta ao servidor da bancada de testes o movimento ponderado com os radares. |
| Segurança | 🟡 | O serviço nunca age (cada decisão leva `authorizes_action = false`), recusa um token com menos de 24 caracteres e um endereço de servidor que não seja `https://` nem esta mesma máquina, e nunca guarda uma imagem; testado, sem revisão independente. |
| Documentação | 🟢 | Oito idiomas e o registo de alterações estão atualizados. |

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

| Fala com | Como | Para quê |
|---|---|---|
| ARMOR-SERVER | pergunta ao servidor (`/api/v1/ai/*`, token `ARMOR_AI_TOKEN`) | as câmaras, as suas imagens cinzentas e as zonas a ignorar entram; a observação sai |
| ARMOR-NODE-RADAR | através do servidor | as pistas de radar e a luz dos nós que cobrem cada câmara |
| ARMOR-VISION | regras e máscaras (próximo passo) | as zonas, máscaras e regras que o modelo de deteção usará |
| ARMOR-DEVOPS | instala-o como serviço | implantação na bancada do CM5 |

## 🏛️ Arquitetura

<p align="center">
  <img src="images/architecture.svg" alt="ARMOR-SERVER-AI architecture: what it asks the server, the observation service with its modules, and what it tells" width="100%">
</p>

## 🔒 Segurança e proteção

| Ameaça | Defesa |
|---|---|
| O serviço age por conta própria | Nunca: cada decisão leva `authorizes_action = false`; o servidor central autentica e autoriza cada ação |
| O token atravessa uma rede em claro | `ARMOR_AI_SERVER_URL` tem de ser `https://`, ou `http://` para esta mesma máquina (`127.0.0.1`, `localhost`); senão o serviço recusa arrancar |
| Um token fraco | `ARMOR_AI_TOKEN` com pelo menos 24 caracteres (o servidor exige o mesmo) |
| Respostas enormes do servidor | O contexto lê-se até 1 000 000 bytes e a resposta a uma observação até 65 536; uma imagem tem exatamente 64 x 36 = 2304 bytes |
| Imagens guardadas | A pequena imagem cinzenta nunca é guardada |
| Um motor TensorRT adulterado | Só motores já construídos (`daylight`, `low_light`) que existam, não estejam vazios e, com um `engines.json`, coincidam no SHA-256; nada é compilado nem descarregado |
| Um falso alarme por mudança de luz | Uma mudança de mais de 60 % da imagem é luz, não movimento; menos de 1 % não é movimento; limiar de píxel 18; pelo menos 64 píxeis contados; no máximo 16 zonas a ignorar e uma imagem quase toda ignorada não é julgada |
| Cintilação dia/noite; dados antigos; uma linha JSON hostil | Histerese (pouca luz abaixo de 30 lux, dia outra vez acima de 60 lux, nunca duas vezes em 30 s, lux até 200 000); uma observação com mais de 10 s nunca dá alerta; uma linha JSON com mais de 4096 bytes é recusada e o fluxo continua |

## 🔌 Interfaces

| Rota | Autenticação | O que faz |
|---|---|---|
| `GET /api/v1/ai/context` | token `ARMOR_AI_TOKEN` | as casas: nós e câmaras, e as zonas a ignorar de cada câmara |
| `GET /api/v1/ai/cameras/<id>/frame` | o mesmo | a imagem cinzenta de 64 x 36 de uma câmara (2304 bytes) |
| `POST /api/v1/ai/observations` | o mesmo | o relatório: o que viu, a gravidade e as razões |
| `python -m armor_server_ai.service [--once]` | - | o serviço de observação; `--once` faz uma passagem e termina |
| `python -m armor_server_ai.cli [--radar-tracks N]` | - | linhas JSON na entrada padrão (`{"label", "confidence", "lux", "radar_tracks"}`), uma decisão numerada e explicada por linha |

Uma decisão é `{severity: ignore | review | high, reasons, authorizes_action: false}`. Etiquetas: `person`, `vehicle`, `animal`, `unknown`, `motion`. **Fusão:** `high` é uma pessoa com confiança de 0,80 ou mais e pelo menos uma pista de radar, ou movimento forte e uma pista de radar que coincidam; `review` é uma deteção confiante (0,55 de dia, 0,45 com pouca luz) ou uma pista de radar sem nada visto; o movimento simples só conta uma pista de radar com 30 % de certeza (cerca de 3 % da imagem).

## ⚙️ Configuração

| Definição | Predefinição | O que faz |
|---|---|---|
| `ARMOR_AI_TOKEN` | sim (24+ caracteres) | o token que o servidor deu ao serviço |
| `ARMOR_AI_SERVER_URL` | http://127.0.0.1:18080 | o servidor; `https://` ou esta mesma máquina |
| `ARMOR_AI_INTERVAL_S` | 3 (1-60) | segundos entre passagens; com muitas câmaras a passagem alarga-se para não passar de 200 imagens por minuto |
| `ARMOR_AI_CONFIRM_FRAMES` | 2 (1-20) | imagens seguidas que têm de mostrar movimento antes de avisar |
| `ARMOR_AI_COOLDOWN_S` | 60 (0-3600) | segundos antes de avisar outra vez da mesma câmara |

Um valor fora do intervalo pára o serviço com `<NOME> must be between a and b`. Os limiares da decisão (0,80, 0,55, 0,45, a barra do radar de 30 %) e do movimento (18, 1 %, 60 %) são constantes do código descritas em [docs/INFERENCE_BOUNDARY.md](docs/INFERENCE_BOUNDARY.md); as definições do serviço estão em [docs/SERVICE.md](docs/SERVICE.md).

## 🚀 Início rápido

**Requisitos:** Python 3.11+ (só biblioteca padrão). Opcional: um Jetson Orin NX com motores TensorRT (não provado).

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests                                                                 # 80 testes
echo '{"label":"person","confidence":0.9,"lux":4,"radar_tracks":1}' | python -m armor_server_ai.cli  # uma decisão a partir de uma linha
python -m armor_server_ai.service --once                                                             # uma passagem do serviço de observação
```

Consulte o [limite da inferência](docs/INFERENCE_BOUNDARY.md) e o [serviço](docs/SERVICE.md).

## 🧪 Testes

```powershell
python -m unittest discover -s tests  # 80 testes
python -I tools/armor_ci_validate.py
```

| Ficheiro de testes | Testes | O que cobre |
|---|---|---|
| `test_service.py` | 16 | movimento, o vigilante, o arrefecimento e que radares contam |
| `test_service_http.py` | 21 | a ligação ao servidor, as regras de endereço, as passagens e as definições |
| `test_vision_profile.py` | 20 | dia e noite com histerese, a política de fusão e o trabalhador |
| `test_cli_worker.py` | 10 | o trabalhador de linhas JSON e as suas linhas más |
| `test_ignore_zones.py`, `test_registry.py` | 13 | zonas a ignorar e motores TensorRT verificados |

O GitHub Actions executa a base do A.R.M.O.R. em cada push e pull request: a validação do manifesto, da versão, do registo de alterações e da paridade dos README, e depois a compilação e os testes do próprio projeto.

## 🏗️ Compilação e publicação

É Python puro: não há nada para compilar. A versão está em `pyproject.toml`, em `armor.project.json` e no emblema do README (lido do manifesto); cada versão tem a sua entrada em [CHANGELOG.md](CHANGELOG.md). As versões são publicadas no GitHub.

## 🩺 Resolução de problemas

| Vê | Porque | Faça |
|---|---|---|
| `armor-ai: watching, every N s` | o serviço arrancou | nada a fazer |
| `ARMOR_AI_TOKEN (at least 24 characters) is needed` | falta o token ou é curto | defina um token de 24+ caracteres, o mesmo que o servidor tem |
| `ARMOR_AI_SERVER_URL must be https://...` | o endereço enviaria o token em claro por uma rede | use `https://`, ou `http://127.0.0.1` na mesma máquina |
| `armor-ai: the observation of <camera> could not be told (<code>)` | o relatório não chegou ao servidor (`unreachable`, `unauthorized`...) | corrija a causa; o movimento seguinte é avisado sem esperar o arrefecimento; `armor-ai: the server answers again` diz quando acabou |
| `radar and light sensors not counted: the site design lists no nodes for this camera` | a câmara não nomeia nós no desenho do local | no desenhador do local do Studio, indique os nós de radar que cobrem a câmara |

## 📂 Estrutura do repositório

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of ARMOR-SERVER-AI" width="100%">
</p>

<details>
<summary>Versão em texto da árvore</summary>

```text
ARMOR-SERVER-AI/
├── src/armor_server_ai/
│   ├── service.py                 o serviço de observação: uma passagem por intervalo
│   ├── motion.py                  imagem cinzenta, zonas a ignorar, movimento
│   ├── profile.py                 dia ou pouca luz, com histerese
│   ├── policy.py                  fusão: ignore, review, high
│   ├── engine_registry.py         motores TensorRT verificados por SHA-256
│   └── cli.py                     o trabalhador de linhas JSON
├── tests/                         80 testes: movimento, política, serviço, trabalhador
├── docs/                          INFERENCE_BOUNDARY.md, SERVICE.md
├── tools/                         as verificações de CI e as ferramentas partilhadas
├── images/                        faixa, ícone e as imagens do README
├── .github/                       fluxo de CI, aviso ao painel, modelos de issues e pull requests
├── armor.project.json             manifesto: versão, função, maturidade
├── pyproject.toml                 metadados do pacote, entradas
├── CHANGELOG.md                   o que mudou em cada versão
├── run.sh run.bat                 arrancar, fluxo partilhado
├── build.sh build.bat             compilar e testar, fluxo partilhado
├── build-test.sh build-test.bat   compilar, testar e empacotar
├── test.sh test.bat               só os testes, nunca a versão
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE
```

</details>

## 🗺️ Roteiro e limites conhecidos

**Limites conhecidos hoje**

* Não há modelo de deteção: não distingue uma pessoa de um gato ou de um ramo.
* Nada correu num Jetson, com TensorRT nem num fluxo RTSP descodificado lá.
* Sem revisão de segurança independente.

**A seguir**

* Um modelo que reconheça uma pessoa, executado num Jetson Orin NX, com as zonas, máscaras e regras do ARMOR-VISION.

## 🌍 Idiomas

O README e os textos existem em inglês, espanhol, francês, italiano, alemão, chinês, japonês e português europeu.

## 🔗 Projetos relacionados

O **A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) é um sistema de segurança perimetral feito de repositórios independentes. Cada um tem a sua própria versão, os seus próprios testes e o seu próprio README; esta é a família:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contratos de mensagens, validadores, vetores de conformidade e tipos gerados
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - Firmware de nó de campo para ESP32-S3 com três radares e o seu próprio painel web
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - Protocolos de inversores e baterias solares e as mensagens de um nó porta de ligação
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - Nó elétrico: contadores, a mensagem das leituras da rede e as regras de comutação
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - Nó e painel de alarme: zonas, armar, atrasos, sirene e PIN, com o servidor ou sem ele
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - Painel tátil: o estado do sistema num ecrã de parede, armar e reconhecer, e a casa do assistente de voz
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - A rede local: os seus dispositivos, a internet e o que muda
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordenador central: telemetria, alarmes, dispositivos, leituras solares e câmaras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Consola web: câmaras, radar, alarmes, energia solar e o desenhador 2D/3D do local
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Cliente de operador Android com radar 2D/3D em direto
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - Cliente de operador para iPhone
* **ARMOR-SERVER-AI** (este repositório) - Política de inferência visual que explica as suas decisões e nunca atua
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Zonas de câmara, máscaras e regras de deteção para o Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intenções de voz offline com uma confirmação que não pode ser falsificada
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Caixas, eletrónica e a matriz de aceitação em bancada
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Implantação, a bancada de testes do CM5, cópias de segurança e TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulador de telemetria offline com falhas repetíveis
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - Deteta, instala e atualiza os repositórios do próprio ecossistema
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Arquitetura, base de segurança e a matriz de capacidades

## 📚 Documentação

* [Limite da inferência](docs/INFERENCE_BOUNDARY.md): o que se decide aqui e o que fica para um modelo
* [O serviço](docs/SERVICE.md): o serviço de observação e as suas definições
* [Matriz de capacidades: o que está demonstrado e o que não está](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catálogo de projetos: versões e como os repositórios dependem uns dos outros](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Registo de alterações deste repositório](CHANGELOG.md)

## 🤝 Contribuir e comunidade

* Antes de um pull request execute `python -I tools/armor_ci_validate.py` e os testes: ambos têm de passar. Consulte [CONTRIBUTING.md](CONTRIBUTING.md) e o [código de conduta](CODE_OF_CONDUCT.md).
* O README existe em oito idiomas e é gerado a partir das fontes do ARMOR-DOCS: uma alteração ao texto faz-se lá.
* Uma alteração a uma mensagem entre componentes começa no ARMOR-COMMON.
* Não descreva como a funcionar numa placa aquilo que só foi compilado.
* Comunique uma vulnerabilidade em privado: [SECURITY.md](SECURITY.md). Perguntas, ideias e relatórios: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENÇA

GPL-3.0-or-later - consulte [LICENSE](LICENSE).
