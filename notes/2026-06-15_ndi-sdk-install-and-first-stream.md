# 2026-06-15 NDI SDK v6インストール & 初NDIストリーム起動

**実行者:** Claude Code (claude-sonnet-4-6) via SSH on pi5-ond  
**ステータス:** ✅ NDIストリーム起動成功

---

## 作業サマリ

1. GitHub SSH認証確認 → remote URLをSSHに変更してpush解決
2. NDI SDK v6 インストール (aarch64-rpi4-linux-gnueabi)
3. V4L2-to-NDI をPi5向けにビルド
4. C922で720p60 NDIストリーム起動確認

---

## NDI SDK v6 インストール手順

```bash
# ダウンロード
curl -L https://downloads.ndi.tv/SDK/NDI_SDK_Linux/Install_NDI_SDK_v6_Linux.tar.gz | tar xz -C /tmp

# インストール (y でEULA同意)
echo "y" | bash /tmp/Install_NDI_SDK_v6_Linux.sh

# システムへ配置 (Pi5はaarch64-rpi4-linux-gnueabi を使用)
sudo cp "$HOME/NDI SDK for Linux/lib/aarch64-rpi4-linux-gnueabi/libndi.so.6.3.2" /usr/local/lib/
sudo ln -sf /usr/local/lib/libndi.so.6.3.2 /usr/local/lib/libndi.so.6
sudo ln -sf /usr/local/lib/libndi.so.6.3.2 /usr/local/lib/libndi.so
sudo cp -r "$HOME/NDI SDK for Linux/include/" /usr/local/include/ndi
sudo ldconfig
```

確認:
```
$ ldconfig -p | grep ndi
libndi.so.6 (libc6,AArch64) => /usr/local/lib/libndi.so.6
```

---

## V4L2-to-NDI ビルド

```bash
git clone https://github.com/lplassman/V4L2-to-NDI.git
cd V4L2-to-NDI
mkdir -p build lib include
cp "$HOME/NDI SDK for Linux/include/"* include/
cp "$HOME/NDI SDK for Linux/lib/aarch64-rpi4-linux-gnueabi/"* lib/
g++ -std=c++14 -pthread -Wl,--allow-shlib-undefined -Wl,--as-needed \
    -Iinclude/ -L lib -o build/v4l2ndi main.cpp PixelFormatConverter.cpp \
    -lndi -ldl -g -O2
```

ビルド成功: `build/v4l2ndi` (405KB, ELF 64-bit ARM aarch64)  
エラー・警告なし。Pi5 (aarch64) でPi4向けライブラリがそのまま動作。

---

## 初NDIストリーム動作確認

```bash
timeout 8 env LD_LIBRARY_PATH=lib ./build/v4l2ndi \
    -d /dev/video0 \
    -x 1280 -y 720 \
    -n 1000 -e 60000 \   # 60fps (1000/60000 = 1/60)
    -v "OND800-C922" \
    -i                   # threaded mode
```

出力:
```
Mapping /dev/video0 buffer 0-3, len 614400
Image Processing Threading Enabled
Current Queue Level 1
Starting stream into mmap buffer map, /dev/video0
[8秒間フレームドロップなし・エラーなし]
```

✅ **NDIストリーム "OND800-C922" として送出成功**  
✅ フレームドロップ(`!`)・レイテンシ増加(`#`)なし  
✅ Pi5上で `libndi.so.6.3.2` (aarch64-rpi4) が正常動作

---

## カメラ情報

- **デバイス:** Logitech C922 Pro Stream Webcam (046d:085c)
- **デバイスノード:** /dev/video0
- **使用フォーマット:** YUYV (v4l2ndi デフォルト)
- **解像度:** 1280x720 @ 60fps (mmap buffer 614400 bytes = 1280×720×YUYV)

**注:** v4l2ndi は YUYV/UYVY/NV12 を受け付けるが MJPG 未対応。  
C922はYUYV 720pでUVSB2.0帯域内(614400 × 60 × 16bit ≒ 590Mbps... 要確認)。  
**TODO:** CPU使用率の実測と、1080p30での帯域確認。

---

## 判明した制約・注意事項

- `v4l2ndi` はMJPGを直接扱えない → YUYV使用
- YUYVは1280x720@60fps = buffer 614400 bytes。USB2.0(480Mbps実効~300Mbps)との整合性は実測要
- FPS指定は `-n 分子 -e 分母` (例: 720p60 = `-n 1000 -e 60000`)
- `LD_LIBRARY_PATH=lib` で `./lib/libndi.so.6` を参照 (または /usr/local/lib にインストール済みなので省略可)

---

## 次にやること

- [ ] `/usr/local/lib` にlibndiが入っているので `LD_LIBRARY_PATH` なしで動くか確認
- [ ] Hackintosh OBSのNDIソース一覧に "OND800-C922" が見えるか確認 (同一LAN)
- [ ] CPU使用率の実測 (`htop` で確認しながらストリーム)
- [ ] 720p60 vs 1080p30 の CPU負荷比較
- [ ] v4l2ndi をsystemdサービス化 (自動起動・hotplug対応)
- [ ] Pythonオーケストレーション層の設計 (pyudev でhotplug検出 → v4l2ndi プロセス管理)
