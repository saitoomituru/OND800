# 2026-06-15 負荷テスト: Pythonオーケストレーター経由NDIストリーム

**実行者:** Claude Code (claude-sonnet-4-6) via SSH on pi5-ond  
**ステータス:** ✅ 測定完了

---

## テスト構成

- **起動コマンド:** `cd /home/ond/OND800 && python3 -m streamer`
- **カメラ:** Logitech C922 `/dev/video0`
- **選択フォーマット:** MJPG 1920x1080@30fps (方針通り自動選択)
- **実送出フォーマット:** YUYV 640x480 (v4l2ndiがMJPGフォールバック)
- **測定時間:** 約30秒 × pidstat 5秒サンプル × 6回
- **受信側:** OBS未接続 (送出側のみ測定)

---

## 測定結果

### CPU負荷 (pidstat -t, 30秒平均)

| プロセス | %usr | %sys | %CPU | スレッド数 |
|---------|------|------|------|-----------|
| v4l2ndi (合計) | **0.00** | **0.00** | **0.00** | 10 |
| `\|__v4l2ndi` (main) | 0.00 | 0.03 | 0.03 | - |
| `\|__disc:accept` | 0.00 | 0.00 | 0.00 | - |
| `\|__disc:find` | 0.00 | 0.00 | 0.00 | - |
| `\|__ndis:lowQ` | 0.00 | 0.00 | 0.00 | - |
| `\|__ndis:resend` | 0.00 | 0.00 | 0.00 | - |
| `\|__ndis:accept` | 0.00 | 0.00 | 0.00 | - |
| python3 (orchestrator) | **0.00** | **0.00** | **0.00** | - |

→ **Pi5での640x480 YUYV NDI送出: CPU負荷ほぼゼロ (全コアidleで99%超)**

### メモリ

| 項目 | 値 |
|------|----|
| v4l2ndi RSS | **11 MB** |
| python3 (orchestrator) RSS | **~20 MB** |
| システム全体使用 | 614 MB / 7.9 GB (7.8%) |
| スワップ使用 | **0** |

### 温度

| 測定時 | CPU温度 |
|--------|---------|
| ストリーム中 | **50.7°C** |

Pi5のサーマルスロットリング閾値は80°C超。50°C台は余裕十分。

### ネットワークトラフィック (NDI, wlan0)

| 方向 | レート |
|------|--------|
| TX (NDI送出) | **20 Kbps** |
| RX | 3 Kbps |

→ OBS未接続のためほぼゼロ。NDIは受信者が接続して初めてビデオデータを流す設計。
  実負荷測定はOBS(Hackintosh)でソースを追加して受信した状態で再測定が必要。

---

## ⚠️ 重要な発見: ネットワーク設定

```
ip route → default via 192.168.0.1 dev wlan0
eth0 → IPアドレス未割り当て
```

**方針ではWi-Fi無効・有線Ethernet運用前提のはずだが、現状はwlan0(Wi-Fi)のみでeth0未設定。**

NDIは帯域を大量に使うため(1080p30で~100-200Mbps相当)、  
**有線Ethernetでの運用が必須**。このままwlan0でOBS受信すると帯域不足になる可能性が高い。

対処:
1. LANケーブルをeth0に接続してDHCP or 固定IP設定
2. `sudo nmtui` or `/etc/network/interfaces` でeth0を有効化
3. wlan0は無効化 or セカンダリに降格

---

## 現状のボトルネック整理

| 項目 | 現状 | 理想 |
|------|------|------|
| 実送出解像度 | **640x480** (YUYVフォールバック) | 1920x1080@30fps |
| NDI送出方式 | v4l2ndi (YUYV専用) | GStreamer ndisink + MJPG |
| CPU負荷(現状) | ~0% | 未測定 (MJPG deocde込みで増加見込み) |
| ネットワーク | wlan0のみ | eth0 有線 |
| OBS受信確認 | 未 | 要確認 |

---

## 次にやること

- [ ] **eth0 有線Ethernet を有効化** (運用方針に合わせる)
- [ ] **OBS(Hackintosh)でNDIソース "OND800-C922-Pro-Stream-Webcam-v0" を受信確認**
- [ ] OBS受信状態での実負荷測定 (ネットワーク帯域・CPU再測定)
- [ ] GStreamer ndisink ビルド → MJPG 1080p30 での真の最大解像度送出
- [ ] MJPG 1080p30 での CPU負荷測定 (デコード分の増加を確認)
- [ ] systemd サービス化 (`python3 -m streamer` を自動起動)
