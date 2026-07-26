# 員数チェックシステム セットアップマニュアル（生産設備メンテナー向け）

対象：RF-DETR員数チェックシステム（object_detection_system_plc_rfdetr）
対象読者：生産設備メンテナー（プログラミング知識は不要です）
対象OS：Windows 10 / 11

このマニュアルの手順どおりに進めれば、リポジトリの中身を読まなくてもセットアップが完了します。
コマンドは枠内の文字をそのままコピーして貼り付けてください。

---

## 1. システム概要

Webカメラで出荷箱を撮影し、AI（RF-DETR）が箱内の部品を検出して員数（個数）をチェックするシステムです。
検査のトリガーは次の2通りです。

| トリガー | 用途 |
|---|---|
| Web画面のボタン | 手動検査・動作確認 |
| PLC（オムロンCJ2H）のビットON | 設備連動の自動検査 |

構成機器：Windows PC、USBカメラ、オムロンPLC（CJ2H）、LANケーブル（PLC連携時）

---

## 2. 事前準備（必要なもの）

- [ ] Windows PC（メモリ16GB以上推奨。学習も行うためGPU搭載を推奨）
- [ ] USBカメラ（PCに接続しておく）
- [ ] このリポジトリ一式（USBメモリ等で受け取ったフォルダ、またはZIP）
- [ ] インターネット接続（初回セットアップ時のみ必要）
- [ ] PLC連携する場合：PLCのIPアドレス、使用するビット番号（→ 7章）

---

## 3. Pythonのインストール

本システムは Python 3.11 で動作します。

1. ブラウザで https://www.python.org/downloads/ を開く
2. 「Python 3.11.x」のWindowsインストーラーをダウンロード
3. インストーラーを起動し、**必ず「Add python.exe to PATH」にチェック**を入れてから「Install Now」をクリック
4. 完了後、確認のため「コマンドプロンプト」を開き（スタートメニューで `cmd` と検索）、以下を入力してEnter

```bat
py --version
```

`Python 3.11.x` と表示されればOKです。

---

## 4. システム一式の配置

1. リポジトリのフォルダ（`object_detection_system_plc_rfdetr`）を `C:\` 直下など、**日本語・スペースを含まないパス**に置きます
   - 例：`C:\object_detection_system_plc_rfdetr`
2. ZIPで受け取った場合は右クリック →「すべて展開」で解凍してから移動します

以降、この場所を「システムフォルダ」と呼びます。

---

## 5. 初回セットアップ（1回だけ実施）

### 5-1. コマンドプロンプトでシステムフォルダを開く

```bat
cd C:\object_detection_system_plc_rfdetr
```

### 5-2. 仮想環境の作成（専用のPython環境を作ります）

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate
```

行の先頭に `(.venv)` と表示されれば成功です。

### 5-3. 必要なソフトウェア部品のインストール

```bat
pip install -r requirements.txt
```

※ 数GBのダウンロードが発生します。10〜30分程度かかることがあります。
※ エラーで止まった場合はネット接続を確認し、同じコマンドをもう一度実行してください。

### 5-4. データベースの作成

```bat
cd object_detection_system
python manage.py makemigrations
python manage.py migrate
cd ..
```

`OK` が並んで表示されれば成功です。

---

## 6. 起動と動作確認

### 6-1. 起動

システムフォルダ内の **`object_detection_system.bat` をダブルクリック**します。
（Djangoサーバー起動 → 自動でブラウザが開きます）

ブラウザが開かない場合は、手動で以下のURLを開いてください。

```text
http://127.0.0.1:8000/
```

### 6-2. カメラの確認

1. トップページから「データ収集」画面を開く
2. カメラ映像が表示されることを確認する
3. 映らない場合 → カメラのUSB接続を確認し、他のアプリ（Teams等）がカメラを使っていないか確認

### 6-3. 停止

起動時に開いた黒い画面（コマンドプロンプト）で `Ctrl + C` を押すか、画面を閉じます。

### 6-4. デスクトップにショートカットを作る（推奨）

`object_detection_system.bat` を右クリック →「送る」→「デスクトップ（ショートカットを作成）」。
以降、作業者はこのアイコンをダブルクリックするだけで起動できます。

---

## 7. PLC連携のセットアップ（オムロンCJ2H）

### 7-1. 設定ファイル

PLC設定はすべて `settings\plc_settings.yaml` に書かれています。メモ帳で開いて編集できます。

```yaml
plc:
  enabled: false        # 実PLCに接続するか（true/false）

test_server:
  enabled: true         # ダミーPLC（テスト用）を使うか
  host: "127.0.0.1"
  port: 8010
  base_url: "http://127.0.0.1:8010"

connection:
  host: "192.168.250.1" # PLCのIPアドレス（現場に合わせて変更）
  port: 9600
  plc_node: 1           # PLCのノード番号
  pc_node: 25           # PCのノード番号
  timeout: 3.0

monitor:                # 検査開始トリガー（設備スイッチでONするビット）
  area: "W"
  word_address: 100
  bit: 0                # → W100.00 を監視
  poll_interval_seconds: 1.0

result_signal:          # 判定結果をPLCへ返すビット
  complete:             # 次トリガー許可（W200.00）
    area: "W"
    word_address: 200
    bit: 0
  ok:                   # 判定OK通知（W200.01）
    area: "W"
    word_address: 200
    bit: 1
  error:                # NG/エラー通知（W200.02）
    area: "W"
    word_address: 200
    bit: 2
```

※ 実ファイルにはこのほか `checker_api` などの項目がありますが、変更不要です。上記以外はそのままにしてください。

### 7-2. 動作モード早見表

| plc.enabled | test_server.enabled | 動作 |
|---|---|---|
| false | true | **テストモード**：PLCなしでダミーPLC画面から動作確認 |
| true | false | **本番モード**：実PLCと通信 |
| true | true | **ブリッジモード**：実PLCに接続しつつ、ブラウザからPLCビットを直接操作（操作盤）。稼働中設備での誤操作に注意 |
| false | false | PLC連携なし（Web画面の手動検査のみ） |

### 7-3. ビット仕様（PLCラダー設計者向け）

| ビット | 方向 | 意味 |
|---|---|---|
| trigger（W100.00） | 設備→PC | OFF→ONの立ち上がりで検査開始 |
| complete（W200.00） | PC→設備 | ONのとき次のトリガー受付可 |
| ok（W200.01） | PC→設備 | 判定OKでON。設備側で確認後、初期状態へ戻す |
| error（W200.02） | PC→設備 | 判定NGまたは処理エラーでON |

- 初期状態：`trigger=OFF, complete=ON, ok=OFF, error=OFF`
- `trigger=OFF かつ complete=ON` のときだけ新しいトリガーを受け付けます
- トリガー検知直後、4ビットすべてOFFにしてから検査を実行します（二重起動防止）
- OK時：`ok=ON, complete=OFF`。NG/エラー時：`error=ON, complete=ON`（次トリガー受付可）
- 起動直後は一度 `trigger=OFF` を確認するまでトリガーを受け付けません（古いONの誤動作防止）

**注意事項**

- 使用エリアは**Wエリア**にしてください。DMエリアは停電後も値が残るため、古いトリガー・結果が再処理される危険があります
- PLC側の **IOM Hold（IOメモリ保持）は無効**にしてください（有効だとWエリアも保持されます）
- 通信はFINS/UDP（ポート9600）です。PCとPLCを同一ネットワークにし、ファイアウォールでUDP 9600を許可してください

### 7-4. テストモードでの動作確認（PLC実機なしで確認）

1. `settings\plc_settings.yaml` を `plc.enabled: false`、`test_server.enabled: true` にする
2. コマンドプロンプトを開き、ダミーPLCサーバーを起動

```bat
cd C:\object_detection_system_plc_rfdetr
.venv\Scripts\activate
python plc_test_server.py
```

3. 別途 `object_detection_system.bat` で本体を起動
4. ブラウザで `http://127.0.0.1:8010/` を開く（ダミーPLC操作画面）
5. ダミーPLC画面で W100.00 をONにする → 本体が撮影・推論を実行し、結果ビット（OK/エラー）が変化することを確認

### 7-5. 実PLCへの接続切り替え

1. `settings\plc_settings.yaml` の `connection.host` を現場PLCのIPアドレスに変更
2. `plc.enabled: true`、`test_server.enabled: false` に変更
3. システムを再起動（batを起動し直す）
4. 設備側スイッチで trigger ビットをONにし、検査が実行されることを確認
5. 状態がおかしくなったら、推論画面右上の「**PLC結果リセット**」ボタンで初期状態に戻せます

---

## 8. 合否判定の仕組みと基準変更（quality_verify.py）

### 8-1. 判定の仕組み

合否（OK/NG）の判定基準は、以下のプログラムに書かれています。

```text
object_detection_system\checker\applications\quality_verify.py
```

検査時の流れは次のとおりです。

1. AIが画像から部品を検出し、「クラス名（ラベル名）: 個数」の形で集計します（例：`{'s': 8}`）
2. その集計結果を `quality_verify.py` 内の判定関数に渡し、OK（True）/ NG（False）を返します
3. 現在使われている判定関数は `quality_verify` です

**現在の判定基準（quality_verify）**

| 検出結果 | 判定 |
|---|---|
| 検出されたラベル（クラス）の種類が **1種類だけ** | OK（個数は問いません） |
| 何も検出されない（0種類）、または2種類以上検出 | NG |

※ `quality_verify_common` という関数もあります。「1個でも何か検出されればOK」という動作確認用の緩い判定です。

### 8-2. 判定基準を変更する方法

例：ラベル `bolt` が8個、`nut` が4個そろっていればOK、としたい場合。

1. **変更前に必ずバックアップを取る**：`quality_verify.py` をコピーして `quality_verify_backup.py` などの名前で同じフォルダに保存
2. メモ帳等で `quality_verify.py` を開き、ファイル末尾に新しい判定関数を追加する

```python
# 新しい判定ロジック（例：boltが8個、nutが4個でOK）
def quality_verify_myproduct(result_dict):
    if result_dict.get("bolt") == 8 and result_dict.get("nut") == 4:
        return True
    else:
        return False
```

3. 呼び出し元を新しい関数名に変更する。以下のファイルを開き、

```text
object_detection_system\checker\applications\snap_service.py
```

`quality_verify.quality_verify` と書かれた行（236行目付近）を書き換えます。

```python
# 変更前
result = quality_verify.quality_verify(result_dict)
# 変更後
result = quality_verify.quality_verify_myproduct(result_dict)
```

4. 両ファイルを上書き保存する

**編集時の注意**

- Pythonは行頭の空白（インデント）で構造が決まります。**行頭の空白の数を崩さない**でください（既存の関数をコピーして書き換えるのが安全です）
- ラベル名（`bolt` 等）は、アノテーション時に登録したラベル名と完全に一致させてください（大文字・小文字も区別されます）

### 8-3. 変更した場合の対処（必ず実施）

判定基準を変更したら、以下を必ず行ってください。

1. **システムを再起動する**：黒い画面をすべて閉じて、batを起動し直す。再起動しないと変更は反映されません
2. **OK品で手動検査**：正しい員数の箱で検査し、OKになることを確認
3. **NG品で手動検査**：わざと1個抜いた箱・1個多い箱で検査し、NGになることを確認
4. **PLC連携時**：ダミーPLCまたは実機トリガーでも、OK/NGビットが正しく変化することを確認
5. 記録として、変更日・変更内容・確認結果をメモに残す

**変更後にエラーが出た・常にNGになるとき**

- 起動時や検査時にエラーになる場合は、書き間違い（インデント崩れ、コロン `:` 忘れ、括弧の閉じ忘れ）が原因のことが多いです
- 復旧できない場合は、バックアップした `quality_verify_backup.py` の内容を `quality_verify.py` に書き戻して再起動すれば元の状態に戻ります
- ラベル名の不一致（アノテーションのラベル名と判定関数内の名前が違う）も「常にNG」の典型原因です

---

## 9. 日常の起動・停止（作業者への引き継ぎ事項)

| 操作 | 方法 |
|---|---|
| 起動 | デスクトップのショートカットをダブルクリック |
| 画面 | ブラウザで http://127.0.0.1:8000/ |
| 停止 | 黒い画面で Ctrl+C、または画面を閉じる |
| PLC状態リセット | 推論画面右上の「PLC結果リセット」ボタン |

---

## 10. トラブルシューティング

| 症状 | 確認・対処 |
|---|---|
| batを実行しても起動しない | 5章のセットアップが完了しているか。コマンドプロンプトで `py --version` が表示されるか |
| ブラウザに「接続できません」 | 黒い画面が起動しているか。URLが `http://127.0.0.1:8000/` か |
| カメラ映像が出ない | USB接続、他アプリのカメラ使用、PCのカメラプライバシー設定（設定→プライバシー→カメラ） |
| PLCトリガーで検査が動かない | ①plc_settings.yamlのモード設定（7-2）②PLCのIPに `ping 192.168.250.1` が通るか ③`trigger=OFF かつ complete=ON` になっているか →「PLC結果リセット」を押す |
| 検査後、次のトリガーを受け付けない | OK後は設備側で初期状態に戻す設計です。手動復旧は「PLC結果リセット」 |
| PLC監視が二重起動と表示され終了する | すでに起動済みです。既存の画面を使うか、すべて閉じてから再起動 |
| pip installが失敗する | ネット接続・プロキシ設定を確認して再実行 |
| 判定基準を変更したら動かない・常にNG | 8-3章を参照。書き間違い・ラベル名不一致を確認し、直らなければバックアップから復旧 |
| 動作がおかしいので初期化したい | 黒い画面をすべて閉じて再起動。改善しなければPC再起動 |

---

## 11. 参考（リポジトリ内の詳細資料）

- `README.md`：システム全体・PLC仕様の詳細
- `zzz_docs/plc_monitor_flow.md`：PLC監視の内部動作
- `zzz_manuals/DETECT_CONF.md`：推論の詳細設定（`settings/rfdetr_detect.yaml`）
- `zzz_manuals/TRAINING_CONF.md`：学習の詳細設定
