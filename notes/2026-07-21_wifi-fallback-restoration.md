# OND800 Wi-Fi fallback復元

状態: `[ACTIVE]` `[Layer A]` `[FALLBACK-CONFIGURED]` `[PASSWORD-LOCAL-ONLY]`
実施日: 2026-07-21
対象: OND800 Pi 5 `wlan0`、NetworkManager、Ethernet不在時のWi-Fi fallback
除外範囲: 再boot後試験、長時間packet loss、電波強度分布、受信側OBSの自動再接続実装

## [FACT] 変更前

- 実機はNetworkManager管理だった。
- `eth0`は`有線接続 1`で接続中、`wlan0`はdisconnectedだった。
- 保存済みWi-Fi connection profileは存在しなかった。
- したがって、過去にWi-Fi設定が存在した可能性は残るが、今回接続時点のNetworkManager profileとしては消失していた。

## [FACT] fallback profile

- connection名: `hiplab-fallback`
- SSID: `hiplab`
- interface: `wlan0`
- security: WPA-PSK
- autoconnect: yes
- autoconnect priority: `-10`
- IPv4 route metric: `600`
- IPv6 route metric: `600`

Ethernetのdefault route metricは`100`、Wi-Fiは`600`だった。両方が存在する時はEthernetを優先し、Ethernet routeが消えた時にWi-Fiを残す構成である。

## [FACT] 疎通確認

- `wlan0`は`hiplab-fallback`へ接続した。
- Wi-Fi側は`192.168.0.14/24`を取得した。
- `ping -I wlan0 192.168.0.1`は3 packets transmitted、3 received、0% packet lossだった。
- NetworkManagerのsystem connection fileはroot所有、mode `600`だった。

## [FACT] 物理LAN抜去fallback

操作者が物理Ethernet cableを抜去した後、次を確認した。

- MacからWi-Fi側`192.168.0.14`へのpingは3 packets transmitted、3 received、0% packet loss、約5.2〜8.3msだった。
- Wi-Fi側IPへのSSH接続に成功した。旧有線IPとWi-Fi側が提示したED25519 host key fingerprintは一致し、同じOND800実機であることを確認した。
- `eth0`は`unavailable`、`wlan0`は`hiplab-fallback`でconnectedだった。
- default routeは`wlan0`、source `192.168.0.14`、metric `600`へ切り替わっていた。
- Avahiは06:02:50に`wlan0`の`192.168.0.14`を登録し、06:06:24に`eth0`の`192.168.0.13`をwithdrawした。

以上により、物理LAN不在時のIP接続、SSH、default routeの自動fallbackは実機で成立した。

## [FACT] BonjourとNDI transportは別に復旧した

- Pi上のAvahiは、C922とC960の2つの`_ndi._tcp` serviceを`wlan0`上へ登録した。
- Mac側の`dns-sd -B _ndi._tcp local.`でも、2026-07-21 06:09:08に両sourceを検出した。
- `ond800-streamer.service`はrunningを維持し、両cameraともframes増加、drops 0を継続した。
- 一方、受信接続は06:06:19〜20頃に両sourceとも`connections=1`から`0`へ落ちた。
- 06:09:31に送信側`ond800-streamer.service`を手動再起動し、両NDI sourceを再生成した。
- 再起動後もframesは増加しdrops 0だったが、06:09:52時点で両sourceとも`connections=0`だった。

この結果では、Bonjour serviceのWi-Fi再広告に追加hookは不要だった。未復旧なのは既存NDI transport／受信client sessionであり、送信側streamer再起動だけでは回復しなかった。自動化するならNetworkManager link changeから送信再広告だけを叩くのではなく、受信側のsource rediscovery、reopen、OBS source再選択まで含む回復protocolが必要である。

## [LOCAL SECRET BOUNDARY]

- Mac側の認証情報はrepository直下`ond-config/wifi.env`へ保存した。
- `.gitignore`は`/ond-config/`をディレクトリ単位で除外する。
- local directoryはmode `700`、認証ファイルはmode `600`にした。
- password本文を本Note、Git差分、commit messageへ記録しない。
- `.gitignore`だけをsecurity boundaryとせず、filesystem permissionと実機側NetworkManager keyfile permissionも併用する。

## [UNKNOWN]

- 以前のWi-Fi profileが消えた時刻と原因
- HAT破損、低電圧、filesystem書き込み、NetworkManager移行、手動削除のどれが関与したか
- 再boot後も同じprofileで接続することの実機再現
- OBS側sourceの無効→有効または再選択で`connections=1`へ戻るか
- 受信側の自動再接続がsource名、IP address、NDI library、OBS pluginのどこで止まったか

## 次の安全な確認候補

再bootを許容できる窓で、次を確認する。

1. Wi-Fi profileのboot後自動接続
2. Ethernetを戻した時のmetric `100`への優先復帰
3. OBS側NDI sourceの再選択によるtransport再接続
4. 受信側reopenまで含むlink-change回復hookの設計

## Provenance

- SSID、認証情報、fallback要件: fusamofu / Mitsuru Saitō
- NetworkManager profile作成、permission、route、疎通確認: OpenAI Codex
