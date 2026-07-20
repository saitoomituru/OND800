# NDI送信IF切替後のOBS再接続 — 既知仕様と実装境界調査

状態: `[RESEARCHED]` `[KNOWN-ARCHITECTURAL-EDGE]` `[DISTROAV-RECOVERY-GAP]`
調査日: 2026-07-21
対象: NDI senderのEthernet→Wi-Fi切替、mDNS再広告、NDI transport、OBS DistroAV receiver
一次資料: NDI公式documentation、DistroAV公式repository／release、OBS Project公式obs-websocket repository

## 結論

今回の挙動は未知の物理現象ではない。NDIが切断後も旧IP／port endpointを保持する既知設計と、DistroAV 6.2.1が接続数0になってもsource finderの新endpointからreceiverを自動再生成しない実装境界の合成として説明できる。

ただし、`EthernetからWi-Fiへ同名sourceが移動した場合にDistroAVが再接続しない`という完全一致のupstream issueは、2026-07-21時点の公式issue tracker検索では発見できなかった。既知のNDI architecture上にあるDistroAV未整理edge caseであり、既知bug番号付きの枯れたワンクリック設定ではない。

## [FACT] OND800実験列

1. Ethernet抜去後、Avahiは2つの`_ndi._tcp` sourceを`wlan0`へ再登録した。
2. Mac側`dns-sd`も両sourceを検出した。
3. senderはframes増加、drops 0を維持したが、両sourceのconnectionsは1→0になった。
4. sender serviceだけを再起動してもconnections 0のままだった。
5. OBS側からsourceを明示再取得すると、両sourceともconnections 1へ戻った。

したがって、Bonjour再広告、sender映像生成、receiver transport再接続は別状態機械である。

## [FACT] 使用中の受信softwareは現行世代

MacのOBS log `2026-07-13 17-49-21.txt`は次を記録している。

- DistroAV 6.2.1
- NDI Runtime 6.3.2.0

DistroAV 6.2.1は2026-04-24公開の現行releaseだった。旧OBS-NDI 4.x固有問題として更新だけで閉じる枝ではない。

出典: [DistroAV releases](https://github.com/DistroAV/DistroAV/releases)

## [FACT] NDI receiverの既知設計

NDI公式receiver documentationは、sourceがnetworkから消えてもreceiverは接続状態を維持でき、sourceが再び利用可能になれば自動再接続すると説明する。一方、NDI公式FAQは、不正終了扱いの切断後、receiverが旧senderのIP addressとportを既定75分保持すると説明する。

- [NDI Receiver SDK](https://docs.ndi.video/all/developing-with-ndi/sdk/ndi-recv)
- [Why does my NDI connection stay active once the source is offline?](https://docs.ndi.video/all/faq/ndi-tools/why-does-my-ndi-connection-stay-active-once-the-source-is-offline)

`同じsourceが同じendpointへ戻る`場合の自動再接続と、`同じsource名が別IP endpointへ移る`場合は同一ではない。今回の観測は、receiverが旧`192.168.0.13:port`を保持し、新しい`192.168.0.14:port`を既存sessionの復帰先として採用しなかったと読むと整合する。これは公式文面と実験からの推論であり、NDI内部実装の直接traceではない。

MAC address変化そのものより、NDI sessionから見たIP address／port endpoint変化が主要境界である。MACはARP等のL2解決には関与するが、NDI receiverが保持すると公式に説明する対象はIPとportである。

## [FACT] DistroAV 6.2.1のreceiver loop

DistroAVの`ndi-source.cpp`は、選択されたNDI source名でreceiverを生成する。receiver生成後、`recv_get_no_connections()`が0ならempty frameを処理して100ms sleepし、loopを継続する。接続数0を契機にfinderを再照会したり、同名sourceのendpoint更新を比較してreceiverを破棄・再生成したりする枝はない。

receiver resetはsource名、bandwidth、latency等の設定変更で立つ。同じsource名が新IPへ再広告されただけでは、OBS設定文字列は変わらないためreset条件にならない。

出典: [DistroAV `ndi-source.cpp`](https://github.com/DistroAV/DistroAV/blob/6.2.1/src/ndi-source.cpp#L385-L603)

## 対策の成熟度

### A. 最も枯れた対策: active session中にendpointを変えない

NDI公式は、複数NICをsoftwareで扱うよりOS／machine configuration levelのNIC teamingを通常は好ましいとし、異なるIP rangeの複数networkはOSとNDIでrobustに扱えない場合があると注意する。

[NDI NIC Selection](https://docs.ndi.video/all/getting-started/white-paper/nic-selection)

したがって放送中の無停止切替が必須なら、applicationが有線IP→Wi-Fi IPへ飛ぶ構成より、endpointを変えないL2／OS側冗長化が定石である。ただしEthernetとWi-Fiのbondingはplatform／driver／AP制約が大きく、OND800のガムテ砲で最初に採る軽量解ではない。

### B. OND800向け現実解: OBS receiver watchdog

今回、OBS側の明示再取得で即復帰した。従って小規模運用では次が費用対効果の高い対策になる。

1. `hiplab-fallback`への切替とNDI Bonjour広告を検出する
2. OBS側で対象NDI sourceを一度停止する
3. 数秒後に同じsource名でreceiverを再生成する
4. sender側connections 1または映像frame復帰を確認する
5. debounce／cooldownを設け、回線flapで再起動loopにしない

OBS 28以降に同梱されるobs-websocket 5.xにはscene itemのenable／disableを切り替える`SetSceneItemEnabled`がある。DistroAV sourceのvisibility behaviorをstop／resume系に固定すれば、receiver threadを破棄・再生成する回復actuatorとして利用できる。

- [obs-websocket公式repository](https://github.com/obsproject/obs-websocket)
- [obs-websocket releases／`SetSceneItemEnabled`](https://github.com/obsproject/obs-websocket/releases)

単なるsender restartは今回の実験で無効だったため、Pi側NetworkManager dispatcherから`systemctl restart ond800-streamer`だけを行う実装は採らない。

### C. Discovery Server: 観測と管理には有効、transport移行の魔法ではない

NDI Discovery ServerはmDNSを中央registryへ置き換え、複数subnet、source／receiver監視、receiver controlへ進む基盤になる。複数server redundancyも公式対応である。

一方、NDI公式はdiscovery後のvideo sessionをIP addressとportからなる2 endpointとして説明する。Discovery Serverを置くだけで、DistroAVの既存receiver instanceが別IPへ自動migrationする保証はない。

- [NDI Discovery Server](https://docs.ndi.video/all/docs/white-paper/discovery-and-registration/discovery-service)
- [Receiver monitoring and control](https://docs.ndi.video/all/developer-guides/receiver-discoverability-monitoring-and-control-overview)

source／receiverが増え、遠隔監視と再接続制御を一つのcontrol planeへ集める段階では有力だが、現在の2camera最低配信にはOBS watchdogより重い。

### D. NDI native failsafe: 別sender冗長化用

NDI sender SDKにはfailsafe sourceがあり、sender故障時にreceiverを別sourceへ自動切替し、元source復帰時に戻せる。これは同一PiのNIC変更を透過化する機能ではなく、独立したbackup senderを用意する冗長化である。

[NDI Sender SDK failsafe](https://docs.ndi.video/all/developing-with-ndi/sdk/ndi-send)

## 工学判断

| 項目 | 判定 |
|---|---|
| Wi-Fi IP fallback | 実機確認済み |
| Bonjour／NDI source再広告 | 自動復旧済み |
| sender process再起動 | receiver復帰には無効 |
| OBS明示再取得 | receiver復帰に有効 |
| NDIの旧endpoint保持 | 既知仕様 |
| DistroAVのIP変更追従 | 現行6.2.1で自動復旧せず。完全一致issueは未発見 |
| Discovery Server単独導入 | discovery改善。transport自動migrationは未保証 |
| 推奨する最初の実装 | OBS側receiver watchdog／再取得actuator |

## [UNKNOWN]

- receiverを操作せず75分以上待った時、新endpointへ自動再接続するか
- NDI Runtime内部でsource名とURLをどの時点で再解決するか
- DistroAV upstreamが本edge caseを未報告bug、仕様、NDI Runtime側責務のどれと判定するか
- scene item enable／disableだけで、現在の各OBS scene配置すべてがreceiver recreateへ到達するか

## 次の実装前probe

1. OBS側2sourceについて、scene item disable→enableで再取得と同じ復帰になるか確認する
2. obs-websocketから同操作を行い、sender connections 0→1の時間を測る
3. 連続flapを模擬せず、一回の有線→Wi-Fi切替でdebounce時間を決める
4. probeが通った後にだけ、監視scriptまたはcockpit操作へ昇格する

## Provenance

- 物理LAN抜去、OBS明示再取得: fusamofu / Mitsuru Saitō
- 実機log、Bonjour、DistroAV local version、公式資料、upstream code／issue調査: OpenAI Codex
