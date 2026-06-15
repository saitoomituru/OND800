# 2026-06-15 環境セットアップ & カメラサーベイ

**実行者:** Claude Code (claude-sonnet-4-6) via SSH on pi5-ond  
**作業ステータス:** NDI SDK インストール待ち

---

## 実機スペック確認

- **モデル:** Raspberry Pi 5 Model B Rev 1.0
- **OS:** Raspberry Pi OS Lite 64-bit (Debian Trixie, kernel 6.12.75+rpt-rpi-2712)
- **RAM:** 7.9 GiB (使用中 ~471 MiB)
- **ストレージ:** /dev/mmcblk0p2 57G, 使用 4.6G, 残 50G
- **ネットワーク:** 有線Ethernet運用

---

## 接続カメラ

**Logitech C922 Pro Stream Webcam** (ID: 046d:085c, USB2.0 Bus 003)

デバイス: `/dev/video0`, `/dev/video1`, `/dev/media3`

### 対応フォーマット (主要なもの)

| フォーマット | 解像度 | 最大fps |
|------------|--------|---------|
| MJPG | 1920x1080 | 30fps |
| MJPG | 1280x720 | **60fps** ← Season 1 メインターゲット |
| MJPG | 800x448 | 30fps |
| YUYV | 640x480 | 30fps |
| YUYV | 1280x720 | 10fps (USB帯域制限) |
| YUYV | 1920x1080 | 5fps |

**判断:** MJPG 1280x720@60fps または 1920x1080@30fps がNDI送出のターゲット。  
YUYVはUSB2.0帯域(480Mbps)の制約でHD以上は使い物にならない。  
**MJPGをデコードしてNDIに渡す**パスで進める。

---

## 導入済みパッケージ

```
git, build-essential, cmake, pkg-config
python3-pip, python3-venv, python3-dev
gstreamer1.0-tools, gstreamer1.0-plugins-{base,good,bad,ugly}
python3-gst-1.0
g++, avahi-daemon, avahi-utils
libssl-dev, libconfig++-dev
v4l-utils (元から入っていた)
```

---

## NDI SDK 状況

- **URL:** https://downloads.ndi.tv/SDK/NDI_SDK_Linux/Install_NDI_SDK_v6_Linux.tar.gz
- **サイズ:** 約59MB (HTTP 200 確認済み)
- **ステータス:** `/tmp/Install_NDI_SDK_v6_Linux.sh` にダウンロード・展開済み
- **次のステップ:** ユーザー承認後に `bash /tmp/Install_NDI_SDK_v6_Linux.sh` 実行

GStreamer の `ndisink` プラグインは **未確認** (NDI SDK インストール後に確認予定)。  
V4L2-to-NDI (https://github.com/lplassman/V4L2-to-NDI) はPi4 aarch64向けの `easy-install-rpi-aarch64.sh` を持つが、Pi5での動作は未検証。

---

## GStreamer 動作確認

`v4l2src` プラグインは認識済み (primary rank)。  
NDI プラグイン (`ndisink`) はSDK未インストールのため未確認。

---

## 次にやること

1. [ ] `bash /tmp/Install_NDI_SDK_v6_Linux.sh` でNDI SDK v6インストール
2. [ ] `gst-inspect-1.0 | grep -i ndi` でndisinkプラグイン確認
3. [ ] もしndisinkが存在しない → V4L2-to-NDIをPi5向けにビルド
4. [ ] GStreamerパイプライン動作確認:
   ```
   v4l2src → image/jpeg,1280x720,60fps → jpegdec → videoconvert → ndisink
   ```
5. [ ] 動作確認できたら Hackintosh OBS で受信確認

---

## 判明した制約・注意事項

- NDI SDKインストーラーはEULAへの同意が必要 (インタラクティブ / `-y` フラグ要確認)
- Pi5はPi4と同じaarch64だがRP1チップのUSBコントローラ実装が違う → USB帯域テスト推奨
- YUYV 1080pはUSB2.0では使えない (5fps)。必ずMJPG使用のこと
