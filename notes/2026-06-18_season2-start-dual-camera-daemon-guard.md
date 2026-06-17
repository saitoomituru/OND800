# Season 2 開始・2カメラ確認・デーモンガード実装 — 2026-06-18

## セッション概要

Season 2 初回セッション。2台目カメラ(EMEET C960)を追加した状態での動作確認と、
デーモン運用の安全化を実施した。

## 接続カメラ構成（現在）

| デバイス | モデル | 解像度 |
|---------|-------|-------|
| /dev/video0 | EMEET SmartCam C960 | MJPG 1920x1080@30fps |
| /dev/video2 | Logitech C922 Pro Stream Webcam | MJPG 1920x1080@30fps |

## 発見したバグと修正

### バグ1: NDI名に `:` が含まれ NDIlib_send_create が失敗

- **症状**: EMEET C960 のNDI送信が `RuntimeError: NDIlib_send_create failed` で落ちる
- **原因**: カメラ名 `EMEET SmartCam C960: EMEET Smar` の `:` がNDI名に混入
- **修正**: `orchestrator.py` の `_ndi_name()` で英数字・ハイフン・アンダースコア以外を `-` に置換
- **結果**: 2台とも正常動作（C922: 581frames/0drops、C960: 529frames/0drops）

## 追加・変更内容

### AGENTS.md に追記
- セッション開始時の必須チェック手順（/notes確認・デーモン状態確認・デバイス占有確認）
- 「OND800はデーモンレイヤーで動くツール」の明記
- 直接Bash起動禁止ルールと、必要な場合の手順

### __main__.py に二重起動ガード実装
- PIDファイル `/run/ond800-streamer.pid`（権限なければ `/tmp/` にフォールバック）
- 既存PIDが生きているなら `sys.exit(1)` + エラーメッセージでブロック
- stale PIDファイル（前回クラッシュの残骸）は自動削除
- `finally` ブロックでPIDファイルを確実にクリーンアップ

## 反省点

- 今回セッション開始時に `/notes` と systemd 状態を確認せずに `python3 -m streamer` を
  直接実行してしまい、既存デーモンプロセス(PID 1142)とカメラデバイスを競合させた。
  AGENTS.md に明記したルールを自分自身が破った形。次回から必ず確認すること。

## Season 2 の次ステップ候補

- LVGL操作パネル (HyperPixel上でカメラ切替・NDI状態表示)
- obs-websocket連携
- NDI HX (H.264) 検討 — Advanced SDK要件確認
- 有線Ethernet自動検出・優先切替
