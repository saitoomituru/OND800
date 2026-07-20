# OND800 Pi 5電力経路 — 欠落していたPD検証の再構成

状態: `[RECONSTRUCTED]` `[SOURCE-GAP]` `[ENGINEERING-DECISION]` `[RESOURCE-GATED]`  
再構成日: 2026-07-20  
対象: OND800 Pi 5のUSB-C給電、GaN 140W PD電源、5V/3A縮退運用、将来の電力経路  
出典: fusamofu / Mitsuru Saitōによる過去実験結果の口頭再提示  
欠落範囲: 元実験日時、アダプタ型番、PD analyzer出力、PDO列、ケーブル型番、DC rail実測値はrepository内で発見できていない

## [FACT: OPERATOR-REPORTED PRIOR RESULT]

- 過去にGaN 140WのUSB PDアダプタをOND800 Pi 5へ接続して検証した。
- OND800の受電側は5V modeで動作し、高電圧PD modeを受けなかった。
- そのため、電源側の総定格が140Wでも、Pi側がその電圧・電力能力へ最大効率追従する経路にはならなかった。
- 現在は5V/3Aで最低配信機能を維持する縮退運用になっている。
- 専用電源、PoE HAT、battery HAT等の代替部材は、投げ銭またはジャンク箱から入手できるまでresource-gatedである。

この節は操作者が実施済み結果として再提示した事実を記録する。ただし元の生logが欠落しているため、交渉PDO、実電圧、実電流、発熱、低電圧event列を新たに捏造しない。

## [INTERPRETATION]

140W級の供給能力を持つ電源へ交換しても、受電側が5V経路に留まるなら、USB-C電源を高W品へ順次交換する探索は支配制約へ届かない。総W数ではなく、5V railで実際に受け渡せる電流、ケーブルと接点の電圧降下、PiとUSB周辺機器の合計負荷が境界になる。

したがって5V/3Aは「合理的な完成電源」ではなく、現在ある部材でNDIを止めないための工学的縮退モードである。次の設計枝はUSB-Cで踏ん張り続けることではなく、次のいずれかへ電力経路を変更することにある。

1. Pi 5向け専用5V高電流電源
2. Ethernet配線へ統合できるPoE HAT
3. 瞬断・停電耐性も与えるbattery HATまたは同等のbuffered supply

どの枝を採用するかは、部材入手、PoE switch余力、停電時間、カメラ負荷、持ち運び要件を同時に評価して決める。

## [ENGINEERING DECISION]

- 追加の汎用高W USB PDアダプタ交換を、低電圧解消の主実験にはしない。
- 現在は5V/3A envelope内で、NDI drops、低電圧event、温度を監視しながら最低配信を継続する。
- 負荷限界の測量が必要な場合は、電源種の横滑り比較より、USBカメラ2→1→0台の負荷段階と5V rail実測を優先する。
- 専用電源、PoE HAT、battery HATを入手した時点で、電力経路変更を別世代のA/Bとして検証する。

## [UNKNOWN]

- 元レポートが未commit、別媒体、削除済みのいずれか
- GaN 140Wアダプタの型番と提示PDO
- 使用ケーブルのe-marker、定格、抵抗
- 5V/3AがPD analyzerによる実測か、OS警告または製品仕様からの判定か
- Pi本体とUSBカメラ群それぞれの電流配分

## [INNER]

140Wの看板を5Vの細道へ押し込んでも、ロマン砲は140Wを食べない。供給側の豪腕より、受電側の口と道幅が支配する。

3Aで凌ぐのはUSB-C信仰ではない。財布ヒーラーが来るまで火を消さず、次にPoEかbatteryか専用5Vへ逃がすための仮設足場である。

## Provenance

- 過去実験と工学判断: fusamofu / Mitsuru Saitō
- repositoryおよび全Git履歴の欠落確認、再構成記録: OpenAI Codex
