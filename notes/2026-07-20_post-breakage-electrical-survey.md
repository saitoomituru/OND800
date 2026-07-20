# OND800液晶割れ後・電力測量メモ

状態: `[ACTIVE]` `[Layer A]` `[LIMITED]`  
開始日: 2026-07-20  
対象: HyperPixel 4.0破損後のOND800 Raspberry Pi 5、電源経路、USB機器、DPI表示器  
検証範囲: Piのkernel／firmwareログ、温度、throttle bits、接続デバイス、ユーザーの現場電力報告  
除外範囲: AC入力電圧、DC 5V rail、各機器電流、漏れ電流の計器測定。現時点では未測定  

## [FACT] 2026-07-20の実機観測

- `vcgencmd get_throttled`は`0x50000`を返した。現在低電圧bitは解除されているが、boot以降に低電圧とクロック制限を経験した履歴を含む。
- kernel journalには複数回の`Undervoltage detected!`と、その数秒後の`Voltage normalised`が記録されている。
- 診断中の2026-07-20 18:18と18:20にも低電圧を検出し、いずれも数秒後にnormaliseした。
- 診断時温度は52.7°C。異常高温は観測していない。
- root filesystemは57GB中11%使用で、容量逼迫は観測していない。
- `/dev/fb0`は存在し、streamerは破損後も`HyperPixel display detected`と判定する。
- C922とEMEET C960の2台がUSB／V4L2デバイスとして列挙されている。
- streamerのcamera pipelineは起動しておらず、低電圧はNDI 2系統の全負荷を掛ける前にも発生した。

## [FACT: USER-REPORTED FIELD CONDITION] 現場の電力環境

- ユーザーによると、設置場所は田舎のグリッド電力が不安定で、夕立で停電することがある。
- 冬季は大雪により、数日間電力が復旧しない場合がある。
- これは今回セッションで計器測定した系統品質ではなく、継続運用者による現場履歴である。
- OND800の電源設計では、瞬断、長時間停電、復電、低電圧を例外ではなく通常のExecution Envelopeとして扱う必要がある。

## [INTERPRETATION]

- 今回の低電圧は実測ログがあり、単なる保守的な注意ではない。
- NDI pipeline停止中にも低電圧が出たため、「2カメラNDIのCPU負荷だけ」が唯一の原因ではない。
- 上流グリッド、AC/DC電源、USB-Cケーブル、2台のUSBカメラ、破損HyperPixelの電源／信号経路は分離して測る必要がある。
- HyperPixelが`/dev/fb0`として列挙されることは、表示面、DPI回路、電源経路が健全である証明にはならない。
- 財布不足は電気的故障原因ではないが、既知の電源・筐体・交換性リスクへの防御費を制約するresource conditionである。プロジェクト失敗と同一視しない。

## [HYPOTHESIS]

### E1: 上流グリッドまたは復電時の電圧変動

夕立、積雪、地域配電条件によりAC入力が瞬断・変動し、Pi電源が5V railを維持できていない可能性。

判別: AC側のUPS／電源ログ、電力計、既知の安定電源環境との比較。今回のPiログだけでは系統原因を断定しない。

### E2: Pi用電源アダプタまたはUSB-Cケーブルの電圧降下

無負荷寄りでも断続的低電圧が出るため、アダプタ容量、ケーブル抵抗、コネクタ接触を候補にする。

判別: 既知の正常なPi 5対応電源と短いケーブルへ交換し、同一boot内の低電圧logを比較する。

### E3: 破損HyperPixelからのリーク電流または部分短絡

物理破損した表示器がDPI/GPIOまたは電源railへ負荷を掛けている可能性。現時点では未測定。

判別: 必ず電源OFF後にHyperPixelを完全に外し、同じ電源・同じPi・最小USB構成で再bootする。低電圧logと消費電流を接続時／非接続時で比較する。活線でDPI/GPIOを抜き差ししない。

### E4: USBカメラ2台と周辺機器の合計負荷

C922とC960の同時接続が5V railへ追加負荷を掛けている可能性。

判別: カメラ0台、1台、2台をboot単位で比較する。NDI pipelineを動かす前と後の両方で測る。

## 比較測量マトリクス

| 構成 | HyperPixel | USBカメラ | Network | 目的 |
|---|---:|---:|---|---|
| A 現状保存 | 接続 | 2台 | Ethernet | 現在症状のbaseline |
| B 表示器分離 | 非接続 | 1台 | Ethernet | 液晶リーク／部分短絡と最低配信構成の確認 |
| C Pi最小 | 非接続 | 0台 | Ethernet | 電源・ケーブル・Pi本体の基準値 |
| D カメラ加算 | 非接続 | 1台→2台 | Ethernet | USB負荷の段階差 |
| E NDI加算 | 非接続 | 1台 | Ethernet | capture／decode／NDI送信負荷の段階差 |

各bootで最低限次を残す。

```text
date -Is
vcgencmd get_throttled
vcgencmd measure_temp
journalctl -k -b --no-pager | grep -i -E 'under.?voltage|voltage normal|throttl'
lsusb
v4l2-ctl --list-devices
systemctl --no-pager --full status ond800-streamer
```

可能ならUSB-C inline meterまたはDC側計測器で電圧・電流を同時取得する。Piのfirmware flagだけから漏れ電流値を逆算しない。

## [UNKNOWN]

- AC入力とDC 5V railの実測値。
- 電源アダプタ型番、定格、USB-Cケーブル抵抗。
- HyperPixel接続時／非接続時の差分電流。
- カメラ0／1／2台での低電圧発生頻度。
- 停電・復電とfilesystem／systemd／NetworkManager profile消失の因果関係。

## [INNER] 内観メモ

ここでは「停電しない前提」が都会の輸入定規になる。
夕立で落ち、雪で数日来ない電気の上に、常時接続前提の配信機材をそのまま置けば負ける。

ロマン砲を新品の完成兵器へ戻すより、電源が細っても表示器が割れても、一眼と一本のLANで撃てるガムテ砲へ縮退できる方が現場では強い。
電力不足を恥として隠すのではなく、どの負荷まで飛べるかを測量図にする。

## [MARKETING-CANDIDATE] マーケ砲候補

> 夕立でグリッドが落ちる。大雪なら数日、電気が来ない。  
> その古民家で、液晶の割れたロマン砲を最低配信用ガムテ砲へ戻す。  
> OND800の耐障害設計は、停電を例外扱いしないところから始まる。

このコピーは現場報告と現在の実験目的を接続した候補であり、電源耐性の実証完了を意味しない。

## 停止条件

- 発熱、焦げ臭、変色、コネクタ溶損、連続低電圧、USB切断反復があれば負荷試験を止める。
- HyperPixelおよびGPIO/DPI接続は必ず電源OFFで変更する。
- 低電圧状態で2カメラNDI長時間試験へ進まない。
- Wi-Fi接続情報、配信キー、秘密鍵は測量ログへ残さない。

## Provenance

- 現場電力履歴、物理作業、resource condition: fusamofu / Mitsuru Saitō
- Piログ採取、仮説分離、比較測量設計: OpenAI Codex
- 関連ログ: `2026-06-26_hyperpixel-breakage-season3-pause.md`、`2026-07-20_post-hyperpixel-ama-no-iwato-recovery.md`
