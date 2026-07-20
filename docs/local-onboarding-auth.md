# OND800 ローカルonboarding・認証設計

状態: `[DESIGN]` `[PARTIALLY-IMPLEMENTED]` `[LOCAL-FIRST]`

## 目的

OND800は、NAT越えのcloud serverではなく、操作者のLAN内で動くedge IoT／配信nodeである。
初回起動、現場復旧、headless接続を、長いpassword、cloud account、外部認証providerなしで成立させる。

同時に、LANへ侵入済みの別機器、誤ったport forwarding、持ち出し先networkを無視しない。
NATの存在だけをsecurity boundaryとせず、公開interface、device state、試行制限を実装上の拘束にする。

## 現在の実装

| 項目 | 現在値 |
|---|---|
| Linux user | `ond` |
| 初期SSH password | `ond` |
| discovery | `pi5-ond.local`（Bonjour） |
| 想定network | 操作者管理下のlocal LAN |
| password変更GUI | `NOT_IMPLEMENTED` |
| operator PIN | `NOT_IMPLEMENTED` |
| claim state machine | `NOT_IMPLEMENTED` |

`ond/ond`は、本projectでは公開可能なbootstrap credentialとして扱う。Wi-Fi PSK、配信key、秘密鍵等のlocal secretとは分類を分ける。

## 認証面を一枚にしない

### 1. bootstrap SSH

初回起動または現場復旧で、`ond/ond`を使い、物理LANまたは明示的に参加させたlocal Wi-Fiから接続する。

- cloud relay、UPnPによる自動port開放、製品側からのNAT traversalを行わない
- GUIには`初期認証で運転中`を常時表示する
- GUIからpassword変更またはSSH key登録を一操作で開始できるようにする
- 認証変更に失敗してもlocal recovery pathを失わない

### 2. operator PIN

日常のコックピット操作は、長いserver passwordではなく4桁または6桁PINを候補とする。

- 推奨defaultは6桁
- 4桁は物理近接、短時間session、または低権限操作に限定する
- 連続失敗には待ち時間を入れ、remote brute forceを無制限に通さない
- PINは配信操作・profile選択等のoperator interfaceに用い、Linux SSH passwordとして自動流用しない
- PIN変更、忘却、local resetをGUIと物理recoveryの両方から扱えるようにする

### 3. owner／maintenance SSH

claim後もSSHを使う場合は、次から操作者が選べるようにする。

- SSH public key
- ownerが設定したpassword
- 明示的にbootstrap passwordを維持するLAB／RECOVERY profile

長いpasswordまたはkeyを全利用者へ強制しない。ただし、短いoperator PINとOS管理権限を暗黙に同一化しない。

## device state

```text
FACTORY / UNCLAIMED
  - local bootstrap available
  - GUI shows initial-auth banner
  - owner can claim without cloud account

CLAIMED
  - operator PIN available
  - SSH credential policy chosen by owner
  - current exposure and auth state visible in GUI

LOCAL RECOVERY
  - entered by an explicit local/physical action
  - returns a bounded route to bootstrap or credential reset
  - does not enable WAN publication or cloud control
```

状態遷移は将来実装であり、現時点の実機には存在しない。

## deployment profile

| profile | bootstrap | 想定 |
|---|---|---|
| `LAB` | 公開共通`ond/ond`を許容 | ZeroRoomLab内、実験、単機運用 |
| `RECOVERY` | local／physical actionで復旧口を開く | headless障害復旧 |
| `DISTRIBUTION` | 個体別またはuser-defined credential | 市販、第三者配布、法域要件あり |

ETSI EN 303 645は、factory default以外のconsumer IoT passwordを個体別またはuser-definedとする。英国PSTI関連規則は、consumer connectable productのuniversal default／容易に推測できるpasswordを禁止対象にする。したがって`ond/ond`をLAB／現場復旧設計として公開することと、第三者向け製品profileへ同じ固定値を恒久搭載することは分ける。

これは現行LAB機をGIP server基準へ寄せるための規定ではない。将来、販売・配布する時点でprofileを切り替えられる設計境界である。

## 実装時の最低試験

- WAN側からSSH／GUIへ到達しないこと
- UPnP／NAT traversalを自動で有効化しないこと
- `UNCLAIMED`／`CLAIMED`／`RECOVERY`がGUIで誤認なく見えること
- PIN試行制限と解除条件
- credential変更後のSSH再接続
- credential変更失敗時のlocal recovery
- Ethernet／Wi-Fi fallback切替後も、認証状態が勝手にfactory defaultへ戻らないこと
- low-voltage、突然の停電、filesystem recovery後もclaim情報が消失または巻き戻らないこと

## 参照

- [NISTIR 8259 Series](https://www.nist.gov/itl/applied-cybersecurity/nist-cybersecurity-iot-program/nistir-8259-series)
- [NIST IoT Logical Access to Interfaces](https://pages.nist.gov/IoT-Device-Cybersecurity-Requirement-Catalogs/technical/logical/)
- [ETSI EN 303 645 V3.1.2](https://www.etsi.org/deliver/etsi_en/303600_303699/303645/03.01.02_20/en_303645v030102a.pdf)
- [英国 consumer connectable product security規則](https://www.gov.uk/guidance/regulations-consumer-connectable-product-security)

