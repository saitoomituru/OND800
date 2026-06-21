# OND800シリーズ レイヤー間インターフェース仕様

**バージョン:** Season 3 v2.1
**著者:** ZeroRoomLab / saitoomituru
**最終更新:** 2026-06-21

> このファイルがFAN800・SAO800の実装の正本。
> 変更はOND800リポジトリ側が行い、FAN800・SAO800はこれに従う。

---

## 依存方向の原則

```
SAO800（Layer 3）→ OND800のNDI出力を受ける
OND800（Layer 2）→ FAN800のBLE GATTイベント仕様に従ってコマンドを送る
FAN800（Layer 1）→ 上位レイヤーに依存しない。イベントを受けて自律動作する
```

**OND800はOBSの設定ファイルを直接参照しない。**
**OND800はSAO800なしで単独起動・配信できなければならない。**

---

## Layer 1：FAN800 ↔ OND800（BLE GATT）

### イベントスキーマの版管理

FAN800の自己申告・イベント・ACK・MIDIルールには `event_schema_version` を必ず含める。
値はSemVer文字列とし、現在の版は `"1.0.0"` とする。

- メジャー版が一致する範囲では、受信側は未知の追加フィールドを無視できる。
- 受信側が対応しない新しいメジャー版は実行せず、`unsupported_schema` で拒否する。
- `event_schema_version` がない旧端末は `legacy_unversioned` として認識する。
- 旧端末のイベント実行は明示的にlegacy互換を有効にした場合だけ許可する。既定は拒否する。
- 安全判定はスキーマ互換性判定の後にも必ずFAN800側で実行する。

この版管理は通信データの契約だけを表す。ファームウェア版やハードウェア版とは分離する。

### イベント言語の原則

```
良い例：FIRE_SLIME_MEDIUM / LIGHT_STAGE_RED / PUMP_STOP
悪い例：GPIO_PIN_4_HIGH_500ms / I2C_ADDR_0x3C_WRITE_0xFF
```

FAN800は「何をしたいか」だけを知る。「どうやるか」はFAN800の責務。

### FAN800自己申告パケット（接続時・BLE GATT）

```json
{
  "event_schema_version": "1.0.0",
  "uuid": "FAN-XX0-xxxx",
  "role": "slime_bazooka",
  "display_name": "スライムバズーカ左",
  "capabilities": [
    { "event": "FIRE_SLIME_SMALL",  "params": {} },
    { "event": "FIRE_SLIME_MEDIUM", "params": {} },
    { "event": "FIRE_SLIME_LARGE",  "params": {} }
  ],
  "mutex_group": "pyro",
  "mutex_with": [],
  "base_recast_ms": 5000,
  "cooldown_ms": 5000,
  "location_hint": "スタジオA"
}
```

### MIDIルール配布パケット（BLE GATT・低頻度）

```json
{
  "event_schema_version": "1.0.0",
  "type": "midi_rule",
  "bpm": 120,
  "quantize": "1/4",
  "swing": 0.0,
  "sequence": [
    { "beat": 1, "event": "LIGHT_STROBE" },
    { "beat": 3, "event": "FIRE_SLIME_MEDIUM" }
  ],
  "loop": true,
  "start_at": "next_bar"
}
```

FAN800はルール受信後、**内部RTCで自律タイムキープ**する。OND800との通信が切れても動作継続。

### ACKパケット（FAN800 → OND800）

```json
{
  "event_schema_version": "1.0.0",
  "uuid": "FAN-XX0-xxxx",
  "type": "ack",
  "event": "FIRE_SLIME_MEDIUM",
  "result": "ok",
  "timestamp_ms": 1234567890
}
```

リジェクト時は `"result": "rejected"` と `reason` を返す。
`reason` の共通値は `unsupported_schema` / `legacy_schema_disabled` /
`unknown_event` / `invalid_event_name` / `cooldown` / `temperature` /
`overcurrent` / `midi_not_connected` とする。

### イベント言語リファレンス

#### 照明系

| イベント | パラメータ |
|---|---|
| `LIGHT_ON` | - |
| `LIGHT_OFF` | - |
| `LIGHT_DIM` | `brightness: 0-100` |
| `LIGHT_COLOR` | `rgb: hex` |
| `LIGHT_STROBE` | `hz: 1-20` |
| `LIGHT_STAGE_RED` | - |
| `LIGHT_STAGE_BLUE` | - |
| `LIGHT_STAGE_GREEN` | - |
| `LIGHT_STAGE_WHITE` | - |

#### 特効系

| イベント | パラメータ | mutex_group |
|---|---|---|
| `FIRE_SLIME_SMALL` | - | pyro |
| `FIRE_SLIME_MEDIUM` | - | pyro |
| `FIRE_SLIME_LARGE` | - | pyro |
| `RAIN_START` | `intensity: 1-5` | wet |
| `RAIN_STOP` | - | wet |
| `SMOKE_START` | `density: 1-5` | - |
| `SMOKE_STOP` | - | - |
| `SSR_ON` | - | - |
| `SSR_OFF` | - | - |
| `PUMP_STOP` | - | - |

#### MIDI系

| イベント | パラメータ |
|---|---|
| `MIDI_NOTE_OUT` | `channel, note, velocity` |
| `MIDI_CLOCK_OUT` | - |
| `MIDI_CC_OUT` | `channel, cc, value` |
| `UNIT_STATUS_REQ` | - |

#### mutex_groupリファレンス

| グループ | 競合 | 理由 |
|---|---|---|
| `pyro` | `wet` | 水と火工系は同時禁止 |
| `wet` | `pyro` | 同上 |
| `lighting_main` | なし | 照明は他と競合しない |

---

## Layer 2：OND800 ↔ SAO800

### NDI映像経路（OND800 → SAO800）

- 映像本線はNDI
- SAO800が接続されていない場合、OND800はobs-websocket v5で直接OBSを制御する

### NDI MIDIメタデータ（OND800 ↔ SAO800・双方向）

NDI Metadata Lab公式標準のMIDIメタデータを使用。

```xml
<!-- OND800 → SAO800：MIDIイベント送出 -->
<ndi_midi version="1.0">
  <note channel="11" pitch="36" velocity="100" type="note_on"/>
</ndi_midi>
```

### NDI上流メタデータ（SAO800 → OND800）

```xml
<!-- SAO800 → OND800：BPM解析結果 -->
<ndi_zero800_analysis version="1.0">
  <bpm value="128.5" confidence="0.95"/>
  <sentiment score="0.8" label="盛り上がり"/>
</ndi_zero800_analysis>

<!-- SAO800 → OND800：PTZ制御 -->
<ndi_zero800_control version="1.0">
  <ptz pan="0.3" tilt="-0.1" zoom="1.0"/>
</ndi_zero800_control>
```

### 解像度ネゴシエーション

解像度変更命令はNDIプロトコル上存在しない。
SAO800はConnection Metadataで「希望解像度」をヒントとして送信する。
**OND800が最終決定権を持つ。**

```xml
<ndi_capabilities_info>
  <video xres="1920" yres="1080" frame_rate_N="30000" frame_rate_D="1001"/>
</ndi_capabilities_info>
```

### SAO800スペック申告（接続時・obs-websocket v5経由）

```json
{
  "type": "sao800_capabilities",
  "features": [
    "bpm_detect",
    "vad",
    "llm_sentence",
    "face_encode",
    "encode_offload",
    "sentiment",
    "midi_dmx_bridge"
  ]
}
```

OND800はこのリストを元にGUI選択肢を動的生成する。

---

## Layer 3：OND800 ↔ OBS（obs-websocket v5）

OBS Studio v28以降ビルトイン。ポート4455。

### 主要コマンド

| コマンド | 用途 |
|---|---|
| `SetCurrentProgramScene` | シーン切替 |
| `SetSceneItemEnabled` | ソース表示/非表示 |
| `SetInputVolume` | 音量調整（マイクフェイルオーバー） |
| `SetInputMute` | ミュート |
| `StartRecord` / `StopRecord` | 録画制御 |
| `TriggerMediaInputAction` | メディアソース制御 |

### マイクフェイルオーバー手順

```
発火 0.5拍前
  SetInputVolume（ガンマイク）: 0dB
  SetInputVolume（ピンマイク）: フェードアウト開始

発火タイミング
  SetInputMute（ピンマイク）: true
  SetInputVolume（ガンマイク）: 0dB 完了

復帰（演者判断後）
  SetInputVolume（ピンマイク）: フェードイン
  SetInputMute（ピンマイク）: false
```

---

## 操縦粒度の定義

| 操縦者 | 粒度 | インターフェース | 接続 |
|---|---|---|---|
| 演者 | 1/16・身体的リアルタイム | OND HUD・物理ボタン | BLE直結 |
| DJ | フレーズ・キュー単位 | CDJキューポイント・MIDIパッド | FAN800-MD USB |
| VJ | クリップ・セクション単位 | Resolume MIDI | FAN800-MD USB |
| 観客 | 投げ銭単位 | TikTok/YouTubeUI | OND800が変換 |
| OND800 | ルール・マクロ | 自動 | 全員に配布 |

DJ/VJは**キュー予約するだけ**。タイミングはFAN800内部クロックが取る。

---

## 兵装プロファイル（RTMP / SRT）

| プロファイル名 | 送出先 | 主なコンテンツ種別 |
|---|---|---|
| `REQUIEM` | TikTok Live | 拡散優先・国内外同時・アルゴリズム面制圧 |
| `COLONY_LASER` | YouTube | 長期アーカイブ・検索流入・技術解説 |
| `LUNAR_LASER` | X (Twitter) Live | 国内テキスト層・速報・論争 |
| `OFFLINE` | USB SSD / USB HDD | ネットワーク不到達時のフォールバック |

*このドキュメントはSeason 3の正本インターフェース仕様。実装が確定したセクションから更新すること。*
