# OND800 - OBS NDI Dominator

**モビルスーツ型コックピットツール**: 分散戦場アーキテクチャにおけるパイロットの判断拠点。
NDIマルチカメラ制御・BLE IoTファンネル展開・マルチRTMP兵装切替を、演じながら片手で実行する。

単なる「スイッチャー」ではなく、**コックピットそのもの**。引き金はパイロットが引く。

## Design Principle: Do Not Break the Show

OND800 is designed for situations where the control surface may be visible to the audience or captured by cameras.

For this reason, the UI uses performance-world labels rather than raw engineering labels. A live show should not expose internal configuration screens, endpoint names, device IDs, or troubleshooting language unless the operator explicitly requests it.

The control surface should feel like a prop from the performance world, not a leaked backstage console.


## 設計哲学

OND800はファンネルではない。モビルスーツだ。

パイロットはここに座る。引き金はここで引く。  
司令室ではない。偉い人でもない。  
戦場で、リアルタイムで。

**システム階層：**

| レイヤー | 実体 | 役割 |
|---------|------|------|
| コロニーレーザー | SaaSプラットフォーム（TikTok / YouTube / X） | 兵装。照準して撃つ。使えなければ別兵装に切替。 |
| バトルシップ | OBS（Mac / Win） | 映像・音声コンポジット管制。オプション強化。 |
| モビルスーツ | OND800 | コックピット。パイロットの判断はすべてここ。 |
| サイコミュファンネル | FAN800（ESP32 BLEメッシュ） | 自律サブユニット群。イベント言語で動く。 |

プラットフォームBANシャドバン＝兵装切替であり、撤退ではない。  
単騎出撃（バトルシップなし）はサポートされた運用モードである。  
コロニー落とし戦術はスコープ外。

照準。発射。フェールオーバー。

## ビジョン

**演者本人に撮影空間の主権を戻すためのツール。**

通常、マルチカメラ撮影には複数人のスタッフ(カメラ操作、スイッチング、配信オペレート)が必要で、
演者は「撮られる側」として撮影空間の支配権を他者に委ねることになる。

OND800は、演者本人が**演じながらでもソロで手軽にマルチカメラ・ヘビーな撮影環境を展開・操作**できる
ことを目標とする。触れる者が撮影空間そのものを支配・執行する——その思想から
「Dominator」の名を冠する。

開発者本人(TikToker/演者)が、NSFW/技術SFW/音楽歌唱/屋外ダンスロケなど多様な現場で
実際に使うことを前提とした、現場駆動・ビジョン駆動の開発。
要件定義から厳密に積むのではなく、目的とビジョンをもとに実験を積み重ねる。

開発リソースは投げ銭とジャンク箱の材料で賄われるため、**停滞・放置期間が発生することも前提**とする。
(エージェントはこれを「プロジェクト停止」と判断せず、再開時に状況を再確認すること)

## なぜこの設計が「本気」なのか

開発者は元電通非正規デザイナー、バラエティAD/D、子役出身の演者、P・黒服経験者という
カオスな現場キャリアを持つ。このシステムの設計はその経験の直訳だ。

**ADとして**: カメラ割り・段取り・タイミングをフロアで管理してきた経験が、
OND800のMIDIシーケンサー設計（クオンタイズ・リキャストタイム・発火前タイミングフック）に直結している。
「0.5拍前にピンマイクをパージしてガンに切り替える」はADの音声段取りそのままだ。

**演者として**: 「演じながら操作する」は本当に難しい。
認知リソースのほぼ全量が演技に向いているとき、操作UIはそれを奪ってはいけない。
OND800のUX原則「片手で1秒以内」は理想ではなく必要条件だ。
子役からのキャリアで身についた「段取りを体に入れて本番は何も考えない」がそのまま設計思想になっている。

**Dとして**: テレビ生放送の音声卓を見てきた人間は、マイクフェイルオーバーがどれだけ
シビアかを知っている。VEが「声が抜けた」と言う前に音声卓は動く。OND800はそれを自動化する。

**黒服・Pとして**: クラブとスタジオは違う箱だが、DMX卓・MIDI機器・照明の基本構造は同じだ。
「黒子（スタッフ）をESP32に置き換える」というFAN800の思想は、
人力で回していた演出段取りをそのまま機械化したものにすぎない。箱が変わっても互換できる設計なのはそのためだ。

電通非正規時代に叩き込まれたプロ機材・プロワークフローとの互換性へのこだわりが、
このシステムが「それっぽいおもちゃ」ではなく「現場で使えるプロツール」を目指す理由だ。

## 思想的背景

- 「NDIをバスとして使い、OBSをミックスエンジンとして使う」構成のため、ハードウェアの種類を問わず
  NDI化できれば全てフラットなソースとして扱える(NDIパッチベイ思想)。
- 統合GUIは「執行デバイス(Dominator)」として、配信環境を一元的に支配・制御するという機能名。
- 各ユニットは「送信専用ノード」「スイッチャー」「両方」のいずれにもなれる、対称的な設計を目指す。
- ハードウェア統合(筐体一体型OSH)は優先度低。ソフト(統合GUI)の再利用性・改変性を優先する。

> The README opens with the public-facing view. The technical notes below assume readers will inspect the hardware,
> commits, logs, test conditions, and claim boundaries before extending any result.

## Season 1 目標 — **達成済み (2026-06-15)**

認識可能なカメラデバイス(USB Webカム等)を、Pi上で**最大性能でNDI公開する**ことをまず確立する。
ここを土台として、以降は実機テストしながらアジャイルに機能を積んでいく。

**達成構成**: C922 Pro Stream Webcam → MJPG 1920x1080@30fps → NDI SDK v6 (ctypes) → OBS  
**測定結果**: frames=300 drops=0, CPU ~1.3コア/4コア, 温度 51.8°C (Wi-Fi環境)  
**自動起動**: systemd `ond800-streamer.service` でブート時自動起動済み  
詳細は [`notes/2026-06-15_season1-complete.md`](notes/2026-06-15_season1-complete.md) 参照。

## Season 2 目標 — **達成済み (2026-06-18)**

2カメラ同時NDI送出・OBS 2ソース受信・HyperPixel分割表示の同時稼働を確立。

**達成構成**: C922 + EMEET C960 → MJPG 1920x1080@30fps × 2 → NDI SDK v6 → OBS（2ソース同時）  
**HyperPixel表示**: HyperPixelCompositor（1cam:フルスクリーン回転 / 2-3cam:縦スタック / 4cam:2×2グリッド）  
**測定結果**: drops=0×2, CPU ~65%, 温度 65-67°C, スロットリングなし（Wi-Fi環境）  
詳細は [`notes/2026-06-18_obs-2source-load-test.md`](notes/2026-06-18_obs-2source-load-test.md) 参照。

> **現状メモ (2026-06-26):** Season 2の動作実績を作ったHyperPixel 4.0は、
> ベンチ作業中の物理破損により一部表示不能になった。これはソフトウェア上の失敗ではなく、
> 裸液晶を現場機として扱うことの限界を示すログである。詳細は
> [`notes/2026-06-26_hyperpixel-breakage-season3-pause.md`](notes/2026-06-26_hyperpixel-breakage-season3-pause.md) 参照。

### NDIストリーミング方針 (デフォルト設定基準)

設定が明示されていない場合、以下の優先順位で自動選択する:

1. **30fps @ 最大解像度を狙う** — 30fpsを満たせる最高解像度を選択
2. **30fps が達成できない場合** — ビデオ規格内(UVC等)で達成可能な最大解像度を狙い、fpsはそれに従う
3. フォーマット選択順位: **MJPG優先 → YUYV**
   - YUYVはUSB2.0帯域制約により実用上限が640x480@30fps (140Mbps)
   - HD解像度(720p/1080p)を30fpsで得るにはMJPGが必須

**C922 での具体的なデフォルト選択:**

| 優先順 | 解像度 | fps | フォーマット | 備考 |
|--------|--------|-----|------------|------|
| 1位 | 1920x1080 | 30fps | MJPG | 最大解像度@30fps |
| 2位 | 1280x720 | 60fps | MJPG | 30fps超でも規格内最大 |
| フォールバック | 640x480 | 30fps | YUYV | MJPG不可時の実用上限 |

> MJPG→NDI送出には GStreamer ndisink(要別途ビルド)または  
> MJPG→YUYV変換後にv4l2ndiへ渡すパイプラインが必要。  
> 現状(v4l2ndi単体)はYUYV 640x480@30fps が最大実用構成。

## 信号経路

```
FAN800 ──BLE GATT──▶ OND800 ──obs-websocket v5──▶ OBS
                        │
                        └──NDI（映像+MIDIメタデータ）──▶ SAO800
                                                          │
                        ◀──NDI上流メタデータ─────────────┘
                          （PTZ/パン/チルト/AI処理結果）
```

| 用途 | プロトコル |
|---|---|
| OND800 → OBS 制御 | obs-websocket v5 |
| OND800 ↔ SAO800 映像 | NDI |
| SAO800 → OND800 PTZ/AI結果 | NDI上流メタデータ |
| FAN800 ↔ OND800 制御 | BLE GATT イベント言語 |
| FAN800 ↔ スタジオ設備 | USB-MIDI / DIN-MIDI / DMX |
| ジャムセッション精度同期 | USB-MIDI（アンビリカル） |

## FAN800シリーズ

ESP32ベースの演出IoTプラットフォーム。共通BLE GATTプロトコルで全機種がOND800と通信する。

| 型番 | 出力 | 用途 |
|---|---|---|
| FAN800-AC | ACスイッチング | 照明・スモーク・バズーカ電源 |
| FAN800-PWM | PWM制御 | LEDテープ・ピストンマシン・サーボ |
| FAN800-IR | リモコン信号クローン | 既製品エフェクター乗っ取り |
| FAN800-MD | USB-MIDI + DIN5 送受信 | DJ・VJ・シンセへの操縦桿トス |
| FAN800-DMX | DMX512 送受信 | 舞台照明卓直結 |
| FAN800-MD/DMX | MIDI↔DMX変換 | ブリッジドングル |

詳細は [saitoomituru/FAN800](https://github.com/saitoomituru/FAN800) リポジトリ参照。

## シーズンロードマップ

| シーズン | 状態 | スコープ |
|---------|------|---------|
| Season 1 | ✅ 完了 | Pi5上でのNDI公開ストリーム確立 |
| Season 2 | ✅ 完了 | 2カメラNDI同時送出・OBS受信・HyperPixel分割表示 |
| Season 3 | ⏸ 一時停止 / 再設計 | 操作パネル耐久化後にFAN800統合・マルチRTMPフェールオーバー・兵装プロファイル・単騎出撃検証へ復帰 |

### Season 3 実装ターゲット

1. **FAN800 BLEメッシュ管理UI** — OND800コックピットからESP32群を展開・監視・命令
2. **マルチRTMP兵装プロファイル** — コンテンツ種別ごとのプリセット（レクイエムモード / コロニーレーザーモード / 月面レーザーモード）
3. **プラットフォームフェールオーバートリガー** — 使用不能時にワンタップでRTMP切替
4. **単騎出撃モード確認** — バトルシップ（OBS/Mac）なしの動作経路を検証・保証
5. **オフライン収録モード** — USB SSD / USB HDDへのマルチトラックローカル収録。ネットワーク不到達時の完全自律動作。復帰後アーカイブ送出。
6. **飛行中UX硬化** — Season 2のUI全体をコックピット設計原則で見直し

### Season 3 再開条件

2026-06-26にHyperPixel 4.0が物理破損したため、Season 3は中止ではなく一時停止とする。
次の作業は機能追加より先に、操作パネルを現場機として成立させることを優先する。

- 液晶再調達候補を複数比較する（WaveShare / Elecrow / SunFounder など）
- 800x480以上、60fps級、屋外・暗所で読める表示を満たす
- 前面保護パネル、ベゼル、固定フレーム、ケーブル逃がしを含む
- 割れにくい、または割れても交換しやすいモジュール構造にする
- 「片手で1秒以内」をUIだけでなく、物理配置・視認性・筐体にも適用する

### 単騎出撃能力の定義

```
Level 1：バトルシップなし → OND800 + iPhone で出撃可能
Level 2：コロニーレーザーなし → OND800 + USB SSD でオフライン収録完結
```

バトルシップは能力強化のオプション、SaaS回線も出撃条件ではない。OND800単体が最小完結単位。

## ディレクトリ構成

```
/ansible       - Raspberry Pi 5 セットアップ用プレイブック(NDI関連パッケージ、ドライバ等)
/app-panel     - 操作パネルアプリ(LVGL予定、HyperPixel 4.0向け)
/app-panel/sdl - SDL2シミュレータ(PC上でのUI動作確認用)
/design        - Figma等のデザイン資産・エクスポート
/docs          - セットアップ手順、設計記録
  interface_spec.md   - レイヤー間インターフェース仕様（FAN800/SAO800の実装正本）
  datastore_arch.md   - データストアアーキテクチャ（ENV/Location/Loadout/Identity）
  controller_arch.md  - コントローラーアーキテクチャ（イベントキュー・MIDIシーケンサー）
/notes         - 実験ノート、作業ログ(AIエージェント/人間共通の記録場所)
/firmware      - Arduino等、物理コントローラー関連(将来用、現状は空でも保持)
```

### ネットワーク方針

**「電源とカメラがあれば動く」を最低保証とし、あるものを最大限使う。**

| 状態 | 使用インターフェース | 備考 |
|------|------------------|------|
| Wi-Fiのみ | wlan0 | 基本動作 |
| 有線のみ | eth0 | 自動検出・優先使用 |
| 両方あり | eth0 を自動選択 | 有線を優先 |

- 有線Ethernetは「あれば使う」ボーナス。超高画質・多カメラ同時送出時に推奨。
- Wi-Fi単独でも通常ユースケース(1080p30 NDI 1カメラ)は動作する想定。
- 有線接続を検出したら自動でeth0にシフトする（実装予定）。

### ローカル初期認証

現在のLAB実機は`ond/ond`をlocal SSHの公開bootstrapとして使用する。これはcloud公開server用の恒久passwordではなく、物理LANとBonjourからheadless機へ即時到達するための初期値である。

将来firmwareでは、初期認証中であることをGUIへ明示し、password変更、SSH key登録、4〜6桁operator PINを簡単に設定できるようにする。PINとLinux SSH管理権限は分離する。GUI、PIN、claim状態機械は現時点では未実装である。

LAB／RECOVERYでは`ond/ond`を許容し、市販・第三者配布時は個体別またはuser-defined bootstrapへ切り替える。cloud account、外部認証provider、UPnP自動開放、NAT traversalは最低起動条件にしない。詳細は[`docs/local-onboarding-auth.md`](docs/local-onboarding-auth.md)を参照。

## ハードウェア構成(現状の在庫前提)

- Raspberry Pi 5: VJ卓本体/NDIマルチカメラユニット(NDIソース化 + 操作パネル + プレビュー)
  - 複数台展開してファンネル運用することを想定
- HyperPixel 4.0 (タッチ非搭載, 800x480 @60FPS, DPI接続): Season 2で動作確認済み。
  2026-06-26に物理破損したため、以後は裸運用を避け、代替液晶・保護筐体・交換性の検証対象とする。
- ANRAN AR-W360-POE: NDI/RTSP対応ネットワークカメラ
- NETGEAR GS308EP (PoE+スイッチ)
- Hackintosh (X99 Extreme4 / RX 5500 XT): 母艦OBS(演算配信母艦)

※ Raspberry Pi 4(顕微鏡用途)は別件として本プロジェクトの対象外。

## ライセンス

- ソフトウェア: Apache License 2.0
- 将来的なハードウェア設計(OSH): CERN-OHL-P v2 (追加時に明記)

## 将来拡張アイデア(優先度低、メモ)

- 撤れ高係数エンジン: 表情/音声解析によるカメラ自動切替
- 犯罪係数セーフティ: 放送事故的要素の事前検知→該当カメラの自動オフライン化
  (誤検知リスクが高いため、初期はアラート表示のみから)

詳細は `/AGENTS.md` および各サブディレクトリの `AGENTS.md` を参照。

## クイックスタート (新規Pi5セットアップ)

```bash
# 1. リポジトリをクローン
git clone git@github.com:saitoomituru/OND800.git
cd OND800

# 2. NDI SDK .deb を ~/ndi-sdk.deb に配置してからセットアップ実行
bash scripts/setup.sh

# 3. 自動起動の確認 (setup.sh が enable 済み)
sudo systemctl status ond800-streamer
journalctl -u ond800-streamer -f
```

詳細は [`docs/autostart.md`](docs/autostart.md) 参照。
