# OND800 障害復旧哲学 — 演者のショー継続を目的関数にする

状態: `[ADOPTED-DESIGN]` `[MVP-PENDING]`
制定日: 2026-07-21
対象: network interface切替、NDI receiver再接続、将来の音声・配信先フェールオーバー
根拠: README／AGENTSの演者主権、2026-07-21のEthernet→Wi-Fi実機試験

追跡Issue: [#3 MVP: NDI endpoint変更後にOBS receiverを自動再生成する](https://github.com/saitoomituru/OND800/issues/3)

## 1. 採用する目的関数

OND800はスポンサー、放送局、複数人の技術スタッフを守るための機材ではなく、演者本人へ撮影空間の主権を戻すためのデバイスである。スポンサーの財布を演者の人生より上位に置く商業放送哲学とは相容れない。従って障害処理の第一KPIは、障害の存在を完全に隠すことでも、誤接続可能性をゼロへ追い込むことでもない。

> 許可済みの撮影系が別経路で再出現した時、演者の認知と操作を奪わず、ショーへ戻るまでの時間を最小化する。

芸人にとって炎上より致命的なのは無風である。事故が画面へ出た場合でも、ソロ演者はリアクションや物語としてコンテンツへ転換できる。一方、復旧のためにOBS設定画面を掘り、sourceを選び直す時間は、その転換可能性ごとショーを止める。OND800はこの非対称性を設計入力にする。

## 2. upstreamとの関係

NDI receiverが不正切断後も旧IP address／portを既定75分保持することは公式FAQに記載された仕様である。ただし、その保持時間が誤接続、送信者の成り代わり、公共放送事故を防ぐために選ばれたという設計意図は、確認できた一次資料には記載されていない。

従って次を分離する。

- `[FACT]`: receiverが旧endpointを保持する。今回、同名sourceがWi-Fi側へ再広告されてもDistroAV 6.2.1は既存receiverを自動再生成しなかった。
- `[INTERPRETATION]`: 保持的な復旧は、endpoint変更を安易に受け入れない安全側の挙動として読むことができる。
- `[UNKNOWN]`: 75分という値と、誤接続／media hijack対策との直接の設計因果。

upstreamを「悪い既存ライブラリ」と技術的に断罪しない。大規模な商業放送では、誤った映像を出す損失が復帰の遅さを上回る場合がある。ただし、そのスポンサー保護を演者より上位に置く哲学まで中立化する必要はない。OND800は立場の不一致を明言し、技術差分はadapterとして実装する。

## 3. 本流profileとfork境界

### `SHOW_CONTINUITY` — OND800本流

- 許可済みsource名が切断後に別endpointで再発見された場合、receiver再生成を試みる
- debounceとcooldownを設け、network flapで再接続loopを作らない
- source名だけを全LANで無条件に信用せず、事前に設定されたscope内へ限定する
- 自動復帰できなければ、演者へは片手1操作の「再取得」だけを提示する
- 原因、endpoint、試行履歴は事後logへ送り、飛行中UIを診断卓にしない

### 商業放送profile — 本流の非目標

- endpoint変更時のoperator確認、厳格な固定、スポンサー損失回避を主目的にするなら、その目的に合わせて作られた商業デバイスを選べる
- OND800へ必要な場合も、外部profileまたはforkとして追加できる
- 限られた本流の開発資源を、既存商業機材の安価な再生産へ使わない

技術的にはrisk配分の違いである。哲学的には、誰を主人として守るかの対立である。OND800は演者を主人に選ぶ。

## 4. NDI再接続MVP

実装境界はOBS／SAO800側のreceiver watchdogとする。Pi senderの再起動だけでは復帰しなかった実機結果があるため、sender restartを主actuatorにしない。

### Phase 0 — actuator probe

1. OBS内の対象NDI scene itemをdisable→enableする
2. DistroAV receiverが破棄・再生成されることを確認する
3. Pi側logで`connections=0`から`connections=1`へ戻る時間を測る
4. 2sourceそれぞれと、複数sceneから参照される場合の挙動を確認する

### Phase 1 — 最小自動復帰

1. source消失またはOND800のnetwork interface変更を検知する
2. 新しい広告が安定するまでdebounceする
3. obs-websocketの`SetSceneItemEnabled`で対象itemを停止・再開する
4. 復帰を確認し、成功または試行上限到達を記録する
5. cooldown中の重複actuationを抑止する

### 受入条件

- Ethernet→Wi-Fi切替後、OBSのsource設定画面を開かずに2sourceが復帰する
- 一回の切替で無限restart／toggle loopを起こさない
- 許可対象外のscene itemを変更しない
- 自動復帰失敗時も、片手1操作の手動再取得へ降りられる
- sender service restartだけに依存しない
- mode、検出時刻、actuation、結果をlogへ残す

## 5. 非目標

- NDI Runtime内部の75分保持を改変すること
- Discovery Serverだけでtransport migrationが解決したと見なすこと
- 異なるLAN上の任意の同名sourceへ無条件で接続すること
- 商業放送profileをOND800本流のroadmapへ追加すること
- 飛行中の演者へ詳細なnetwork診断を要求すること

## 6. 実装配置の境界

receiver再生成はOBSを操作するため、最終的にはLayer 3のSAO800責務が自然である。ただし、OND800は「回線が切り替わった」「正規sourceが再広告された」という意図または状態eventを送ってよい。OBS固有のscene item IDやDistroAV内部状態をOND800 streamer本体へ逆流させない。

関連:

- [GitHub Issue #3](https://github.com/saitoomituru/OND800/issues/3)
- [`../notes/2026-07-21_ndi-interface-switch-reconnect-research.md`](../notes/2026-07-21_ndi-interface-switch-reconnect-research.md)
- [`interface_spec.md`](interface_spec.md)
- [NDI Receiver SDK](https://docs.ndi.video/all/developing-with-ndi/sdk/ndi-recv)
- [NDI旧endpoint保持FAQ](https://docs.ndi.video/all/faq/ndi-tools/why-does-my-ndi-connection-stay-active-once-the-source-is-offline)
