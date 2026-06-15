# 自動起動設定 (systemd)

OND800 ストリーマーは起動時に自動的に NDI 送出を開始するよう systemd サービスとして設定済み。

## サービスファイル

`/etc/systemd/system/ond800-streamer.service`

```ini
[Unit]
Description=OND800 NDI Streamer
After=network.target sound.target
Wants=network.target

[Service]
Type=simple
User=ond
WorkingDirectory=/home/ond/OND800
ExecStart=/usr/bin/python3 -m streamer
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ond800-streamer

[Install]
WantedBy=multi-user.target
```

## インストール手順

`scripts/setup.sh` が自動的に設定します。手動で行う場合:

```bash
# サービスファイルを配置後:
sudo systemctl daemon-reload
sudo systemctl enable --now ond800-streamer
```

## 運用コマンド

```bash
# 状態確認
sudo systemctl status ond800-streamer

# リアルタイムログ
journalctl -u ond800-streamer -f

# 手動再起動
sudo systemctl restart ond800-streamer

# 停止
sudo systemctl stop ond800-streamer

# 自動起動の無効化
sudo systemctl disable ond800-streamer
```

## 起動シーケンス

1. Pi5 電源オン
2. OS 起動 → `network.target` 到達
3. `ond800-streamer.service` 起動
4. `orchestrator.py` が `/dev/video*` をスキャン
5. C922 (またはその他 UVC カメラ) を検出
6. `best_format()` → MJPG 1920x1080@30fps
7. GStreamer パイプライン起動
8. NDI ソース `OND800-C922-Pro-Stream-Webcam-v0` が LAN に出現
9. HyperPixel 検出済みの場合、同時に fbdevsink ビューファインダー表示

## トラブルシューティング

| 症状 | 確認コマンド | 対処 |
|------|------------|------|
| サービスが起動しない | `journalctl -u ond800-streamer -n 50` | ログでエラー確認 |
| NDI が OBS に出ない | `ping -c1 $(hostname -I \| awk '{print $1}')` | Wi-Fi / 有線接続確認 |
| カメラ未検出 | `v4l2-ctl --list-devices` | USB 接続確認、`/dev/video0` 存在確認 |
| HyperPixel 映らない | `ls /dev/fb0` | `dtoverlay=vc4-kms-dpi-hyperpixel4` が config.txt にあるか確認 |
