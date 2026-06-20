# datastore_arch.md
# OND800 データストアアーキテクチャ

---

## 原則

- **顔データはOND800の所有物。OBS・SAO800は顔データを知らない**
- **ENVは人が直接編集する。ツールは触らない**
- **Identity Storeは永続。Identity SessionはGUIで毎回組む**
- **FAN800の帰属はLoadoutで決まる。Locationは場所の記述のみ**
- **衣装が変わってもpersonが同じならスロットを分ける**

---

## 構造概要

```
ENV           ハードウェア固定（1ファイル・手動編集）
  │
  ├─ Location   場所ごとの環境設定（複数）
  │    └─ N:N
  ├─ Loadout    出撃兵装セット（複数）
  │    └─ アタッチ
  └─ Identity Session   今日の出演者リスト（撮影ごと）
       └─ 参照
  Identity Store   人物・衣装・顔データ（永続・独立管理）
```

---

## Layer 0：ENV

```toml
# /etc/ond800/env.toml
# ハードウェア換装しない限り変更しない

display = "hyperpixel_4"
keyboard = false
control_buttons = ["btn_a", "btn_b", "btn_c"]
usb_midi_port = "/dev/midi1"
```

---

## Location

```toml
# /var/ond800/locations/studio_a.toml

name = "スタジオA"
obs_host = "192.168.10.5"
obs_mac  = "aa:bb:cc:dd:ee:ff"
obs_port = 4455
ndi_group = "StudioA"
network_ssid = "StudioA_WiFi"

# スタジオ固定設備（FAN800 UUIDで管理）
[[fixed_equipment]]
uuid = "FAN-AA1-7f3c"
display_name = "上手スポット"

[[fixed_equipment]]
uuid = "FAN-AA2-8b2d"
display_name = "下手スポット"
```

```toml
# /var/ond800/locations/outdoor.toml

name = "外（屋外ロケ）"
obs_host = null           # 単騎出撃
ndi_group = "Outdoor"
network_ssid = null       # テザリング
```

---

## Loadout（出撃兵装セット）

```toml
# /var/ond800/loadouts/full.toml

name = "フルセット"
description = "スタジオ本番・全装備"

[[cameras]]
id = "cam0"
rtsp = "rtsp://192.168.1.100:554/stream"
gimbal = "RS3_mini"           # 電動雲台・OND帰属
fan_id = "FAN-portable-01"    # 手持ちFAN800

[[cameras]]
id = "cam1"
rtsp = "rtsp://192.168.1.101:554/stream"
fan_id = null

[[fan_devices]]
uuid = "FAN-BB2-9a1d"
alias = "スライムバズーカ左"
owner = "studio"              # スタジオ帰属
base_recast_ms = 5000
public_recast_mode = "gauge"  # exact / gauge / hidden / fake
queue_mode = "fifo"           # fifo / lottery / bid
display_on_stream = true
stack_count = 3               # 充填スタック数
stack_recast_bonus_ms = -500  # 1スタックあたりの短縮

  [[fan_devices.virtual_bindings]]
  actor_slot = 0
  alias = "みつるバズーカ"
  passives_apply = true

  [[fan_devices.virtual_bindings]]
  actor_slot = 1
  alias = "旦那バズーカ"
  passives_apply = true

[[fan_devices]]
uuid = "FAN-CC3-2b8e"
alias = "カナダライ上部"
owner = "studio"
base_recast_ms = 10000
mutex_with = ["pyro"]

standalone_path = "/mnt/usb0"
track_mode = "face"           # face / manual / off
key_bindings = "default"

[sequencer]
bpm_source = "sao800_detect"  # sao800_detect / manual / fan_tap
bpm_manual = 120
quantize = "1/4"              # 1/1 / 1/2 / 1/4 / 1/8 / 1/16 / free
swing = 0.0

[midi_bus]
mode = "shared"
channel_map = { drums = 10, fan800 = 11, effects = 12 }

[[midi_map]]
note = 36
event = "FIRE_SLIME_MEDIUM"
actor_slot = 0

[[midi_map]]
note = 37
event = "FIRE_SLIME_MEDIUM"
actor_slot = 1

[[midi_map]]
note = 48
event = "RAIN_START"
params = { intensity = 3 }
```

---

## Identity Store（永続・独立管理）

```
/var/ond800/identity/
  みつる/
    meta.toml
    ゴム巫女_黒/
      face_0.bin        # 顔特徴量ベクトル
      face_1.bin        # 角度違いサンプル
      passives.toml     # 衣装パッシブ
    ゴム巫女_赤/
      face_0.bin
      passives.toml
    私服/
      face_0.bin
      passives.toml
  旦那/
    meta.toml
    私服/
      face_0.bin
      passives.toml
```

```toml
# /var/ond800/identity/みつる/ゴム巫女_黒/passives.toml

[[passives]]
name = "息継ぎ読み"
trigger = "pre_fire_1beat"
effect = "actor_hud_countdown"

[[passives]]
name = "ピンマイクパージ"
trigger = "pre_fire_0.5beat"
effect = "mic_failover"
params = { primary = "pin_mic", failover = "gun_mic" }
auto = true

[[passives]]
target_event = "FIRE_SLIME_MEDIUM"
recast_multiplier = 0.8        # 20%短縮

[[actor_skills]]
tier = "active_manual"
name = "事故偽装セット"
trigger = "actor_button"
recast_ms = 30000

[[actor_skills]]
tier = "ultimate"
name = "溜め解放"
trigger = "actor_long_press"
recast_ms = 120000
```

---

## Identity Session（撮影ごと・GUIで組む）

```toml
# /tmp/ond800/session.toml（セッション中のみ保持）

active_location = "スタジオA"
active_loadout  = "フルセット"
primary_slot = 0

[[cast]]
person  = "みつる"
costume = "ゴム巫女_黒"
slot    = 0
temporary = false

[[cast]]
person  = "旦那"
costume = "私服"
slot    = 1
temporary = false

[[cast]]
person  = "ショッカー"
costume = "エイサー衣装"
slot    = 2
temporary = true              # 今日だけ・後でクリーンアップ可
```

---

## mutexテーブル（FAN800自己申告から構築）

OND800がFAN800の自己申告を受け取って動的に構築する。

```toml
[[mutex_rules]]
source    = "wet"
conflicts = ["pyro"]

[[mutex_rules]]
source    = "pyro"
conflicts = ["wet"]

[[cooldowns]]
uuid = "FAN-BB2-9a1d"
cooldown_ms = 5000
```

---

## オフロード設定

```toml
[offload]
sao_available = true          # 自動検出

[offload.features]
bpm_detect      = "sao800"
vad             = "sao800"
llm_sentence    = "sao800"    # スペック確認済みの場合のみ有効
face_encode     = "local"
encode_offload  = "sao800"

[offload.fallback]
bpm_detect      = "manual"
vad             = "vad"
llm_sentence    = "vad"       # llm死亡時はvadに降格
face_encode     = "local"
encode_offload  = "local"     # 解像度落としてOND800で処理

[offload.talk_sync]
mode = "sao800_detect"        # sao800_detect / vad / manual
```

---

## マイクフェイルオーバー設定

```toml
[[mic_failover]]
name = "ピンマイクパージセット"

primary.obs_name  = "マイク_ピン"
failover.obs_name = "マイク_ガン"

fade_out_ms  = 500
fade_in_ms   = 300
overlap_ms   = 200
trigger      = "pre_fire_0.5beat"
auto_restore = false
restore_fade_ms = 1000

[[mic_failover.candidates]]
priority   = 1
obs_source = "マイク_ガン"
volume_db  = 0

[[mic_failover.candidates]]
priority   = 2
obs_source = "隣演者_ピン"
volume_db  = -6

[[mic_failover.candidates]]
priority   = 3
obs_source = "ルームマイク"
volume_db  = -12
```

---

## 母艦ペアリングテーブル

```toml
# /etc/ond800/pairing.toml

[[hosts]]
name     = "ZeroRoomLab_main"
mac      = "aa:bb:cc:dd:ee:ff"
ip       = "192.168.1.10"
obs_port = 4455
priority = 1

[[hosts]]
name     = "出張_laptop"
mac      = "11:22:33:44:55:66"
ip       = "192.168.1.20"
obs_port = 4455
priority = 2
```

MACアドレスで同一母艦を識別。IPが変わっても再ペアリング不要。
