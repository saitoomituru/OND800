# OND800液晶割れ後・電力測量メモ

状態: `[ACTIVE]` `[Layer A]` `[LIMITED]` `[NDI-RECOVERED]` `[HAT-FAULT-ISOLATED]` `[POWER-UNSTABLE]` `[WIFI-PROFILE-MISSING]`
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

過去実験の再構成: 操作者報告ではGaN 140W USB PDアダプタも検証済みだが、受電側は5V modeに留まり、高電圧PD modeの能力を利用できなかった。現在は5V/3Aで凌ぐ縮退運用である。元実験日時、PDO列、実電圧・電流の生logはrepositoryから欠落しているため、詳細は`2026-07-20_pi5-power-delivery-constraint-reconstruction.md`へ`[SOURCE-GAP]`付きで保存した。

判別更新: 汎用高W PDアダプタの追加交換は主実験にしない。現行5V/3A envelopeでカメラ0／1／2台の負荷段階とDC 5V railを測る。根本変更はPi 5向け専用5V高電流電源、PoE HAT、battery HAT等の部材入手後に別世代比較とする。

### E3: 破損HyperPixelからのリーク電流または部分短絡

物理破損した表示器がDPI/GPIOまたは電源railへ負荷を掛けている可能性。現時点では未測定。

判別: 必ず電源OFF後にHyperPixelを完全に外し、同じ電源・同じPi・最小USB構成で再bootする。低電圧logと消費電流を接続時／非接続時で比較する。活線でDPI/GPIOを抜き差ししない。

工学判定更新: 物理破損を目視できるHyperPixel HATアッシーをパージした後、母機は2カメラNDI全負荷で復旧した。交換可能モジュール単位の故障隔離としてHyperPixel HATアッシーを黒と判定する。一方、後続観測で低電圧が再発したため、電源状態の正常化をHATパージだけへ帰属させない。漏れ電流または部分短絡という内部故障モードの直接測定も未実施である。

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

## [FACT] 液晶パージ後の比較結果

観測時刻: 2026-07-20 20:03 JST前後

boot ID: `a522bbe4-38fe-449f-91e5-69286211aa59`

構成: 破損HyperPixelを物理的に取り外し、C922、EMEET C960、Ethernetを接続

- ユーザーが破損液晶を物理パージした後、NDI sourceが再び上がったことを受信側で確認した。
- 途中のログ収集失敗は物理USB抜けによるものとユーザーから報告された。再接続後、`192.168.0.13`へのSSHは復活した。抜けたUSB機器の個別同定は本ログでは行っていない。
- `ond800-streamer.service`はactive/enabledで、2台のカメラを起動時に検出した。
- EMEET C960とC922はいずれもMJPG 1920x1080@30fpsでNDI送信を開始した。
- 両streamは各3000 frames時点で`drops=0`、`connections=1`だった。
- Ethernetは観測時点でTX 2,901,443,398 bytes、1,931,459 packets、errors 0、dropped 0、carrier errors 0だった。
- streamer processは約200% CPUを使用し、Pi全体では約42.5% idleを残していた。
- メモリ使用量は約437MiB／7.9GiB、swap使用量は0だった。
- 温度は初回56.5°C、安定スナップショットで59.3°Cだった。
- `vcgencmd get_throttled`は2回とも`0x0`だった。
- 今回bootのkernel journalにundervoltage、voltage normalised、throttle記録はなかった。
- 物理液晶を外した後もDevice Tree overlay由来の`/dev/fb0`は存在し、streamerは`HyperPixel display detected`としてdisplay compositor branchを実行していた。
- Wi-Fiは引き続きdisconnectedで、通信とNDI送信はEthernet経路だった。

### [FACT: LATER OBSERVATION] 20:45までの追観測

- 同じboot ID、同じHATパージ状態、2カメラNDIサービス継続中に、kernelは20:06:42から20:45:03まで10回の低電圧を記録した。
- 各回は`Undervoltage detected!`から約2秒後に`Voltage normalised`へ戻った。発生間隔は約2〜8分だった。
- 20:45の`vcgencmd get_throttled`は`0x50000`で、boot中の低電圧／throttle履歴が立っていた。
- 20:47の温度は65.3°C。`ond800-streamer.service`は19:59:17からactiveを維持していた。
- Wi-Fi radio、rfkill、supplicant、SSID scanは動作したが、保存済み接続は有線とloopbackだけだった。`wlan0`はdisconnectedで、Wi-Fi profileは復活していない。
- したがって、20:03前後の`0x0`と低電圧log 0件は初期スナップショットとして正しいが、boot全体の安定性を示す長時間結果ではない。

### 比較表

| 観測 | 破損液晶接続時 | 液晶物理パージ後 |
|---|---|---|
| NDI workload | pipeline停止状態 | 1080p30×2、受信接続あり |
| low-voltage | boot中・診断中に反復 | 20:03初期観測では0件。その後20:06〜20:45に10回 |
| throttle bits | `0x50000` | 20:03は`0x0`、20:45は履歴`0x50000` |
| 温度 | 52.7°C（pipeline停止） | 56.5→59.3°C（2系統送信） |
| framebuffer | `/dev/fb0`あり | `/dev/fb0`あり（物理panelなし） |
| NDI drops | 未送信 | 3000 frames×2で0 |

## [INTERPRETATION] パージ後評価

- 破損液晶接続時はNDI pipeline停止中にも低電圧が反復した。パージ直後の短時間窓では低電圧を観測しなかったが、同じbootの後続窓では2カメラNDI全負荷中に再発した。液晶またはその接続経路の関与は否定できないが、電力不安定の主要因または解消済みとは置けない。
- 同時に再bootと物理USB再接続が入っているため、今回の比較だけで液晶リーク電流を単独原因とは確定できない。漏れ電流値も未測定である。
- 原因確定とは別に、液晶を外した構成で最低配信用NDIノードの映像送信は復旧したため、現場運用上はパージ状態を維持する根拠が得られた。ただし電源安定性は未達であり、長時間安定稼働とは呼ばない。
- `/dev/fb0`の存在は物理panel接続の証明にならない。将来のheadless判定はframebuffer nodeだけでなく、明示設定または実機probeを検討する余地がある。
- NDI映像経路は復旧したが、Wi-Fi、音声、直接RTMP／SRT、長時間耐久は今回の成功範囲に含めない。

## 工学的故障判定

判定: **HyperPixel HATアッシー不具合／物理パージで母機復旧**

- 物理破損は目視確認済みであり、破損部品を交換可能なHATモジュールとして母機から隔離した。
- パージ前はNDI pipeline停止中にも低電圧を反復した。
- パージ後は2カメラ1080p30 NDI送信と各3000 framesでdrop 0を観測した。初期観測ではthrottle bits `0x0`だったが、後続観測では低電圧が再発した。
- 以上により、運用復旧とモジュール交換判断に必要な工学的fault isolationは成立した。
- 「LCD内部のどの箇所から何mA漏れたか」「再装着すれば同じ症状が必ず再現するか」は科学的因果再現または部品解析の問いであり、本復旧の完了条件には含めない。
- 目視破損し、電源系への関与が疑われる部品を再装着すると、復旧済みPi、GPIO/DPI、電源、ストレージを再び危険へ晒す。追加知見より再故障リスクが大きいため、再装着再現試験は実施しない。
- 将来、廃棄前の部品単体解析を安全な治具・電流制限電源・母機から分離した環境で行うことは妨げない。

### 黒アッシー内部のグレー寄与マップ

HyperPixel HATアッシーは黒として隔離するが、内部原因を一つへ固定しない。

| 寄与候補 | 根拠 | 現在の扱い |
|---|---|---|
| HATの電気的追加負荷 | パージ直後は`0x0`だったが、同じパージ状態で低電圧が再発 | 関与疑い。電流値未測定、主要因とは未判定 |
| リーク電流／部分短絡 | 物理破損と電源状態変化に接続する内部mode | 関与疑い・上位候補 |
| 上流AC／5V電力経路／USB-Cケーブル | HATパージ後も周期的低電圧が継続。GaN 140W PDでも受電側は5V modeだったとの過去実験報告あり | 関与濃厚。現在の5V/3A envelope内のrail、cable、contact、load配分は未分離 |
| USBカメラ合計負荷 | NDI 2系統運転中に周期的低電圧が再発 | 関与疑い。0／1／2台比較なし |
| airflow／放熱変化 | panel除去で物理流路が変化しうる | 関与疑い。温度条件差により未判定 |
| GPIO／DPI接触、機械応力、ケーブル荷重 | 物理破損HATと接続経路を同時に除去 | 関与疑い。直接測定なし |
| display compositor software負荷 | panel除去後もdisplay branchは継続 | 復旧の主因候補として弱い |
| reboot／USB再接続 | パージと同時に変化 | 交絡候補 |

温度はパージ前52.7°C、パージ後56.5〜59.3°Cであり、数値だけなら低下していない。ただしworkloadがpipeline停止から1080p30 NDI 2系統へ変わったため、airflow寄与を比較できない。

電流値そのものは測定していない。初期窓で観測した低電圧logとthrottle状態の改善は後続窓で持続しなかった。HATパージによってカメラ処理へ電力余裕が戻った可能性はあるが、電流が減った／増えた、またはHAT電気負荷が主要因だったとは主張しない。

将来、部品不足または再利用価値が発生した場合は、母機へHAT全体を戻さず、分離治具上で寄与疑いが比較的低い部品からsalvageを検討する。回収価値より短絡・再混入・母機損傷riskが大きい場合は、黒アッシーの隔離を維持する。

### 現在の工学status

- HyperPixel HATアッシー: `故障隔離済み`
- HATの電気的追加負荷への関与: `関与疑い`
- リーク電流／部分短絡という内部mode: `関与疑い・上位候補`
- 上流AC／5V電力経路／USB-Cケーブル経路の電圧余裕不足: `関与濃厚`。GaN 140Wという総定格では解消しない受電制約を確認済みとの操作者報告あり。区間未分離
- USBカメラ合計負荷: `関与疑い`
- airflow、GPIO／DPI接触、機械応力: `関与疑い`
- software display branch: 復旧主因としては弱い
- 同型品または製造lotへの一般化: 未評価

内部故障モードを確定するfailure benchは、再発防止、部品salvage、安全責務、数値設計等の必要が生じた場合だけ別実験として起動する。現時点はassembly隔離と運用復旧で閉じる。

## 次の測量候補

1. 現在のパージ状態と5V/3A縮退運用を維持し、カメラ2→1→0台で最低配信負荷と低電圧event率を測る。
2. 可能ならGaN 140W過去実験のアダプタ／USB-Cケーブル情報、提示PDO、DC側電圧・電流を回収する。追加の汎用高W PD電源交換は主探索にしない。
3. 破損液晶の母機への再接続試験は行わない。工学的fault isolationは完了しており、復旧済み母機を再び危険へ晒さない。
4. `fb0`が残るheadless状態で不要なdisplay compositor負荷を止める明示設定を、別の実装候補として評価する。
5. 投げ銭またはジャンク箱から専用5V高電流電源、PoE HAT、battery HATを得た場合、USB-C 5V/3A縮退系とは別世代の電力経路として比較する。

## [INNER] 内観メモ

ここでは「停電しない前提」が都会の輸入定規になる。
夕立で落ち、雪で数日来ない電気の上に、常時接続前提の配信機材をそのまま置けば負ける。

ロマン砲を新品の完成兵器へ戻すより、電源が細っても表示器が割れても、一眼と一本のLANで撃てるガムテ砲へ縮退できる方が現場では強い。
電力不足を恥として隠すのではなく、どの負荷まで飛べるかを測量図にする。

待っていても財布ヒーラーもジャンク箱ヒーラーも自然には来ない。
割れた液晶を抱えたまま援軍待ちで停止することは、resource-gatedな枝の保存ではなく、現在撃てる枝まで閉じることになる。
測って、表示器が電力を吸っているならパージする。コックピットの象徴を一度外してでも、映像を外へ返す方を選ぶ。

## [MARKETING-CANDIDATE] マーケ砲候補

> 夕立でグリッドが落ちる。大雪なら数日、電気が来ない。  
> その古民家で、液晶の割れたロマン砲を最低配信用ガムテ砲へ戻す。  
> OND800の耐障害設計は、停電を例外扱いしないところから始まる。

液晶パージ編:

> 待っていても財布ヒーラーは来ない。ジャンク箱ヒーラーも来ない。
> ならば測る。割れた液晶が残りの電力を吸っているなら、天岩戸ごとパージする。
> 豪華なコックピットを失っても、カメラ一眼とLAN一本のガムテ砲で配信へ戻る。

このコピーは現場報告と現在の実験目的を接続した候補であり、電源耐性の実証完了を意味しない。
物理的な液晶パージは実施済み。工学的にはHyperPixel HATアッシー黒、母機復旧として確定した。

パージ後の実測版:

> 液晶を外した。2台のカメラが1080p30で戻った。
> 3000フレームずつ、drop 0。映像は戻ったが、低電圧という別の敵は残った。
> ロマン砲の画面は失ったが、最低配信用ガムテ砲は撃てる。

この表現の射程は、2026-07-20の実機、Ethernet、NDI 2系統、観測したフレーム範囲に限定する。

## 停止条件

- 発熱、焦げ臭、変色、コネクタ溶損、連続低電圧、USB切断反復があれば負荷試験を止める。
- HyperPixelおよびGPIO/DPI接続は必ず電源OFFで変更する。
- 低電圧状態で2カメラNDI長時間試験へ進まない。
- Wi-Fi接続情報、配信キー、秘密鍵は測量ログへ残さない。

## Provenance

- 現場電力履歴、物理作業、resource condition: fusamofu / Mitsuru Saitō
- Piログ採取、仮説分離、比較測量設計: OpenAI Codex
- 関連ログ: `2026-06-26_hyperpixel-breakage-season3-pause.md`、`2026-07-20_post-hyperpixel-ama-no-iwato-recovery.md`
