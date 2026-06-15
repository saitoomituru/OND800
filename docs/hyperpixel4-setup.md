# HyperPixel 4.0 セットアップ (Pi5)

## 物理接続

1. Pi5の電源を落とす
2. HyperPixel 4.0 HATをGPIOヘッダー全40ピンに差し込む
3. 電源を入れてSSHで接続

## /boot/firmware/config.txt 設定

`[all]` セクションの末尾に追記:

```ini
# HyperPixel 4.0 (non-touch, 800x480, DPI)
dtoverlay=hyperpixel4
```

または Pimoroni公式インストーラー (推奨):

```bash
curl -sSL https://get.pimoroni.com/hyperpixel4 | bash
```

インストーラーが `config.txt` に以下を自動追記する:
```ini
dtoverlay=hyperpixel4
display_rotate=0
```

再起動後、`/dev/fb0` または `/dev/dri/card1` にHyperPixelが出現することを確認:

```bash
ls /dev/fb*
modetest -M card1 -c | grep -i dpi
```

## OND800 ビューファインダー動作確認

```bash
cd /home/ond/OND800
python3 -m streamer
```

ログに `viewfinder enabled (HyperPixel detected)` が出ればOK。

GStreamerパイプライン (自動構築):
```
v4l2src (MJPG 1920x1080@30fps) → jpegdec → tee
  ├─ queue → videoconvert → videoscale → 800x480@60fps → kmssink  [HyperPixel]
  └─ queue → videoconvert → UYVY → appsink → NDI SDK              [OBS NDI]
```

## 注意事項

- HyperPixel 4.0はGPIOを全占有するため、他のGPIO HAT (Arduino連携等) は同時使用不可
- `kmssink force-modesetting=true` でDPIモードをKMSが制御
- ビューファインダーはNDI送出と同じ映像ソースを `tee` で分岐するため追加CPU負荷は videoscale のみ
