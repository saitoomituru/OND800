# controller_arch.md
# OND800 コントローラーアーキテクチャ

---

## 判断権の原則

| 判断 | 担当 | 理由 |
|---|---|---|
| 物理安全チェック | FAN800 | ONDを信用しない・最終防衛ライン |
| mutexリジェクト | OND800 | 論理的裁定 |
| 発火タイミング | FAN800内部クロック | BLE遅延に依存しない |
| ルール配布 | OND800 | 全FAN800に一括配布 |
| 顔トラック判断 | OND800 | カメラ映像を見ているのはOND800 |
| PTZ命令 | OND800 → FAN800（雲台） | |
| OBSフィルタ更新 | OND800 → obs-websocket v5 | |
| BPM解析 | SAO800（optional） | スペック確認後にオフロード |
| エンコード | SAO800（optional） | スペック確認後にオフロード |

**SAO800・OBSがどちらも「顔を知らなくていい」構造。**

---

## イベントキューの流れ

```
入力ソース
  ├─ 投げ銭・コメント（TikTok/YouTube）
  ├─ FAN800ボタン（演者・DJ/VJ）
  ├─ OND HUDタッチ（演者）
  └─ MIDIバス（外部シンセ・DJ機材）
        ↓
  OND800 イベントキュー
        ↓
  MIDIシーケンサー（BPM・クオンタイズ・リキャスト管理）
        ↓
  mutexテーブル照合
  ├─ 競合なし → 発火キューへ
  ├─ 競合あり → リジェクト・GUIに警告
  └─ クールダウン中 → 待機 or リジェクト
        ↓
  ├─ FAN800へ BLE GATT（物理演出）
  ├─ OBSへ obs-websocket v5（シーン・エフェクト・マイク）
  └─ NDI MIDIメタデータ → SAO800（照明・音響同期）
```

---

## MIDIシーケンサー

### BPMソース優先順位

```
1. SAO800 BPM解析（接続中・feature確認済み）
2. fan_tap（FAN800タップテンポ）
3. manual（手動設定）
```

### クオンタイズモード

| モード | 動作 | 向いてる場面 |
|---|---|---|
| `free` | 即時発火 | リキャスト管理のみ |
| `1/4` | 次の4分音符頭 | 音楽・トーク汎用 |
| `1/1` | 次の小節頭 | DJ/VJキュー予約 |
| `1/16` | 16分音符 | 演者リアルタイム |

### トークBPM同期モード

| モード | 演算コスト | 向いてる場面 |
|---|---|---|
| `manual` | ゼロ | MCバトル・ラップ |
| `vad` | 低 | 普通のトーク |
| `llm_sentence` | 高（SAO800必須） | 長尺バラエティ |

---

## リキャストタイム設計

### 2層構造

```
内部リキャスト（OND画面のみ・演者が見る）
  = (base_recast_ms + actor_recast_ms) × recast_multiplier - stack_bonus

公開リキャスト（OBS配信画面・観客が見る）
  = public_recast_modeに従ってOND800が算出・送出
```

### 算出例

```
FAN800申告: base_recast_ms = 5000
演者HOLD:   actor_recast_ms = +2000
衣装パッシブ: recast_multiplier = 0.8
スタック充填: stack_bonus = -500ms

内部リキャスト = (5000 + 2000) × 0.8 - 500 = 5100ms
　→ OND画面に表示・演者のみ閲覧

公開リキャスト = public_recast_mode = "gauge"
　→ ゲージのみ・秒数非表示でOBSオーバーレイに送出
```

### public_recast_mode

| モード | 観客に見えるもの | 演出用途 |
|---|---|---|
| `exact` | 正確な残り秒数 | 透明性重視 |
| `gauge` | ゲージのみ | 汎用 |
| `hidden` | 非表示 | サプライズ投げ銭 |
| `fake` | 演者が任意設定 | 煽り演出 |

---

## 演者スキルシステム

### スキルティア

| ティア | 発動 | 例 |
|---|---|---|
| `passive` | 常時自動 | ビート読みHUD表示 |
| `active_auto` | 発火前に自動実行 | ピンマイクパージ |
| `active_manual` | 演者ボタン | 事故偽装セット |
| `ultimate` | 演者長押し | 溜め解放（HOLD全キュー一斉発火） |

### 発火前タイミングフック

```
pre_fire_1beat   → 息継ぎ読みHUD表示（OND画面のみ）
pre_fire_0.5beat → ピンマイクフェイルオーバー開始
pre_fire_0.25beat → リアクション音声再生
fire             → FAN800発火・OBSエフェクト
post_fire_2beat  → 演者「ピンマイク復帰？」確認ボタン
```

---

## アクター仮想バインド（Dの動き）

物理FAN800 1台を複数アクターで共有。観客には各アクターに個別のデバイスがあるように見える。

```
物理FAN800: スライムバズーカ 1台
  └─ OND800が仮想的に複数キューを管理

観客から見える世界
  みつる用スライムバズーカ  ← 同じFAN-BB2の別キュー
  旦那用スライムバズーカ    ← 同じFAN-BB2の別キュー

物理発火の調停
  └─ fire_arbitration = "fifo"
       └─ キューを跨いでFIFO順に物理発火
       └─ 物理リキャスト中は次のアクターキューを待機
```

---

## 観客入力の変換

### 投げ銭→MIDIノート変換

```python
ITEM_MAP = {
    "スライム": (37, "FIRE_SLIME_MEDIUM"),
    "雨":       (48, "RAIN_START"),
    "光":       (36, "LIGHT_STROBE"),
}

def on_gift(item_name, amount):
    note, event = ITEM_MAP.get(item_name, (0, None))
    velocity = min(127, amount // 10)
    midi_bus.queue(note=note, velocity=velocity, channel=11)

def on_comment(text, comments_per_min):
    for keyword, (note, event) in ITEM_MAP.items():
        if keyword in text:
            velocity = min(127, comments_per_min)
            midi_bus.queue(note=note, velocity=velocity, channel=11)
```

SAO800接続・sentiment機能あり → コメントストリームをオフロードして感情スコア・BPM補正を受け取る。

---

## SAO800スペック確認フロー

```
OND800起動 or SAO800接続検出
  └─ capability queryを送信
       └─ SAO800がfeatureリストを返す
            └─ OND800がGUI選択肢を動的生成

SAO800が落ちた場合
  └─ OND800が検知
       └─ offload.fallbackに従って自動降格
            └─ GUIに「SAO800オフライン・VАDモードで継続中」表示
            └─ 配信継続
```

---

## MIDIジャムセッション共有モデル

```
演者シンセ ──┐
SAO800     ──┼──▶ 共有MIDIバス（NDI MIDIメタデータ）──▶ 全員
FAN800群   ──┘
               OND800がルーター兼BPM解析器

FAN800からのフィードバック
  └─ 発火・動作をMIDIノートとして共有バスに返す
       └─ 演者シンセがFAN800の動作を受け取ってリアクション可能
```

### 通信方式の役割分担

| 方式 | 役割 |
|---|---|
| BLE GATT | 楽譜を渡す（ルール・メタ情報） |
| FAN800内部クロック | 演奏する（タイムキープ） |
| USB-MIDI（アンビリカル） | 一緒にセッションする（ジャム精度同期） |

**精度が必要な場面はアンビリカルで割り切る。**  
**OND800が落ちてもFAN800はループし続ける。**

---

## 外部設備接続

FAN800-MDをスタジオのMIDI INに刺すことで既存設備をジャック。

| 設備 | 接続方法 |
|---|---|
| MIDI機器（シンセ・ドラムマシン） | FAN800-MD USB-MIDI |
| DMX照明卓 | FAN800-DMX or SAO800ブリッジ |
| Ableton Live | Ableton Link（LAN・BPM同期） |
| Resolume VJ | FAN800-MD MIDI in |
| DJ機材（CDJ） | FAN800-MD MIDIクロック |
| レーザー・ストロボ | FAN800-DMX |

NDI Metadata Lab公式標準のMIDI・DMXを使用するため、SAO800がMIDI↔DMX変換ブリッジを担える。
