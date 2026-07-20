# OND800 Wi-Fi fallback復元

状態: `[ACTIVE]` `[Layer A]` `[FALLBACK-CONFIGURED]` `[PASSWORD-LOCAL-ONLY]`
実施日: 2026-07-21
対象: OND800 Pi 5 `wlan0`、NetworkManager、Ethernet不在時のWi-Fi fallback
除外範囲: 物理LAN抜去試験、再boot後試験、長時間packet loss、電波強度分布

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
- 物理LANを抜く試験は今回行っていない。Wi-Fi interface単独のgateway疎通と待機default routeまでは確認済みである。

## [LOCAL SECRET BOUNDARY]

- Mac側の認証情報はrepository直下`ond-config/wifi.env`へ保存した。
- `.gitignore`は`/ond-config/`をディレクトリ単位で除外する。
- local directoryはmode `700`、認証ファイルはmode `600`にした。
- password本文を本Note、Git差分、commit messageへ記録しない。
- `.gitignore`だけをsecurity boundaryとせず、filesystem permissionと実機側NetworkManager keyfile permissionも併用する。

## [UNKNOWN]

- 以前のWi-Fi profileが消えた時刻と原因
- HAT破損、低電圧、filesystem書き込み、NetworkManager移行、手動削除のどれが関与したか
- Ethernet物理抜去後からWi-Fi default route切替までの実時間
- 再boot後も同じprofileで接続することの実機再現

## 次の安全な確認候補

配信停止を許容できる窓で、次の順に確認する。

1. Wi-Fi側SSH sessionを先に確立する
2. Ethernet cableを抜去する
3. default route、NDI送出、Bonjour名、低電圧eventを確認する
4. Ethernetを戻し、metric `100`へ優先復帰することを確認する

## Provenance

- SSID、認証情報、fallback要件: fusamofu / Mitsuru Saitō
- NetworkManager profile作成、permission、route、疎通確認: OpenAI Codex
