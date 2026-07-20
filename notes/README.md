# notes

実験ノート・作業ログ置き場。AIエージェント・人間共通の記録場所。

GitHub Issuesの代替として機能する(AIエージェントがIssueにアクセスできない場合があるため)。

## ファイル命名

`YYYY-MM-DD_短い説明.md`

例: `2026-06-15_v4l2ndi-pi5-first-test.md`

## 記録すべき内容

- 冒頭に対象、検証範囲、除外範囲、状態、出典を書く
- `[FACT]`: 実行したこと、観測結果、成功・失敗、原エラー、性能値
- `[INTERPRETATION]`: 事実から読めること。事実そのものとは分ける
- `[HYPOTHESIS]`: 未検証の原因候補と、それを判別する次の実験
- `[INNER]`: 内観メモ、所感、ポエム、身体感覚、雑な類推
- `[MARKETING-CANDIDATE]`: README、note.com、X、動画等へ転用しうるマーケ砲候補
- `[UNKNOWN]`: 取れていない情報。未観測を「存在しない」へ変換しない
- 次にやるべきこと、停止条件、User Gate
- hardware/runtime → commit/version → command/workload → log/measurement → observed result → test boundary の証拠列
- 作業した人間・モデル・エージェント名とProvenance（分かる範囲）

## レジスターと昇格境界

- `notes/` は一次資料・実験ログ・思考の芽を保存する場所であり、ここへ書いた時点では正規仕様や実装済み契約にならない。
- 事実、解釈、仮説、内観、マーケ候補を同じ段落へ混ぜない。内観メモを削って無機質な障害票だけにしない。
- マーケ砲は観測事実を弱めずに強く書いてよいが、`[MARKETING-CANDIDATE]` のままでは公開採用済みではない。
- README冒頭、技術文書、リポジトリ内`notes/`、note.com、X、YouTubeは別の媒体レジスターとして扱う。
- ノートからREADME、`docs/`、実装契約へ昇格する場合は、対象、差分、根拠、User Gateを明示する。
- LANアドレス、Bonjour名、ローカルIoTの初期認証方式を、GIPへ晒す公開サーバーと同じ基準で自動的に秘密扱いしない。機密性は対象workspaceの運用、ユーザー指定、実際の公開範囲から判定する。
- 詳細規約はZeroRoomLab-manifestの`note/AGENTS.md`、`docs/operations/manifest-operating-model.ja.md`、`docs/operations/technical-communication-register.ja.md`を正本として参照する。

## 重要ログ

- `2026-06-26_hyperpixel-breakage-season3-pause.md`: HyperPixel 4.0物理破損、Season 3一時停止、操作パネル耐久化・筐体保護・交換性の設計入力。
- `2026-07-20_post-hyperpixel-ama-no-iwato-recovery.md`: 液晶破損後にNDI自動起動とWi-Fi接続が停止した実機の、天岩戸ごもり復旧セッション。事実、仮説、内観、マーケ砲候補を分離して追記する。
- `2026-07-20_post-breakage-electrical-survey.md`: 液晶破損後の低電圧、電源・ケーブル・液晶リーク仮説、夕立／豪雪停電を含む実行環境を比較測量する。
- `2026-07-20_amedas-ambient-and-single-variable-plan.md`: 過去OND負荷ログと高畠アメダス外気を同一系列で比較し、ガムテ、電源、USB負荷を非侵襲な順に単体変数化する。
- `2026-07-20_pi5-power-delivery-constraint-reconstruction.md`: repositoryから欠落していたGaN 140W PD検証を操作者報告から再構成し、5V/3A縮退、5V安定化電源はbench対照、PoE HAT／battery HATは配備設計という分岐を記録する。
- `2026-07-21_wifi-fallback-restoration.md`: 消失していたNetworkManagerのWi-Fi profileをfallbackとして復元し、Ethernet優先route、ローカル認証境界、Wi-Fi側疎通を記録する。
- `2026-07-21_ndi-interface-switch-reconnect-research.md`: 有線からWi-FiへのIP変更後にOBSが自動再接続しない挙動を、NDI公式仕様、DistroAV 6.2.1実装、実機結果から切り分ける。演者の復帰時間を優先する`SHOW_CONTINUITY`哲学、receiver watchdog MVP、将来の`BROADCAST_GUARD`を分離して記録する。
- `2026-07-21_local-bootstrap-and-pin-policy.md`: `ond/ond`をlocal公開bootstrapとして扱い、operator PIN、SSH管理口、LAB／配布profileを分離する。
