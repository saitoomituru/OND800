#!/usr/bin/env bash
# OND800 Pi5 セットアップスクリプト
# 動作確認済み環境: Raspberry Pi 5, Raspberry Pi OS Bookworm (arm64)
#
# 使い方:
#   git clone git@github.com:saitoomituru/OND800.git
#   cd OND800
#   bash scripts/setup.sh
#
# 前提:
#   - OS インストール済み, SSH接続可能
#   - NDI SDK v6 .deb が ~/ndi-sdk.deb に配置済み (別途取得要)
#   - sudo 権限あり

set -euo pipefail

echo "=== OND800 セットアップ開始 ==="

# ---- 1. システムパッケージ ----
echo "[1/5] APT パッケージをインストール..."
sudo apt-get update -qq
sudo apt-get install -y \
    python3-gi python3-gi-cairo gir1.2-gstreamer-1.0 \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    v4l-utils \
    python3-pyudev \
    git

# ---- 2. NDI SDK v6 ----
echo "[2/5] NDI SDK v6 をインストール..."
NDI_DEB="${HOME}/ndi-sdk.deb"
if [ ! -f "$NDI_DEB" ]; then
    echo "ERROR: NDI SDK .deb が見つかりません: $NDI_DEB"
    echo "  https://ndi.video/for-developers/ndi-sdk/ から"
    echo "  'NDI SDK for Linux' (arm64 .deb) をダウンロードして"
    echo "  ~/ndi-sdk.deb として配置してから再実行してください。"
    exit 1
fi
sudo dpkg -i "$NDI_DEB"
sudo ldconfig

# NDI SDK の共有ライブラリが /usr/local/lib に入ることを確認
if [ ! -f /usr/local/lib/libndi.so.6 ]; then
    echo "ERROR: libndi.so.6 が /usr/local/lib に見つかりません"
    exit 1
fi
echo "  libndi.so.6 確認 OK"

# ---- 3. HyperPixel 4.0 (接続している場合のみ) ----
echo "[3/5] HyperPixel 4.0 設定..."
CONFIG=/boot/firmware/config.txt
OVERLAY="dtoverlay=vc4-kms-dpi-hyperpixel4"
if grep -qF "$OVERLAY" "$CONFIG"; then
    echo "  dtoverlay は設定済みです (スキップ)"
else
    echo ""
    read -r -p "  HyperPixel 4.0 を接続していますか? [y/N] " ans
    if [[ "$ans" =~ ^[Yy]$ ]]; then
        # [all] セクションに追記
        sudo sed -i "/^\[all\]/a ${OVERLAY}" "$CONFIG"
        echo "  $CONFIG に $OVERLAY を追記しました (次回起動時に有効)"
    else
        echo "  スキップ (後から手動で config.txt に追記可能)"
    fi
fi

# ---- 4. systemd サービス ----
echo "[4/5] systemd サービスを設定..."
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE=/etc/systemd/system/ond800-streamer.service

sudo tee "$SERVICE" > /dev/null << EOF
[Unit]
Description=OND800 NDI Streamer
After=network.target sound.target
Wants=network.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${REPO_DIR}
ExecStart=/usr/bin/python3 -m streamer
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ond800-streamer

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ond800-streamer
echo "  ond800-streamer.service 有効化完了"

# ---- 5. 動作確認 ----
echo "[5/5] カメラ検出テスト..."
if v4l2-ctl --list-devices 2>/dev/null | grep -q "video"; then
    echo "  カメラ検出 OK"
    v4l2-ctl --list-devices 2>/dev/null
else
    echo "  カメラ未検出 (起動後にUSB接続してください)"
fi

echo ""
echo "=== セットアップ完了 ==="
echo ""
echo "次のステップ:"
echo "  1. HyperPixel 追記した場合は再起動: sudo reboot"
echo "  2. 手動起動テスト: cd $REPO_DIR && python3 -m streamer"
echo "  3. 自動起動の確認: sudo systemctl status ond800-streamer"
echo "  4. ログ確認: journalctl -u ond800-streamer -f"
echo ""
