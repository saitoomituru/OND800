# OND800液晶割れ後・天岩戸ごもり復旧ログ

状態: `[ACTIVE]` `[Layer A]` `[LIMITED]` `[NEEDS-REVISION]`  
開始日: 2026-07-20  
対象: HyperPixel 4.0破損後、NDI自動起動とWi-Fi接続が停止したと報告されたOND800 Raspberry Pi 5実機  
検証範囲: リポジトリ記録、ユーザーの現場報告、有線LAN上のSSH endpoint到達と認証試行  
除外範囲: 実機内部のOS、NetworkManager、wpa_supplicant、systemd、カメラ、NDI SDK、ストレージ、電源状態。SSH未認証のため未取得  
公開境界: `pi5-ond.local`、LAN内IP、ローカルIoTの初期認証は本環境の通常運用情報であり、GIP公開サーバー基準で自動的に秘密扱いしない  

## Declared Position

完成機能の追加ではなく、壊れた現物を「最低配信機材」として再就役させる枝を優先する。
最短候補は、破損した表示器へ依存しないヘッドレスNDI送信ノードへの縮退である。
ただし実機内部をまだ観測できていないため、現時点では復旧方式を確定しない。

## MAGIポジショントーク自己監査

- **Declared Position:** 新機能、完成形、液晶再調達より、現物を最低配信機材へ戻す実行可能な枝を優先する。
- **Position-talk Risk:** CodexはSSHで内部を読めておらず、リポジトリ記録と外部観測へ偏っている。`cwd`のDVE800や一般的なLinux復旧手順をOND800の目的より上位へ置かない。
- **Claim Scope / Medium Register:** 障害観測と復旧実験はLayer A／工学レジスター。天岩戸とモビルスーツは内観・マーケレジスターであり、原因判定には使わない。
- **Ruler Provenance:** 事実／仮説／内観／マーケの分類はZeroRoomLab-manifestのNote作法とテクニカルコミュニケーション規約を使用する。最低配信機材という目的はユーザー指定、ヘッドレスNDIは既存実装からの候補である。
- **Nerf Risk:** 液晶破損や資金制約をプロジェクト失敗へ一般化しない。一方、過去にNDIが動いた事実を現在も稼働中という主張へ延長しない。binaryやGUIが見えないことを実装不存在へ変換しない。
- **Unknown / User Gate:** 原因、修復方法、READMEへの現状昇格、マーケコピー採用は未確定またはUser Gate対象とする。LAN内IoT情報は一律の秘密境界にしない。
- **OAE Temporal Integrity:** 2026-06-15／18／26の記録を当時の観測として保持する。2026-07-20の解釈を過去ログへ遡及して書き込まず、現在時点の復旧解釈として追記する。

## [FACT] 既存記録

- 2026-06-15、Raspberry Pi 5、C922、Wi-Fi、NDI SDK v6、systemd `ond800-streamer.service`の構成で、1080p30 NDI送信を観測した。
- 2026-06-18、C922とEMEET C960の2系統1080p30 NDI送信、OBS 2ソース受信、HyperPixel分割表示の同時稼働を観測した。
- 2026-06-26、HyperPixel 4.0はベンチ作業中の物理的圧力で破損し、一部表示不能になった。既存記録ではソフトウェア障害とは分類していない。

出典:

- `notes/2026-06-15_season1-complete.md`
- `notes/2026-06-18_obs-2source-load-test.md`
- `notes/2026-06-26_hyperpixel-breakage-season3-pause.md`

## [FACT] 2026-07-20に得た観測

- ユーザーから「途中からNDIが自動起動しなくなり、Wi-Fiにも上がらなくなった」と報告された。
- ユーザーが物理Ethernetを接続し、実機が`192.168.0.13`を取得したことを確認した。
- Codex実行環境から`ond@192.168.0.13`へSSH接続を試行した。
- SSH endpointは応答し、ED25519 host keyを提示した。
- `ond`ユーザーに対する非対話認証は`Permission denied (publickey,password).`で終了した。
- Mac側で確認できた既存のED25519鍵候補を明示指定して再試行したが、認証は成立しなかった。
- ユーザーは`ond@pi5-ond.local`へパスワード認証でログインできた。Bonjour名とSSH serverは動作している。
- Codexも同じローカルIoT認証経路でログインし、実機内部の無変更診断を取得した。
- OSはDebian GNU/Linux 13 (trixie)、kernelは`6.12.75+rpt-rpi-2712`、architectureはarm64。
- `ond800-streamer.service`はactive/enabledだが、pyudev callbackが`TypeError: Orchestrator._on_udev_event() missing 1 required positional argument: 'device'`で終了していた。
- pyudev 0.24.3の`MonitorObserver`はcallbackを`callback(device)`として呼ぶ。実装側は`_on_udev_event(self, action, device)`を直接登録しており、引数契約が一致していない。
- C922とEMEET C960はV4L2デバイスとして認識されているが、streamer processはカメラデバイスを占有していない。
- `wlan0`はrfkillされておらず周囲のSSIDを走査できるが、NetworkManagerの保存済み接続一覧には有線とloopbackしかなく、Wi-Fi接続profileが存在しない。
- 実機checkoutは`main`の`6fa5d74`でclean。Mac側checkoutの`5876c30`より古い。
- root filesystemは57GB中11%使用、温度は52.7°C。現在のthrottle bitsは解除済みだが、boot中と診断中に複数回`Undervoltage detected!`が記録され、その後normaliseしている。

## [INTERPRETATION] 現時点で読めること

- ユーザーのDHCP確認とSSH応答を合わせると、物理LAN、IP層、SSH endpointまでの経路は生存している可能性が高い。
- 液晶破損、Wi-Fi不参加、NDI自動起動停止は同時期の症状として扱う必要があるが、同一原因と断定できない。
- 鍵認証は成立しなかったが、ローカルIoTの初期パスワード認証は正常だった。これは公開サーバーの侵害兆候ではなく、このworkspaceの通常初期運用として扱う。
- 表示デバイスが`/dev/fb0`として残っている場合、物理的に割れていてもstreamerがdisplay branchを構築する可能性がある。ただし、今回の停止原因かは未確認。
- NDI自動起動停止の直接原因は、systemd unitの停止ではなく、サービスprocess内のpyudev observer threadだけがcallback引数不一致で死んだことと判断できる。
- Wi-Fi不参加の直接状態は、無線ハード故障ではなく保存済み接続profile不在である。profileが消えた経緯は未確定。

## [HYPOTHESIS] 原因候補と判別実験

### H1: SSH認証状態だけが以前と変わった — 一部棄却

パスワード認証は成功した。鍵認証が成立しない理由は最低配信復旧の阻害要因ではないため、現時点では追跡を止める。

### H2: Wi-Fi設定またはnetwork serviceが起動していない — 絞り込み済み

NetworkManager、wlan0、scan、rfkillは動作している。保存済みWi-Fi接続profileが存在しない。次は既知SSIDのprofileを再作成し、自動接続を検証する。

### H3: `ond800-streamer.service`がdisabled、failed、または再起動ループ中 — 棄却、別原因確定

unitはactive/enabled。pyudev 0.24.3がcallbackへdevice一個だけを渡すのに、実装がactionとdeviceの二引数を要求したためobserver threadが死亡している。

### H4: カメラ、NDI SDK、Python/GStreamer、PID lockのいずれかで起動失敗

判別: `fuser /dev/video*`、`v4l2-ctl --list-devices`、共有ライブラリ、Python import、PIDファイル、サービスjournalを順に確認する。

### H5: 電源低下、ストレージ、ファイルシステム、別OS起動等の基盤障害

判別: `vcgencmd get_throttled`、温度、uptime、boot ID、mount、空き容量、kernel journal、Git checkout/commitを確認する。

## [UNKNOWN]

- 保存済みWi-Fi profileが消えた時点と原因。
- NDI SDKが現在も正常送信できるか。
- HyperPixelの破損が表示面だけか、DPI/GPIO/電源経路へ波及したか。
- NDI自動起動停止とWi-Fi停止が同一boot eventで発生したか。
- 低電圧の原因が電源アダプタ、ケーブル、USB機器負荷のどこにあるか。

## [INNER] 内観メモ

液晶が割れたあと、OND800は死んだというより天岩戸へ引きこもったように見える。
外からは画面もNDIもWi-Fiも見えないが、有線LANを一本差すと岩戸の内側からSSHの戸口だけは返事をした。

ここで豪華なSeason 3を呼び戻す必要はない。まずカメラ一台の光を外へ返す。
表示器を失っても配信機材として立つなら、破損はコックピットの死ではなく、ヘッドレス形態への換装試験になる。

一方で「返事がした」ことと「中身が健康」を混ぜない。岩戸の中はまだ見えていない。

## [MARKETING-CANDIDATE] マーケ砲候補

> 液晶が割れ、NDIもWi-Fiも沈黙した。OND800、天岩戸ごもりなう。  
> だが物理LANを一本ぶっ刺すと、SSHの戸口だけは生きていた。  
> 買い直す前に、壊れたモビルスーツを最低配信機材として現場復帰させる。

別案:

> 画面が死んでも、配信機材まで死なせない。  
> OND800の次の実験は新機能ではなく、破損状態からの単眼・ヘッドレス再出撃である。

ガムテ砲案:

> ロマン砲の液晶が割れて天岩戸へ引きこもった。  
> それでもPi、カメラ、SSH、NDIコードは残っている。  
> ならば今撃てる一発へ縮退する。OND800、最低配信用ガムテ砲への現場改修。

天岩戸パージ案:

> 財布ヒーラーもジャンク箱ヒーラーも待っているだけでは来ない。
> 割れた液晶が岩戸になって電力まで吸うなら、測量してパージする。
> OND800は豪華な完成待ちをやめ、今あるPi、カメラ、LANで配信へ戻る。

この欄は公開採用前の候補であり、READMEや外部媒体へ自動転記しない。実機診断後、観測事実と矛盾する部分を修正してUser Gateへ返す。

## 次の実験順

1. ユーザー側Bashまたは復旧した鍵認証から、無変更の基盤診断を取得する。
2. systemdとカメラ占有を確認するまで、`python3 -m streamer`を直接起動しない。
3. 原因をWi-Fi、streamer、カメラ／NDI、表示器、電源／ストレージへ分離する。
4. 最短の復旧枝として、1カメラ・NDI-only・systemd自動起動を検証する。
5. OBS側で映像受信と音声経路を別々に確認し、最低配信構成を閉じる。
6. 取得したcommand、原log、observed result、test boundaryを本ノートへ追記する。

## 停止条件・User Gate

- ストレージ破損、低電圧、異常発熱、USB電源短絡、DPI/GPIO物理損傷の兆候があれば、サービス変更より先に停止する。
- Wi-Fi資格情報、秘密鍵、authorized_keys全文、配信キーはノートへ記載しない。Bonjour名とLAN内IPは通常のローカルIoT運用情報として扱う。
- READMEの現状表示やマーケコピーへ昇格する前に、実機診断結果を反映してUser Gateへ返す。
- 電力測量は`notes/2026-07-20_post-breakage-electrical-survey.md`へ分離し、本ログから測定値と解釈を混線させない。

## Provenance

- 人間側観測・物理作業: fusamofu / Mitsuru Saitō
- リポジトリ・manifest監査、SSH到達／認証試行、初期記録: OpenAI Codex
- 正本規約: ZeroRoomLab-manifest `note/AGENTS.md`、`manifest-operating-model.ja.md`、`technical-communication-register.ja.md`
