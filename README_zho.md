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
  🇨🇳 <b>简体中文</b> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### 观察服务：把摄像头上的移动与雷达对照权衡；它做出决定并给出解释，从不执行动作

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Target-Jetson%20Orin%20NX-76b900.svg" alt="Target">
  <img src="https://img.shields.io/badge/Tests-80%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.2.7-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**诚实性检查 - 今天真正能运行的部分：** 决策层和移动检测器是真实的并经过测试（80 个测试），观察服务**在 CM5 测试台上运行**：系统布防时，它查看真实 IP 摄像头的微小灰度帧，并报告与雷达对照权衡后的移动。它分不清人、猫或树枝：**目前还没有检测模型**，也没有任何东西在 Jetson、TensorRT 或在那里解码的 RTSP 流上运行过。

---

## 📋 速览

| | |
|---|---|
| 版本 | `0.2.7` |
| 成熟度 | 成熟 |
| 角色 | 观察服务：结合雷达评估运动，只给出建议 |
| 技术栈 | Python 3.11+，仅用标准库 |
| 测试 | 80 项（`python -m unittest discover -s tests`） |
| 契约 | ARMOR-SERVER 的客户端：`/api/v1/ai/` 下的 3 条路由；从不被调用 |
| 运行位置 | CM5 测试台（作为服务，见 ARMOR-DEVOPS）或任何计算机 |
| 真实硬件 | 在 CM5 测试台上用真实 IP 摄像头作为服务运行（仅移动）；Jetson 上没有任何东西 |
| 许可证 | GPL-3.0-or-later |

**跳转到：** [概述](#-概述) · [架构](#-架构) · [安全](#-安全与防护) · [接口](#-接口) · [配置](#-配置) · [快速开始](#-快速开始) · [测试](#-测试) · [故障排除](#-故障排除) · [结构](#-仓库结构) · [相关项目](#-相关项目)

## 🚦 项目状态

每一行是本仓库的一个部分，灯号表示它今天做到了哪一步。内容依据仓库能够展示的证据（测试、构建、运行），而不是计划。

🟢 已完成并验证 · 🟡 可用，有已知限制 · 🟠 部分完成或尚未验证 · 🔴 未完成或不可用

| 领域 | 状态 | 在这里的含义 |
|---|---|---|
| 软件 | 🟡 | 移动检测器和决策层在 CM5 测试台上作为服务运行，但目前还没有检测模型：它分不清人、猫或树枝。 |
| 测试 | 🟢 | 80 项测试通过（`python -m unittest discover -s tests`）。 |
| 硬件 | 🟡 | 系统布防期间，它查看 CM5 测试台上真实 IP 摄像头的微小灰度画面；还没有在 Jetson、TensorRT 或解码后的 RTSP 流上运行过。 |
| 集成 | 🟡 | 它把结合雷达加权后的移动情况报告给测试台的服务器。 |
| 安全 | 🟡 | 该服务从不执行动作（每个判定都带 `authorizes_action = false`），拒绝少于 24 个字符的令牌以及既不是 `https://` 也不是本机的服务器地址，从不保存图片；已测试，没有独立审查。 |
| 文档 | 🟢 | 八种语言和更新日志均为最新。 |

## 🎯 概述

* **观察服务：**`python -m armor_server_ai.service` 服务器从不调用它（是它用自己的令牌向服务器询问）：系统**布防**时，它每隔几秒从每个摄像头的码流取一帧微小的灰度图（64 x 36，从不保存），测量画面移动了多少，当雷达轨迹一致时，带着自己的令牌上报给 ARMOR-SERVER。
* **要忽略的画面区域：**服务器把每个摄像头的忽略区域交给它，区域内的像素不计入（摇动的树、公路）；几乎全被忽略的画面不做判断，最多计入十六个区域。
* **带滞回的昼夜配置：**低于 30 勒克斯为弱光，只有高于 60 勒克斯才回到白天，且 30 秒内绝不切换两次，因此黄昏不会让它来回抖动。
* **可解释的融合：**每次检测或移动与雷达轨迹给出一个严重级别（`ignore`、`review`、`high`）及理由；强移动**并且**有一致的雷达轨迹为 `high`，较弱的移动为 `review`。
* **只是建议：**决定总是带有 `authorizes_action = false`。中央服务器对每个动作进行认证和授权。
* **经校验和验证的引擎：**预先构建的 TensorRT 引擎只有在存在、非空，并且（有 `engines.json` 时）SHA-256 匹配时才会被接受。不会编译或下载任何东西。
* **会说明出了什么问题的服务：**每个新问题变化时都会报告（`unreachable`、`unauthorized`……），结束时会说明*服务器又有应答了*；JSONL 工作进程保留编号并带解释的结果，坏的一行绝不会中断数据流。

## 🧩 在 A.R.M.O.R. 中的角色

ARMOR-SERVER-AI 是在住宅布防时观察摄像头移动的部分。它从不行动：它告诉 [ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER) 它看到了什么以及原因（移动与雷达轨迹一致即为 `high`），由服务器决定怎么做。下一步是在 Jetson 上运行能识别人的模型；[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION) 保存该模型将使用的区域、遮罩和规则。

| 对话对象 | 方式 | 用途 |
|---|---|---|
| ARMOR-SERVER | 向服务器查询（`/api/v1/ai/*`，令牌 `ARMOR_AI_TOKEN`） | 摄像头、其灰度帧和忽略区进来，观察结果出去 |
| ARMOR-NODE-RADAR | 经服务器 | 覆盖每台摄像头的节点的雷达轨迹和光照 |
| ARMOR-VISION | 规则与遮罩（下一步） | 检测模型将使用的区域、遮罩和规则 |
| ARMOR-DEVOPS | 将其安装为服务 | 在 CM5 测试台上部署 |

## 🏛️ 架构

<p align="center">
  <img src="images/architecture.svg" alt="ARMOR-SERVER-AI architecture: what it asks the server, the observation service with its modules, and what it tells" width="100%">
</p>

## 🔒 安全与防护

| 威胁 | 防御 |
|---|---|
| 服务自行行动 | 绝不：每个判定都带 `authorizes_action = false`；每个动作都由中央服务器认证并授权 |
| 令牌以明文穿过网络 | `ARMOR_AI_SERVER_URL` 必须是 `https://`，或指向本机的 `http://`（`127.0.0.1`、`localhost`）；否则服务拒绝启动 |
| 弱令牌 | `ARMOR_AI_TOKEN` 至少 24 个字符（服务器同样要求） |
| 服务器返回超大响应 | 上下文最多读取 1 000 000 字节，对观察的响应最多 65 536 字节；一帧恰好是 64 x 36 = 2304 字节 |
| 被保存的图片 | 小灰度帧从不保存 |
| 被篡改的 TensorRT 引擎 | 只接受已构建好的引擎（`daylight`、`low_light`）：存在、非空，有 `engines.json` 时 SHA-256 须一致；不编译也不下载 |
| 光线变化造成的误报 | 画面超过 60 % 的变化是光线而非运动；不足 1 % 不算运动；像素阈值 18；至少统计 64 个像素；最多 16 个忽略区，几乎全被忽略的画面不做判断 |
| 昼夜抖动；过期数据；恶意 JSON 行 | 迟滞（低于 30 lux 为弱光，高于 60 lux 才回到白天，30 秒内不会切换两次，照度至多 200 000）；超过 10 秒的观察从不触发警报；超过 4096 字节的 JSON 行被拒绝，流继续 |

## 🔌 接口

| 路由 | 认证 | 作用 |
|---|---|---|
| `GET /api/v1/ai/context` | 令牌 `ARMOR_AI_TOKEN` | 各住宅的节点和摄像头，以及每台摄像头的忽略区 |
| `GET /api/v1/ai/cameras/<id>/frame` | 同上 | 摄像头的 64 x 36 灰度帧（2304 字节） |
| `POST /api/v1/ai/observations` | 同上 | 报告：看到了什么、严重程度和原因 |
| `python -m armor_server_ai.service [--once]` | - | 观察服务；`--once` 只运行一轮就结束 |
| `python -m armor_server_ai.cli [--radar-tracks N]` | - | 标准输入的 JSON 行（`{"label", "confidence", "lux", "radar_tracks"}`），每行一个带编号并有说明的判定 |

判定为 `{severity: ignore | review | high, reasons, authorizes_action: false}`。标签：`person`、`vehicle`、`animal`、`unknown`、`motion`。**融合：** `high` 是置信度不低于 0.80 且至少有一条雷达轨迹的人，或强运动与雷达轨迹一致；`review` 是有把握的检测（白天 0.55、弱光 0.45）或看不到任何东西的雷达轨迹；单纯的运动只有在 30 % 把握（约占画面 3 %）时才计入雷达轨迹。

## ⚙️ 配置

| 设置 | 默认值 | 作用 |
|---|---|---|
| `ARMOR_AI_TOKEN` | 是（24 个以上字符） | 服务器给服务的令牌 |
| `ARMOR_AI_SERVER_URL` | http://127.0.0.1:18080 | 服务器；`https://` 或本机 |
| `ARMOR_AI_INTERVAL_S` | 3 (1-60) | 两轮之间的秒数；摄像头多时会拉长，使每分钟不超过 200 帧 |
| `ARMOR_AI_CONFIRM_FRAMES` | 2 (1-20) | 报告前必须连续显示运动的帧数 |
| `ARMOR_AI_COOLDOWN_S` | 60 (0-3600) | 同一摄像头再次报告前的秒数 |

取值超出范围时，服务会以 `<名称> must be between a and b` 停止。判定阈值（0.80、0.55、0.45，雷达门槛 30 %）和运动阈值（18、1 %、60 %）是代码中的常量，见 [docs/INFERENCE_BOUNDARY.md](docs/INFERENCE_BOUNDARY.md)；服务的设置见 [docs/SERVICE.md](docs/SERVICE.md)。

## 🚀 快速开始

**要求：** Python 3.11+（仅标准库）。可选：带 TensorRT 引擎的 Jetson Orin NX（未验证）。

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests                                                                 # 80 项
echo '{"label":"person","confidence":0.9,"lux":4,"radar_tracks":1}' | python -m armor_server_ai.cli  # 从一行得到一个判定
python -m armor_server_ai.service --once                                                             # 观察服务运行一轮
```

请参阅[推理边界](docs/INFERENCE_BOUNDARY.md)和[服务](docs/SERVICE.md)。

## 🧪 测试

```powershell
python -m unittest discover -s tests  # 80 项
python -I tools/armor_ci_validate.py
```

| 测试文件 | 测试数 | 覆盖内容 |
|---|---|---|
| `test_service.py` | 16 | 运动、监视器、冷却时间以及哪些雷达计入 |
| `test_service_http.py` | 21 | 与服务器的连接、地址规则、轮次与设置 |
| `test_vision_profile.py` | 20 | 带迟滞的昼夜、融合策略与工作进程 |
| `test_cli_worker.py` | 10 | JSON 行工作进程及其坏行 |
| `test_ignore_zones.py`, `test_registry.py` | 13 | 忽略区与经校验的 TensorRT 引擎 |

GitHub Actions 在每次推送和拉取请求时运行 A.R.M.O.R. 基线：清单、版本、更新日志和 README 一致性的校验，然后是项目自身的构建和测试。

## 🏗️ 构建与发布

这是纯 Python：无需编译。版本记录在 `pyproject.toml`、`armor.project.json` 和 README 徽章中（读取自清单）；每个版本在 [CHANGELOG.md](CHANGELOG.md) 中都有对应条目。发布版本发布在 GitHub 上。

## 🩺 故障排除

| 你看到 | 原因 | 处理 |
|---|---|---|
| `armor-ai: watching, every N s` | 服务已启动 | 无需处理 |
| `ARMOR_AI_TOKEN (at least 24 characters) is needed` | 缺少令牌或令牌太短 | 设置 24 个以上字符的令牌，与服务器所持相同 |
| `ARMOR_AI_SERVER_URL must be https://...` | 该地址会让令牌以明文穿过网络 | 使用 `https://`，或同机的 `http://127.0.0.1` |
| `armor-ai: the observation of <camera> could not be told (<code>)` | 报告未到达服务器（`unreachable`、`unauthorized` 等） | 排除原因；下一次运动不等冷却时间就会报告，`armor-ai: the server answers again` 表示已恢复 |
| `radar and light sensors not counted: the site design lists no nodes for this camera` | 场地设计中该摄像头没有指定节点 | 在 Studio 的场地设计器中列出覆盖该摄像头的雷达节点 |

## 📂 仓库结构

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of ARMOR-SERVER-AI" width="100%">
</p>

<details>
<summary>目录树的文本版本</summary>

```text
ARMOR-SERVER-AI/
├── src/armor_server_ai/
│   ├── service.py                 观察服务：每个间隔一轮
│   ├── motion.py                  灰度帧、忽略区、运动量
│   ├── profile.py                 白天或弱光，带迟滞
│   ├── policy.py                  融合：ignore、review、high
│   ├── engine_registry.py         以 SHA-256 校验的 TensorRT 引擎
│   └── cli.py                     JSON 行工作进程
├── tests/                         80 项：运动、策略、服务、工作进程
├── docs/                          INFERENCE_BOUNDARY.md、SERVICE.md
├── tools/                         共用的 CI 检查和工具
├── images/                        横幅图、图标和 README 的图片
├── .github/                       CI 工作流、仪表板通知、议题和 pull request 模板
├── armor.project.json             清单：版本、角色、成熟度
├── pyproject.toml                 包元数据、入口
├── CHANGELOG.md                   每个版本的变化
├── run.sh run.bat                 启动（共用流程）
├── build.sh build.bat             构建并测试（共用流程）
├── build-test.sh build-test.bat   构建、测试并打包
├── test.sh test.bat               只运行测试，不改版本
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE
```

</details>

## 🗺️ 路线图与已知限制

**当前已知限制**

* 还没有检测模型：分不清人、猫或树枝。
* 在 Jetson 上、使用 TensorRT 或在那里解码的 RTSP 流，都没有运行过任何东西。
* 没有独立的安全审查。

**下一步**

* 在 Jetson Orin NX 上运行能识别人的模型，使用 ARMOR-VISION 的区域、遮罩和规则。

## 🌍 语言

README 和文本提供英语、西班牙语、法语、意大利语、德语、汉语、日语和欧洲葡萄牙语版本。

## 🔗 相关项目

**A.R.M.O.R.**（Autonomous Radar & Multimodal Observation Range）是一个由相互独立的仓库组成的周界安全系统。每个仓库都有自己的版本、自己的测试和自己的 README；这是整个系列：

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - 消息契约、验证器、一致性向量和生成的类型
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - 面向 ESP32-S3 的现场节点固件，配三个雷达和自带的网页面板
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - 太阳能逆变器和电池的协议，以及网关节点的消息
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - 电气节点：电表、电网读数的消息和切换规则
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - 报警节点与面板：防区、布防、延时、警笛和 PIN，可配合服务器也可独立使用
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - 触摸面板：壁挂屏幕上的系统状态、布防与确认，以及语音助手的所在
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - 本地网络：其设备、互联网以及变化
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - 中央协调器：遥测、报警、设备、太阳能读数和摄像头
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - 网页控制台：摄像头、雷达、报警、太阳能以及 2D/3D 场地设计器
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - 带实时 2D/3D 雷达的 Android 操作员客户端
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - iPhone 操作员客户端
* **ARMOR-SERVER-AI**（本仓库） - 视觉推理策略，会解释其决策且从不驱动设备
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - 面向 Jetson Orin NX 的摄像头区域、遮罩和检测规则
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - 离线语音意图，附带无法伪造的确认
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - 外壳、电子器件和台架验收矩阵
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - 部署、CM5 测试台、备份和 TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - 带可重复故障的离线遥测模拟器
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - 检测、安装和更新生态系统自身的仓库
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - 架构、安全基线和能力矩阵

## 📚 文档

* [推理边界](docs/INFERENCE_BOUNDARY.md)：这里决定什么，留给模型什么
* [服务](docs/SERVICE.md)：观察服务及其设置
* [能力矩阵：哪些已被证明，哪些没有](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [项目目录：版本以及各仓库之间如何相互依赖](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [本仓库的更新日志](CHANGELOG.md)

## 🤝 参与贡献与社区

* 提交 pull request 之前，请运行 `python -I tools/armor_ci_validate.py` 和测试：两者都必须通过。请参阅 [CONTRIBUTING.md](CONTRIBUTING.md) 和[行为准则](CODE_OF_CONDUCT.md)。
* README 提供八种语言，由 ARMOR-DOCS 中的源文件生成：文本的修改在那里进行。
* 组件之间消息的变更从 ARMOR-COMMON 开始。
* 不要把仅仅构建过的东西描述为已在板子上运行。
* 请私下报告漏洞：[SECURITY.md](SECURITY.md)。问题、想法和报告：electrohobby3d@gmail.com（[SUPPORT.md](SUPPORT.md)）。

## 👤 作者

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 许可证

GPL-3.0-or-later - 见 [LICENSE](LICENSE)。
