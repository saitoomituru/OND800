# HyperPixel 4.0 セットアップ (Pi5)

## 物理接続

1. Pi5の電源を落とす
2. HyperPixel 4.0 HATをGPIOヘッダー全40ピンに差し込む
3. 電源を入れてSSHで接続

## /boot/firmware/config.txt 設定

`[all]` セクションの末尾に追記:

```ini
# HyperPixel 4.0 (non-touch, 800x480, DPI)
dtoverlay=vc4-kms-dpi-hyperpixel4
```

> **注意**: `dtoverlay=hyperpixel4` は Pi5 では動作しない。
> Pi5 の vc4-kms ドライバに対応した正しい overlay 名は `vc4-kms-dpi-hyperpixel4`。

overlay が存在するか確認:
```bash
ls /boot/firmware/overlays/vc4-kms-dpi-hyperpixel4.dtbo
```

再起動後、`/dev/fb0` が出現することを確認:
```bash
ls /dev/fb*
# → /dev/fb0  が出ればOK
```

## OND800 ビューファインダー動作確認

```bash
cd /home/ond/OND800
python3 -m streamer
```

ログに `viewfinder enabled (HyperPixel detected)` が出ればOK。

GStreamerパイプライン (自動構築):
```
v4l2src (MJPG 1920x1080@30fps) → jpegdec → videoconvert → I420 → tee
  ├─ queue → videoconvert → UYVY → appsink → NDI SDK          [OBS NDI]
  └─ queue → videoconvert → videoscale → videoflip(clockwise)
          → BGRx 480x800 → fbdevsink /dev/fb0                 [HyperPixel]
```

## フレームバッファ仕様

| 項目 | 値 |
|------|-----|
| デバイス | `/dev/fb0` |
| 解像度 | 480x800 (ポートレート) |
| フォーマット | BGRx 32bpp (B=offset8, G=offset0, R=offset16) |
| GStreamer format | `BGRx` |
| 回転 | カメラ(ランドスケープ)を時計回り90°回転して表示 |

## 注意事項

- HyperPixel 4.0はGPIOを全占有するため、他のGPIO HAT は同時使用不可
- `kmssink` はコンポジターなしでは `driver does not provide mode settings configuration` エラーになる
  → `fbdevsink device=/dev/fb0` を使用 (OND800はこちらで実装済み)
- ビューファインダーはNDI送出と同じ映像ソースを `tee` で分岐するため追加CPU負荷は videoscale/videoflip のみ
