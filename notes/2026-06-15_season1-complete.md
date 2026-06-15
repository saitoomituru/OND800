# Season 1 達成ノート — 2026-06-15

## 達成内容

**Season 1 ゴール「認識したカメラデバイスをPi上で最大性能でNDI公開する」** を達成。

## 動作確認済み構成

| 項目 | 内容 |
|------|------|
| ハード | Raspberry Pi 5 |
| OS | Raspberry Pi OS Bookworm (arm64) |
| カメラ | Logitech C922 Pro Stream Webcam |
| ディスプレイ | HyperPixel 4.0 (480x800, DPI, fbdevsink) |
| NDI送出 | 1080p30fps MJPG→UYVY→NDI SDK v6 ctypes |
| ネットワーク | Wi-Fi (wlan0) のみで動作確認 |
| 自動起動 | systemd `ond800-streamer.service` |

## 性能測定結果 (Wi-Fi, 1080p30)

- frames=300, drops=0 (10秒間)
- CPU使用率: ~1.3コア / 4コア
- 温度: 51.8°C
- OBS NDI受信: 同一Wi-Fiネットワーク上で確認

## 動作パイプライン

```
C922 (MJPG 1920x1080@30fps)
  → v4l2src
  → jpegdec
  → videoconvert → I420
  → tee
      ├─ queue → videoconvert → UYVY → appsink → NDI SDK v6  →  OBS (NDI)
      └─ queue → videoconvert → videoscale → videoflip(CW)
              → BGRx 480x800 → fbdevsink /dev/fb0            →  HyperPixel
```

## 解決した主なハマりポイント

1. **dtoverlay名誤り**: `hyperpixel4` → `vc4-kms-dpi-hyperpixel4` (Pi5はvc4-kmsドライバ)
2. **kmssink 失敗**: コンポジターなし環境では `fbdevsink` を使う
3. **fb0フォーマット**: RGB16ではなく BGRx 32bpp (ioctl で確認)
4. **GStreamer caps交渉失敗**: tee前に `videoconvert ! video/x-raw,format=I420` を挟む
5. **NDI-only時の二重videoconvert**: 表示ブランチ除去時は明示的なパイプライン文字列を書く
6. **sudo tee パイプ順序**: `echo pw | sudo -S tee file << 'EOF'` の順序

## 成果物ファイル

```
streamer/
  __main__.py      — エントリポイント (SIGINT/SIGTERM対応)
  orchestrator.py  — pyudev ホットプラグ監視 + ストリーム管理
  camera.py        — カメラ探索 & フォーマット選択 (MJPG優先)
  gst_stream.py    — GStreamerパイプライン構築・実行
  ndi_send.py      — NDI SDK v6 ctypesラッパー
  display.py       — HyperPixel ビューファインダー

docs/
  hyperpixel4-setup.md  — HyperPixel 4.0 セットアップ手順
  autostart.md          — systemd 自動起動手順

scripts/
  setup.sh              — 新規Pi5への再現セットアップスクリプト
```

## 次のステップ候補 (Season 2)

- LVGL操作パネル (HyperPixel上でカメラ切替・NDI状態表示)
- obs-websocket連携 (シーン切替のリモートコントロール)
- 複数カメラ同時NDI送出テスト
- 有線Ethernet自動検出・切替の実装
- NDI HX (H.264) 検討 — Advanced SDK要、現状はStandard SDKでI-frame UYVY
