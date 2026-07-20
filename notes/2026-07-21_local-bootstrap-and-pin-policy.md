# OND800公開bootstrapとPIN運用メモ

状態: `[ACTIVE]` `[Layer A]` `[USER-DIRECTED]` `[DESIGN-RECORDED]`

## [FACT]

- 現在の実機はLinux user `ond`、SSH password `ond`でlocal LANから接続できる。
- ユーザーは、将来firmwareとして固める場合も`ond/ond`を初期bootstrap値として公開可能と判断した。
- 想定するOND800は、cloudへGIP公開するserverではなく、NAT traversalを行わないlocal edge IoTである。
- password変更GUI、4桁／6桁PIN、claim state machineは現時点では未実装である。

## [INTERPRETATION]

`ond/ond`は秘密として強度を持たせる値ではなく、初回到達性を持たせる公開手順である。したがって、repositoryへ書かれたこと自体をcredential leakとは扱わない。

一方、公開bootstrapが恒久的なroot相当管理権限と同義になると、local LAN内の別機器、持ち出し先network、誤port forwardingから操作されうる。対策はcloud server並みの儀礼を輸入することではなく、用途ごとの認証面を分けることである。

逆に、LAN edge機へcloud前提の認証依存を積みすぎると、停電、時計ずれ、外部service停止、token失効、回線断で、所有者自身が現場機へ入れない`UFOムーブ`が起きる。これは強固さではなく、local recoveryを外部条件へ売り渡す別の故障modeである。

- 初回／復旧: `ond/ond`
- 日常操作: 6桁PINをdefault候補、4桁は低権限または物理近接
- maintenance: SSH key、owner password、または明示的なLAB profile

## [ENGINEERING DECISION]

- `ond/ond`はLAB／local recovery用の公開bootstrap credentialとして文書化する。
- GUIには初期認証状態を隠さず表示し、認証変更を一操作で開始できるようにする。
- PINをLinux SSH passwordへ自動流用しない。
- cloud account、外部認証provider、強制的な長文passwordを最低起動条件へしない。
- cloud relay、UPnP自動開放、NAT traversalを既定実装へ入れない。
- 市販または第三者配布profileでは、個体別またはuser-defined bootstrapへ切り替える。

正規設計は`docs/local-onboarding-auth.md`へ分離した。

## [UNKNOWN]

- GUIをどのservice／portで提供するか
- 物理displayがない個体で、recovery actionを何に割り当てるか
- PINが許可する操作権限の境界
- PINの失敗回数、backoff、session lifetime
- claim情報の保存先と、低電圧／filesystem recovery時のatomicity
- distribution profileをbuild時、初回起動時、個体provisioning時のどこで決定するか

## [INNER]

鍵を重くしすぎて、火事の現場で戸が開かない機械は困る。
だが戸に「誰でも開く」と書いたまま、舞台の裏口まで同じ鍵にする必要もない。

入口は軽く、今どの入口が開いているかは派手に見せる。
操縦桿のPINと、機関室のSSH鍵は、同じ指で触れても別の錠前にする。

## [MARKETING-CANDIDATE]

> 初期userは`ond`。初期passwordも`ond`。
> cloud accountを作る前に、LAN一本で機体へ入れる。
> 固くするか、軽いまま飛ばすかは、所有者がGUIで決める。

このcopyは設計候補であり、GUI実装済みを意味しない。

## Provenance

- local IoTの公開bootstrap、PIN志向、NAT traversal回避: fusamofu / Mitsuru Saitō
- 認証面、device state、deployment profileへの構造化: OpenAI Codex
