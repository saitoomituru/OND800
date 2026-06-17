# SyntaxError修正 & ファイルログ実装 — 2026-06-18

## 症状

2カメラ対応コミット (`a9c7ef5`) 適用後の再起動でデーモンが起動ループ。
NDI射出が全くされない状態。

## 原因

`streamer/__main__.py` 46行目 の `global _PID_FILE` 宣言が、
その変数を使用している23行目より後に置かれていたため Python が SyntaxError。

```
SyntaxError: name '_PID_FILE' is used prior to global declaration
```

systemd の `Restart=on-failure` により5秒おきに再起動→即クラッシュを繰り返し、
restart counter が 50超になっていた。

## 修正

`_acquire_pid_lock()` 関数の先頭に `global _PID_FILE` を移動。

## 追加実装: ファイルログ

`journalctl` だけではデバッグログが流れて見づらいため、ファイルログを追加:

- 書き出し先: `/var/log/ond800-streamer.log`（権限なければ `/tmp/ond800-streamer.log`）
- ログレベル: DEBUG（ファイルのみ。journalctl は INFO 以上）
- フォーマット: `YYYY-MM-DD HH:MM:SS LEVEL    module message`

現在は `/tmp/ond800-streamer.log` に書き出し中（サービスユーザーが `/var/log/` に書けないため）。
`/var/log/` に書きたい場合は:

```bash
sudo touch /var/log/ond800-streamer.log
sudo chown ond:ond /var/log/ond800-streamer.log
```

## 動作確認結果

- C922 Pro Stream Webcam (video2): NDI stream started ✓
- EMEET SmartCam C960 (video0): NDI stream started ✓
- `systemctl is-active ond800-streamer`: active ✓

## コミット

`bc3a04f`
