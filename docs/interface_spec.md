# OND800 レイヤー間インターフェース仕様

**バージョン:** Season 3 v1.0  
**著者:** ZeroRoomLab / saitoomituru  
**最終更新:** 2026-06-18

このドキュメントは OND800（Layer 2）・FAN800（Layer 1）・SAO800（Layer 3）の
レイヤー間境界仕様を定義する。各リポジトリの実装はこの仕様に従う。

---

## レイヤー構成と依存方向

```
SAO800（Layer 3, OBSプラグイン）
    ↓ NDI / OSC / WebSocket（受信のみ）
OND800（Layer 2, モビルスーツ）
    ↓ BLE GATT イベント言語（送信のみ）
FAN800（Layer 1, ESP32サイコミュファンネル）
```

**原則：依存は上位レイヤーから下位レイヤーへ。逆方向の依存は禁止。**

- FAN800はOND800を知らない（イベントを受けて自律動作するのみ）
- OND800はSAO800を知らない（NDI出力を提供するのみ）

---

## OND800 ↔ FAN800（BLE GATT）

### 基本原則

OND800は**意図（インテント）**を送る。ハードウェアプリミティブは露出しない。
物理的動作の決定（タイミング・強度・シーケンス）はFAN800ファームウェアが担う。

### イベント言語仕様（確定）

| イベント名 | 意味 | FAN800側の動作 |
|-----------|------|--------------|
| `FIRE_SLIME_SMALL` | スライム小量射出 | ポンプ短時間駆動 |
| `FIRE_SLIME_MEDIUM` | スライム中量射出 | ポンプ中時間駆動 |
| `FIRE_SLIME_LARGE` | スライム大量射出 | ポンプ長時間駆動 |
| `PUMP_STOP` | ポンプ即時停止 | 全ポンプ停止 |
| `LIGHT_STAGE_RED` | ステージ照明→赤 | LED制御 |
| `LIGHT_STAGE_GREEN` | ステージ照明→緑 | LED制御 |
| `LIGHT_STAGE_BLUE` | ステージ照明→青 | LED制御 |
| `LIGHT_STAGE_WHITE` | ステージ照明→白 | LED制御 |
| `LIGHT_OFF` | 照明全消灯 | LED全停止 |
| `SSR_ON` | SSRリレーON | AC機器ON |
| `SSR_OFF` | SSRリレーOFF | AC機器OFF |
| `UNIT_STATUS_REQ` | ユニット状態要求 | バッテリー・温度等を返却 |

### 禁止パターン

```
❌ GPIO_PIN_4_HIGH_500ms   （ハードウェアプリミティブの露出）
❌ I2C_ADDR_0x3C_WRITE_0xFF  （密結合）
❌ PUMP_DURATION_MS_300    （物理パラメータの直接指定）
```

### BLE GATT プロファイル（暫定）

- Service UUID: `未確定（Season 3で決定）`
- Characteristic UUID: `未確定（Season 3で決定）`
- データ形式: UTF-8文字列（イベント名をそのまま送信）
- 方向: OND800→FAN800（Write Without Response）
- 応答: FAN800→OND800（Notify、`UNIT_STATUS_REQ` 応答時のみ）

---

## OND800 ↔ SAO800（NDI / OSC / WebSocket）

### 基本原則

OND800はNDI映像ストリームを出力する。SAO800（OBSプラグイン）はこれを受信する。
OND800はSAO800の存在を知らず、SAO800の有無は動作に影響しない。

### NDI映像出力

- プロトコル: NDI SDK v6
- デフォルト設定: 1920x1080 @ 30fps（MJPG経由）
- ストリーム名: `OND800_{hostname}_{camera_index}`
- メタデータ送信: カメラID・タイムスタンプ（将来拡張、現状未実装）

### OND800→SAO800 制御チャネル（未確定）

Season 3で検討。候補：

| 候補 | 特徴 |
|------|------|
| OSC（UDP） | 軽量・ブロードキャスト可・OBSプラグイン実績あり |
| WebSocket | 双方向・確実性高い |
| NDIメタデータ | 映像と同一チャネル・実装コスト低 |

→ Season 3実装前に決定し、このファイルを更新する。

---

## 兵装プロファイル（RTMP / SRT）

### コンテンツ種別と推奨兵装

| プロファイル名 | 送出先 | 主なコンテンツ種別 |
|--------------|--------|-----------------|
| `REQUIEM` | TikTok Live | 拡散優先・国内外同時・アルゴリズム面制圧 |
| `COLONY_LASER` | YouTube | 長期アーカイブ・検索流入・技術解説 |
| `LUNAR_LASER` | X (Twitter) Live | 国内テキスト層・速報・論争 |
| `OFFLINE` | USB SSD / USB HDD | ネットワーク不到達時のフォールバック |

### フェールオーバー原則

- プラットフォームBANシャドバン＝兵装切替。ミッション中止ではない。
- 切替はOND800コックピットのトグル1つで完結する（タップ数：1）。
- `OFFLINE` プロファイルはネットワーク不到達を検出したら自動提案する。
- 復帰後アーカイブ送出は自動または手動トリガーのいずれかをサポートする。

---

*このドキュメントはSeason 3設計フェーズの生きた仕様書。実装が確定したセクションから更新すること。*
