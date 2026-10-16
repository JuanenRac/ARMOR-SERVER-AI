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
  🇯🇵 <b>日本語</b> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### 観察サービス：カメラ上の動きをレーダーと照らし合わせます。判断して説明するだけで、決して動作させません

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Target-Jetson%20Orin%20NX-76b900.svg" alt="Target">
  <img src="https://img.shields.io/badge/Tests-42%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.2.5-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**正直さのチェック - 今日動いているもの:** 判断レイヤーと動き検出器は実在し、テストされています（42 件）。観察サービスは **CM5 テストベンチで動作**しており、システムの警戒中に実際の IP カメラの小さなグレーフレームを見て、レーダーと照らし合わせた動きを報告します。人と猫や枝の区別はできません。**検出モデルはまだなく**、Jetson、TensorRT、そこでデコードした RTSP ストリームでは何も動いていません。

---

## 📋 ひと目で

| | |
|---|---|
| バージョン | `0.2.5` |
| 成熟度 | 確立 |
| テスト | 42 (`python -m unittest discover -s tests`) |
| 技術 | Python 3.11+ / Docker |
| 実機での確認 | CM5 テストベンチで実際の IP カメラとともにサービスとして動作（動きのみ）。Jetson 上では何もありません |

## 🎯 概要

* **観察サービス：**`python -m armor_server_ai.service` はサーバーに何も求めず、何も求められません。システムが**警戒中**のあいだ、数秒ごとに各カメラのストリームから小さなグレーフレーム（64 x 36、保存しない）を 1 枚取り、画面のどれだけが動いたかを測り、レーダーの軌跡と一致すれば、自分のトークンで ARMOR-SERVER に報告します。
* **無視する映像ゾーン：**サーバーが各カメラの無視ゾーンを渡し、その中のピクセルは数えません（揺れる木、道路）。ほとんどが無視される画像は判断せず、数えるゾーンは最大 16 個です。
* **ヒステリシス付きの昼夜プロファイル：**30 ルクス未満で低照度、60 ルクスを超えたときだけ昼に戻り、30 秒以内に 2 度は切り替えないため、夕暮れでばたつきません。
* **説明できる融合：**検出や動きとレーダーの軌跡から、理由付きで重大度（`ignore`、`review`、`high`）を出します。強い動き**かつ**一致するレーダーの軌跡は `high`、弱い動きは `review` です。
* **推奨のみ：**判断には常に `authorizes_action = false` が付きます。中央サーバーがすべての動作を認証・認可します。
* **チェックサムで検証されるエンジン：**ビルド済みの TensorRT エンジンは、存在し、空でなく、`engines.json` があればその SHA-256 と一致するときだけ受け付けます。何もコンパイルもダウンロードもしません。
* **何が悪いかを伝えるサービス：**新しい問題が変わるたびに報告し（`unreachable`、`unauthorized` など）、終われば*サーバーがまた応答する*と伝えます。JSONL ワーカーは番号付きで説明付きの結果を保ち、不正な行がストリームを止めることはありません。

## 🧩 A.R.M.O.R. での役割

ARMOR-SERVER-AI は家が警戒中にカメラの動きを見張る部分です。決して動作せず、何を見たかとその理由（動きとレーダーの軌跡が一致すれば `high`）を [ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER) に伝え、サーバーが何をするかを決めます。次の段階は、Jetson で動く人を認識するモデルで、[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION) がそのモデルが使うゾーン、マスク、ルールを保持します。

## 📂 リポジトリの構成

```text
ARMOR-SERVER-AI/
├── src/armor_server_ai/   profile (day/night), policy (fusion), motion (movement and ignore zones), engine_registry, service (the observation service), cli
├── tests/                 42 tests
└── docs/                  INFERENCE_BOUNDARY.md, SERVICE.md
```

## 🛠️ 開発環境

**必要なもの:** Python 3.11+, optional: a Jetson Orin NX with TensorRT engines (not proven)

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests   # 42 tests
echo '{"label":"person","confidence":0.9,"lux":4,"radar_tracks":1}' | python -m armor_server_ai.cli
python -m armor_server_ai.service --once   # one pass of the observation service
```

[推論の境界](docs/INFERENCE_BOUNDARY.md)と[サービス](docs/SERVICE.md)を参照してください。

## 🔗 関連プロジェクト

**A.R.M.O.R.**（Autonomous Radar & Multimodal Observation Range）は、独立したリポジトリで構成される周辺警備システムです。それぞれに独自のバージョン、テスト、README があります。ファミリーは次のとおりです：

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - メッセージ契約、検証器、適合性ベクトル、生成された型
* **[ARMOR-RADAR](https://github.com/JuanenRac/ARMOR-RADAR)** - ESP32-S3 用フィールドノードのファームウェア。レーダー 3 基と独自の Web パネル付き
* **[ARMOR-SOLAR](https://github.com/JuanenRac/ARMOR-SOLAR)** - 太陽光インバーターとバッテリーのプロトコル、およびゲートウェイノードのメッセージ
* **[ARMOR-ELECTRICAL](https://github.com/JuanenRac/ARMOR-ELECTRICAL)** - 電気ノード：電力量計、電力網の計測メッセージ、開閉のルール
* **[ARMOR-ALARM](https://github.com/JuanenRac/ARMOR-ALARM)** - 警報ノードと警報盤：警戒区域、警戒セット、遅延、サイレン、PIN。サーバーがあってもなくても
* **[ARMOR-HMI](https://github.com/JuanenRac/ARMOR-HMI)** - タッチパネル：壁面ディスプレイでのシステム状態表示、警戒・確認操作、音声アシスタントの拠点
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - ローカルネットワーク：機器、インターネット、そして変化
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - 中央コーディネーター：テレメトリ、アラーム、デバイス、太陽光の測定値、カメラ
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Web コンソール：カメラ、レーダー、アラーム、太陽光発電、2D/3D サイト設計
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - リアルタイム 2D/3D レーダー付きの Android オペレータークライアント
* **ARMOR-SERVER-AI** (このリポジトリ) - 判断を説明し、決して動作しない視覚推論ポリシー
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Jetson Orin NX 向けのカメラのゾーン、マスク、検知ルール
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - 偽造できない確認を備えたオフライン音声インテント
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - 筐体、電子部品、ベンチ受け入れマトリクス
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - デプロイ、CM5 テストベンチ、バックアップ、TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - 再現可能な故障を備えたオフラインのテレメトリシミュレーター
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - エコシステム自身のリポジトリを検出し、インストールし、更新する
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - アーキテクチャ、セキュリティ基準、機能マトリクス

## 📚 ドキュメントとコミュニティ

詳しくは：

* [機能マトリクス：実証済みのものとそうでないもの](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [プロジェクト一覧：バージョンとリポジトリ間の依存関係](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [このリポジトリの変更履歴](CHANGELOG.md)
* [ライセンス（GPL-3.0-or-later）](LICENSE)
* 質問・提案・報告：electrohobby3d@gmail.com

## 👤 作者

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 ライセンス

GPL-3.0-or-later - [LICENSE](LICENSE) を参照。
