# 2026-06-15 CPU負荷測定 & NDIストリーミング方針確定

**実行者:** Claude Code (claude-sonnet-4-6) via SSH on pi5-ond  
**ステータス:** ✅ 測定完了、方針確定

---

## 測定環境

- **機材:** Raspberry Pi 5 Model B (4コア aarch64, 8GB RAM)
- **カメラ:** Logitech C922 Pro Stream Webcam (`/dev/video0`, USB2.0)
- **ツール:** V4L2-to-NDI `./build/v4l2ndi` + NDI SDK v6 libndi.so.6.3.2
- **測定ツール:** `pidstat -t` (sysstat), `mpstat -P ALL`

---

## 測定結果

### テスト1: 640x480@30fps YUYV (threaded)

```
コマンド: ./build/v4l2ndi -d /dev/video0 -x 640 -y 480 -n 30000 -e 1000001 -v "test" -i
```

| 指標 | 値 |
|------|----|
| v4l2ndi %CPU | **0.00%** (pidstat 5秒平均) |
| システム全体 idle | ~99% |
| RSS | 11MB |
| スレッド数 | 10 (メイン+NDI内部) |

### テスト2: 640x480@60fps YUYV (threaded)

```
コマンド: ./build/v4l2ndi -d /dev/video0 -x 640 -y 480 -n 60000 -e 1000001 -v "test" -i
```

| 指標 | 値 |
|------|----|
| v4l2ndi %CPU | **0.00%** (pidstat 5秒平均) |
| システム全体 idle | ~99% |
| 実効CPU使用 (mpstat CPU3) | **~3%** ← v4l2ndiが主に使用 |

### スレッド内訳 (pidstat -t 結果)

```
|__v4l2ndi     (main)
|__v4l2ndi     (capture thread x2)
|__disc:accept (NDI discovery)
|__disc:find   (NDI discovery)
|__ndis:lowQ   (NDI send queue)
|__ndis:resend (NDI resend)
|__ndis:accept (NDI accept)
|__v4l2ndi     (image processing thread)
```

全スレッド 0.00% → **待機ベース。640x480@60fps でもPi5は余力99%超**。

---

## 判明した制約: YUYV帯域とMJPGの必要性

| 解像度 | fps | フォーマット | USB帯域 | 実用 |
|--------|-----|------------|---------|------|
| 640x480 | 30fps | YUYV | 140Mbps | ✅ |
| 640x480 | 60fps | YUYV | 281Mbps | ✅ |
| 1280x720 | 30fps | YUYV | 422Mbps | ❌ USB2.0超過 |
| 1920x1080 | 30fps | YUYV | 949Mbps | ❌ |
| 1280x720 | 60fps | MJPG | 圧縮済み | ✅ (要デコード) |
| 1920x1080 | 30fps | MJPG | 圧縮済み | ✅ (要デコード) |

**結論:** v4l2ndiはYUYV/UYVY/NV12のみ対応。MJPG非対応のため、  
HD解像度NDIストリームには別アプローチが必要。

**注意:** v4l2ndiに `-x 1280 -y 720` を渡しても、実際には640x480にフォールバックする  
(バッファサイズ 614400 = 640×480×2 bytes で確認済み)。

---

## NDIストリーミング方針 (README.mdに追記済み)

**デフォルト選択基準:**

1. 30fps @ 最大解像度を優先
2. 30fps 未達なら、ビデオ規格内最大解像度 (fps はそれに従う)
3. フォーマット: MJPG優先 → YUYV フォールバック

**C922でのデフォルト選択:**

| 優先 | 解像度 | fps | 方式 |
|------|--------|-----|------|
| 1 | 1920x1080 | 30fps | MJPG→NDI |
| 2 | 1280x720 | 60fps | MJPG→NDI |
| FB | 640x480 | 30fps | YUYV→v4l2ndi |

---

## 次にやること

- [ ] **GStreamer NDI sink プラグインのビルド**
  - [gst-plugin-ndi](https://github.com/teltek/gst-plugin-ndi) または NDI SDK同梱のGstプラグイン確認
  - パイプライン: `v4l2src ! image/jpeg,width=1920,height=1080,framerate=30/1 ! jpegdec ! videoconvert ! ndisink`
- [ ] MJPG→NDI パイプラインのCPU負荷測定 (1080p30, 720p60 両方)
- [ ] Hackintosh OBSでの受信確認 (現状の640x480でまず確認)
- [ ] systemdサービス化 (カメラ自動検出→起動)
- [ ] pyudev でhotplug対応のPythonオーケストレーター設計
