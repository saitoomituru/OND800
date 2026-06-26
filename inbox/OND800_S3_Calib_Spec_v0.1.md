# OND800 Season 3 — 自動カメラ同期キャリブレーション機能
## 実装仕様書 v0.1
ZeroRoomLab / 2026-06-26 / Apache 2.0

---

## 1. 概要と設計思想

OND800 Season 3の中核追加機能として、マルチカメラ録画時のソース間遅延を自動検出・補正するキャリブレーションシステムを実装する。

**設計原則：「録画時点で揃える。編集で直さない」**

衛星放送の遅延補正ノウハウをOBS＋Raspberry Pi環境に移植する。
最遅カメラを基準（0ms）とし、他カメラにプラス方向のオフセットのみで全カメラを揃える。
マイナス補正は使用しない。

---

## 2. システム構成

### 2.1 ハードウェア構成

| コンポーネント | 役割 | 備考 |
|---|---|---|
| Raspberry Pi 5 | 制御コア・WebUI・GPIO制御 | OND800既存構成 |
| ハードリレーモジュール | GPIO系とストロボ系のガルバニック絶縁 | コイル側=Pi系GND、接点側=ストロボ系独立 |
| スティール用モノブロックストロボ | 映像側キャリブ信号発光 | 6.3Φフォノ（TS）シンクロ端子接続 |
| スピーカー（USB/3.5mm） | 音声側キャリブ信号再生 | Pi内蔵オーディオ可 |
| OBS PC | カメラソース録画・オフセット受信 | OBS WebSocket v5.x |

### 2.2 ソフトウェア構成

| モジュール | 言語/FW | 役割 |
|---|---|---|
| ond-calib-server | Python / FastAPI | キャリブ制御・計算・OBS通信 |
| ond-calib-ui | HTML/JS（既存WebUI拡張） | オフセット調整GUI |
| calib-signal-gen | Python（aplay / gpiozero） | クリック音生成・リレーGPIO制御 |
| calib-analyzer | Python（OpenCV / scipy） | 映像・音声スパイク検出 |
| obs-offset-writer | Python（obsws-python） | OBS WebSocket経由オフセット書き込み |

---

## 3. ストロボトリガー回路仕様

### 3.1 設計思想：完全ガルバニック絶縁

Pi GPIO系とストロボ系は**GNDを含め一切共有しない**。
ハードリレーの磁気結合のみで信号を渡す。

```
Pi GPIO (出力) ──→ リレーコイル(+) ──→ リレーコイル(-) ──→ Pi GND
                        ↕ 磁気結合のみ（電気的絶縁）
ストロボ系 GND ──→ リレー接点(COM) ──→ リレー接点(NO) ──→ 6.3Φ Tip
                   ※接点ショートでトリガー発火
```

Pi側GNDとストロボ側GNDは**絶対に接続しない**。

### 3.2 6.3mm フォノ（TS）シンクロ端子プロトコル

スティール用モノブロックストロボのシンクロ端子最低仕様：

| 項目 | 仕様 |
|---|---|
| コネクタ | 6.3mm フォノ（TS: Tip/Sleeve 2極） |
| トリガー方式 | Tip-Sleeve間 接点ショート |
| トリガー電圧 | 無電圧接点で発火（現行機種：概ね5V以下） |
| 必要電流 | 数mA以下 |
| パルス幅 | 1ms以上で確実発火 |
| Pi側出力 | GPIO → リレーコイル → 接点ショート（電圧・電流はPi系から供給しない） |

### 3.3 対応機種と注意事項

| カテゴリ | 機種例 | 同期端子電圧 | 本回路での安全性 |
|---|---|---|---|
| 現行モノブロック | Godox / Profoto / Broncolor | 5V以下 | ○ リレー絶縁で安全 |
| 旧型ストロボ | Vivitar 283等 | 最大200V超 | ○ リレー絶縁で安全（GND共有しないため） |
| TTL専用機 | カメラ専用TTLのみ対応機 | — | △ シンクロ端子なしの場合は非対応 |

リレーによるガルバニック絶縁により、旧型高圧トリガー機種も含め**任意のスティール用モノブロックに対応**する。

### 3.4 推奨部品

```
リレーモジュール : 5V動作 / 接点容量 250VAC 10A 以上（余裕を持たせる）
                  例: SRD-05VDC-SL-C 搭載モジュール
フォノケーブル   : 6.3mm TS オス → 接点はんだ付けまたはターミナルブロック
GPIOピン         : BCM番号でソフト側と合わせること
```

---

## 4. キャリブレーションフロー

### 4.1 全体シーケンス

```
① UIで「キャリブレーション開始」ボタン押下
       ↓
② リレーON（ストロボ発光）＋ クリック音再生（同時トリガー）
       ↓
③ 各カメラソースの映像フレームを取得 → 輝度スパイク検出
   音声ありカメラは並列で波形スパイクも検出
       ↓
④ 各カメラのスパイク検出タイムスタンプを比較
       ↓
⑤ 最遅カメラを基準(0ms)として相対オフセット値を算出
   オフセット = 基準タイムスタンプ - 各カメラのタイムスタンプ（常に >= 0）
       ↓
⑥ OBS WebSocket経由で各ソースにオフセット値を書き込み
```

### 4.2 信号種別と検出方式

| カメラ種別 | 使用信号 | 検出方式 | 精度目安 |
|---|---|---|---|
| 映像あり・音声あり | ストロボ＋クリック音 | 映像+音声スパイク（両方で相互補正） | ±1フレーム以内 |
| 映像あり・音声なし | ストロボのみ | 輝度スパイク検出（OpenCV） | ±1〜2フレーム |
| 音声のみ | クリック音のみ | 波形スパイク検出（scipy） | ±数ms |

---

## 5. 検出アルゴリズム

### 5.1 映像スパイク検出（OpenCV）

```python
# 概略実装
import cv2, time

cap = cv2.VideoCapture(source_index)
baseline_lum = get_baseline_luminance(cap)  # 発光前の平均輝度

trigger_strobo()  # リレーON

while True:
    ret, frame = cap.read()
    ts = time.perf_counter()
    lum = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean()
    if lum - baseline_lum > THRESHOLD:  # デフォルト閾値: +50輝度値
        spike_ts[source_name] = ts
        break
```

### 5.2 音声スパイク検出（scipy）

```python
import sounddevice as sd, time
from scipy.signal import find_peaks

def audio_callback(indata, frames, time_info, status):
    rms = np.sqrt(np.mean(indata**2))
    if rms > AUDIO_THRESHOLD:
        audio_spike_ts[source_name] = time.perf_counter()
```

### 5.3 オフセット計算

```python
# 最遅カメラを基準とする（プラス方向のみ）
baseline_ts = max(spike_ts.values())  # 最遅カメラのタイムスタンプ

offsets = {}
for source, ts in spike_ts.items():
    offsets[source] = int((baseline_ts - ts) * 1000) + BUFFER_MS
    # BUFFER_MS: デフォルト 50ms（余裕分）
    # 結果は常に >= 0
```

---

## 6. OBS WebSocket連携仕様

### 6.1 使用API（v5.x）

| 操作 | リクエスト名 | 主要パラメータ |
|---|---|---|
| 音声オフセット取得 | `GetInputAudioSyncOffset` | `inputName` |
| 音声オフセット書き込み | `SetInputAudioSyncOffset` | `inputName`, `inputAudioSyncOffset`（ms・整数） |
| 映像遅延フィルタ書き込み | `SetSourceFilterSettings` | `sourceName`, `filterName: "sync_delay"`, `filterSettings.delay_ms` |
| プロファイル保存 | `CreateProfile` / `SetCurrentProfile` | `profileName` |

### 6.2 接続設定

- プロトコル: OBS WebSocket v5.x
- デフォルト接続先: `ws://localhost:4455`
- 認証パスワード: UIで入力・Pi内にローカル暗号化保存
- OBS録画・配信中でもオフセット書き込み可（無停止適用）

---

## 7. GUI仕様（WebUI拡張）

### 7.1 キャリブレーション画面コンポーネント

| コンポーネント | 機能 |
|---|---|
| 「キャリブレーション開始」ボタン | ストロボ＋クリック音同時トリガー・自動計算・OBS書き込みまで一括実行 |
| カメラ一覧（スライダー） | 各カメラのオフセット値表示・手動微調整（0〜500ms） |
| 基準カメラドロップダウン | 手動で基準カメラを指定（デフォルト: 自動=最遅） |
| 相対表示トグル | 基準カメラからの相対ms表示に切り替え |
| 「プロファイル保存」ボタン | 現在のオフセット値をOBSプロファイルに書き込み |
| プロファイル呼び出しドロップダウン | 保存済みプロファイルをOBSに適用 |
| キャリブ履歴ログ | 過去のキャリブ結果をタイムスタンプ付きで表示 |

### 7.2 手動フォールバックモード

ストロボ・クリック音なし環境向け：

- 基準カメラを再生しながら他カメラのスライダーを手動調整
- フレーム単位（+/-1フレームボタン）での微調整
- 調整結果は自動キャリブと同じプロファイル形式で保存

---

## 8. クリック音仕様

```
フォーマット : WAV / 44100Hz / 16bit / モノラル
波形         : 単発インパルス（矩形波 1サンプル or 正弦波バースト 1〜2ms）
出力コマンド : aplay -D hw:0,0 click.wav
タイミングログ: ms単位でperf_counter記録（ストロボトリガーと同一スレッドで管理）
```

ストロボトリガーとの同時発火はスレッドを並列起動し数ms以内に収める。
厳密な同時性が必要な場合はGPIO出力と同一割り込みハンドラ内でaplay非同期呼び出し。

---

## 9. Season 3 実装スコープ

| 機能 | 優先度 | S3 | 将来 |
|---|---|---|---|
| ストロボ+クリック音自動キャリブ | ★★★ | ✓ | |
| リレーによるガルバニック絶縁回路 | ★★★ | ✓ | |
| OBS WebSocketオフセット書き込み | ★★★ | ✓ | |
| WebUI（スライダー＋ボタン） | ★★★ | ✓ | |
| プロファイル保存/呼び出し | ★★★ | ✓ | |
| 手動微調整フォールバック | ★★ | ✓ | |
| キャリブ履歴ログ | ★★ | ✓ | |
| DVE800へのオフセットメタデータ連携 | ★ | | ✓ |
| 複数Pi間ネットワーク同期 | ★ | | ✓ |

---

## 10. 非機能要件

| 項目 | 要件 |
|---|---|
| キャリブ所要時間 | ボタン押下から完了まで10秒以内 |
| オフセット精度 | ±1フレーム（33ms @ 30fps）以内 |
| 最大対応ソース数 | OND800既存構成に準拠（最大8ソース） |
| OBS無停止適用 | 録画・配信継続中にオフセット書き込み可 |
| ライセンス | Apache 2.0 |
| 動作環境 | Raspberry Pi 5 / Python 3.11以上 / OBS 30.x以上 |

---

## 11. 依存ライブラリ

| ライブラリ | 用途 | ライセンス |
|---|---|---|
| obsws-python | OBS WebSocket v5クライアント | MIT |
| opencv-python | 映像フレーム取得・輝度解析 | Apache 2.0 |
| scipy | 音声波形スパイク検出 | BSD |
| sounddevice | オーディオストリームキャプチャ | MIT |
| gpiozero / RPi.GPIO | リレーGPIO制御 | MIT |
| FastAPI | WebUIバックエンド | MIT |
| aplay（alsa-utils） | クリック音再生 | LGPL |

---

*OND800 S3 Calib Spec v0.1 — ZeroRoomLab — Apache 2.0*
