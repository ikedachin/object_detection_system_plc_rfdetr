# 🚧 **under construction** 👷‍♀️
# RF-DETRシステム
rfdetr社のRF-DETRを**誰でも、簡単に**使えることを目的としたwebアプリです
RF-DETRに関してはrfdetr社のライセンスに準じます。

![RF-DETRシステム画面](./assets/images/image.png)


## 概要

このプロジェクトは、Webカメラを使用して物体検出を行います。
たとえば部屋の中の写真を定期的に撮影し、人やペット、お皿などにアノテーションを施し、学習することで機械学習（RF-DETR）を用いてアイテムを推論（検出）するシステムです。

## 主な機能
- **自動画像キャプチャ**: 設定された時間間隔で自動的に画像をキャプチャして保存
- **手動スナップショット**: ユーザーが必要なときに手動でスナップショットを撮影
- **画像の切り取り**：学習データの写真を大きめの画像サイズで撮影し、切り取る位置を決めて全データに適用することができます。
- **学習**：学習時のパラメータを簡単にセットすることができます。詳しくはrfdetr社のHPを見てください。
- **アイテム推論（検出）**: RF-DETRモデルを使用した箱内のアイテム推論（検出）
- **PLC連携トリガー**: オムロンPLC（CJ2H）のメモリビットを監視し、ON検知時にチェッカーアプリのスナップショット処理を実行


## システム構成

### バックエンド

- **Django**: ウェブアプリケーションフレームワーク
- **Channels/Daphne**: WebSocketサポート用
- **OpenCV**: カメラ制御と画像処理
- **Roboflow RF-DETR**: 物体検出と分類
- **pyfins**: オムロンPLCとのFINS/UDP通信

### フロントエンド

- **HTML/CSS/JavaScript**: ユーザーインターフェース
- **WebSocket**: リアルタイムデータ通信


## フォルダ構成
```
object_detection_system/
├── detect/ # 推論結果保存先（日付フォルダと時間フォルダの中に結果が格納されます）
│   ├── 20250724/
│   │   ├── 22_30_18/
│   │   │   └── predict/
│   │   ├── 22_30_22/
│   │   │   └── predict/
│   │   └── ...
├── projects/ # プロジェクト別にフォルダを分けます。画像自動キャプチャ時にプロジェクト名が決まります。
│   ├── project_20250724_222419/
│   │   ├── annotated/ # 学習用データ
│   │   │   └── data_collection/
│   │   ├── cropped/ # 切り取りデータ
│   │   ├── data_collection/ # 自動収集されたデータ
│   │   │   ├── snap_2025-07-24_22-24-25.jpg
│   │   │   └── ...
│   │   ├── models/ # 学習後に出力されるモデルや学習結果
│   │   │   └── ...
│   │   └── thumbnail/ webアプリ表示用サムネイル
│   │       └── ...
├── settings/ # 残骸かも・・・
│   ├── rfdetr_detect.yaml
│   └── plc_settings.yaml # PLC接続・監視ビット設定
├── object_detection_system/ # Djangoのファイル
│   ├── annotator/ # アノテーションを行うアプリ
│   │   └── ...
│   ├── checker/ # 推論を行うアプリ
│   │   └── ...
│   ├── configuration/ # 設定・プロジェクト管理を行うアプリ
│   │   └── ...
│   ├── crop_app/ # 画像切り取り位置を決定し、切り取るアプリ
│   │   └── ...
│   ├── get_imgs/ # 学習用データとなる画像を収集するアプリ
│   │   └── ...
│   ├── training/ # 学習を実行するアプリ
│   │   └── ...
│   ├── object_detection_system/
│   │   ├── __init__.py
│   │   ├── asgi.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── ...
│   ├── (db.sqlite3) # データベース
│   ├── manage.py
│   └── (Roboflow/rf-detr-large) # RF-DETRのウエイト
├── design_docs/ # 設計書を入れておく予定（作成中）
│   ├── project_folder_construction.md
│   └── ...
├── pyproject.toml
├── README.md
├── start.sh # ワンタッチ実行用のシェルスクリプト（作成中）
├── TASK_FOLDER_STRUCTURE.md
├── uv.lock
```



## Djangoアプリケーションの機能詳細


`object_detection_system` ディレクトリ配下には、以下の主要なDjangoアプリケーションモジュールがあります：

### 1. チェッカーアプリ (`checker`)
出荷用の箱内アイテムを推論（検出）するアプリです。
- キャプチャ画像内のアイテム推論（RF-DETR推論）
- 推論結果のビジュアル表示
- 推論インターフェース（Web UI）
- 共有カメラリソースによる効率的な画像処理
- 結果の保存・履歴管理
- PLC監視スクリプトによる外部設備スイッチからの検査トリガー

### 2. 画像取得アプリ (`get_imgs`)
カメラからの画像取得・保存・配信を担当するアプリです。
- WebSocketによるリアルタイムカメラフィード配信
- 自動画像キャプチャ（インターバル撮影）
- 手動スナップショット取得
- 画像保存・管理（自動/手動）
- マルチスレッドによるカメラ制御


### 3. 設定アプリ (`configuration`)
システム全体の設定管理を提供するアプリです。
- 設定ファイル（YAML等）の管理・編集
- システム全体のパラメータ管理

### 4. 画像切り抜きアプリ (`crop`)
画像の切り抜き・前処理専用のアプリです。
- インタラクティブな画像切り抜きUI
- バッチ切り抜き・YAML出力
- EXIF対応・セキュリティ対策
- 切り抜き座標の一括管理・ダウンロード

### 5. 学習管理アプリ (`training`) ※作成中
RF-DETRモデルの学習・管理を行うアプリです（開発中）。
- 学習ジョブの管理・実行
- 学習状況の可視化・履歴管理
- モデルファイルの管理

### 6. 推論アプリ (`checker`)
学習したモデルを用いる

### 7. その他・共通モジュール
（必要に応じて追加されることがあります）
- 共通ユーティリティ、ミドルウェア、管理用コマンド等

### 4. メイン設定・ルーティング (`object_detection_system`)
Djangoプロジェクト本体の設定・ルーティング・ASGI/WGIエントリポイントを管理します。
- プロジェクト全体の設定（settings.py）
- URLルーティング（urls.py）
- ASGI/WGIサーバー起動用ファイル

### 5. その他・共通モジュール
（必要に応じて追加されることがあります）

## セットアップと実行方法

### 作成環境

- Python 3.11（他バージョンは未確認）
おそらく多くのpythonのバージョンで動くはず
- 必要なパッケージ:
  - channels >= 4.2.2
  - daphne >= 4.2.0
  - django >= 5.2.2
  - fastapi >= 0.115.0 (ダミーPLCサーバー用)
  - ipykernel >= 6.29.5 (Jupyter Notebook用)
  - opencv-python >= 4.11.0.86
  - pip >= 25.1.1
  - pyyaml >= 6.0.2
  - rfdetr >= 8.3.158
  - uvicorn >= 0.30.0 (ダミーPLCサーバー用)
  あまりバージョンを気にしなくていいかもしれない

### インストール
1. リポジトリをクローンする
2. 依存関係をインストール
   - uvを使う場合
      ```bash
      uv sync
      ```
   - venvを使う場合
      ```bash
      python -m venv .venv
      # macOS/Linux: source .venv/bin/activate
      # Windows: .venv\Scripts\activate
      pip install -r requirements.txt
      ```

### データベース構築
   - uvを使う場合
      ```bash
      cd object_detection_system
      uv run python manage.py makemigrations
      uv run python manage.py migrate
      ```
   - venvを使う場合
      ```bash
      # 先に仮想環境を有効化
      cd object_detection_system
      python manage.py makemigrations
      python manage.py migrate
      ```


### 実行

Djangoサーバーを起動:
   - uvを使う場合
      ```bash
      cd object_detection_system
      uv run python manage.py runserver
      ```

   - venvを使う場合
      ```bash
      # 先に仮想環境を有効化
      cd object_detection_system
      python manage.py runserver
      ```

   - DjangoサーバーとPLC監視をまとめて起動する場合
      ```bash
      # macOS/Linux
      python3 start.py

      # Windows
      py start.py
      ```
      macOS/Linuxでは `./start.sh`、Windowsでは `object_detection_system.bat` からも同じ `start.py` を起動できます。

### PLC監視スクリプト

チェッカーアプリでは、Web画面の `snapButton` と同じバックエンド処理をPLCのメモリビットから起動できます。

PLC接続情報と監視ビットは `settings/plc_settings.yaml` で設定します。

```yaml
plc:
  enabled: false

test_server:
  enabled: true
  host: "127.0.0.1"
  port: 8010
  base_url: "http://127.0.0.1:8010"

connection:
  host: "192.168.250.1"
  port: 9600
  plc_node: 1
  pc_node: 25
  timeout: 3.0

monitor:
  area: "D"
  word_address: 100
  bit: 0
  poll_interval_seconds: 1.0

result_signal:
  complete:
    area: "D"
    word_address: 200
    bit: 0
    on_value: 1
    reset_value: 0
  ok:
    area: "D"
    word_address: 200
    bit: 1
    ok_value: 1
    ng_value: 0
    reset_value: 0
  error:
    area: "D"
    word_address: 200
    bit: 2
    on_value: 1
    reset_value: 0
  reset_by_equipment: true

behavior:
  reset_value: 0
```

- `plc.enabled` はPLC通信のON/OFFです。PLCなしで画面やDjango側をテストする場合は `false`、実機PLCへ接続する場合は `true` にします。
- `test_server.enabled` はFastAPI製のダミーPLCサーバーを使うかどうかの設定です。`plc.enabled: false` かつ `test_server.enabled: true` の場合、PLC監視スクリプトと `PLC結果リセット` は実PLCではなく `test_server.base_url` へHTTPでアクセスします。
- `plc.enabled: false` かつ `test_server.enabled: false` の場合、PLC監視スクリプトはPLCへ接続せず終了します。画面右上の `PLC結果リセット` もPLC書き込みをスキップして成功扱いにします。
- 実PLCへ接続する場合は、使用するFINSライブラリを別途導入してください。`pyfins` はPyPIに通常パッケージとして公開されていないため、GitHub配布版など実環境で使う実装に合わせて導入し、`checker/applications/plc_monitor.py` の `PlcClient` adapterを最終確認してください。
- GitHub版 `pyfins` を導入する補助スクリプトとして、macOS/Linux用の `install_pyfins.sh` とWindows用の `install_pyfins.bat` を用意しています。
- `monitor` は現場スイッチONで立つ監視対象ビットです。上記例では `D100.00` を監視します。
- `result_signal.complete` は次トリガー許可ビットです。初期状態とNG/処理エラー時にON、判定実行中とOK時にOFFになります。
- `result_signal.ok` はOK通知ビットです。判定OK時にONになります。設備側はこのONを確認して設備を動かした後、初期状態へ戻してください。
- `result_signal.error` はNGまたは処理エラー通知ビットです。判定NG、カメラ取得、モデル、推論などで判定処理自体が失敗した場合にONになります。
- 初期状態は `trigger=OFF`、`complete=ON`、`ok=OFF`、`error=OFF` です。`trigger=OFF` かつ `complete=ON` のときだけ新しいトリガーを受け付けます。
- `trigger` を検知した直後に、二重起動防止のため `trigger`、`complete`、`ok`、`error` をすべてOFFにしてからsnap/推論処理を実行します。
- 判定OK時は `ok=ON`、`complete=OFF`、`error=OFF` にします。設備側がOKを確認して設備を動かした後、初期状態へ戻す前提です。
- 判定NG時は `error=ON`、`complete=ON`、`ok=OFF` にします。この状態では次の `trigger` を受け付けられます。
- 判定処理中はPLCポーリングを停止します。Web画面の `snapButton` とPLC監視が同時に判定処理を走らせないよう、共通ロックで排他制御しています。
- PLC監視スクリプトはOSの一時ディレクトリ上の `object_detection_system_plc_monitor.lock` で二重起動を防止します。2つ目のプロセスは起動時に終了します。
- 画面右上の `PLC結果リセット` ボタンで、`trigger=OFF`、`complete=ON`、`ok=OFF`、`error=OFF` の初期状態に戻します。このボタンは検査開始ボタンから離した場所に配置しています。

Djangoサーバーを起動すると、PLC監視も同じプロセス内のバックグラウンドスレッドで起動します。

```bash
cd object_detection_system
python manage.py runserver
```

PLC監視だけを単独で確認する場合:

```bash
source .venv/bin/activate
cd object_detection_system
python manage.py run_plc_monitor
```

uvを使う場合:

```bash
cd object_detection_system
uv run python manage.py run_plc_monitor
```

実PLC用のGitHub版 `pyfins` をインストール:

```bash
chmod +x install_pyfins.sh
./install_pyfins.sh
```

Windowsの場合:

```bat
install_pyfins.bat
```

#### ダミーPLCサーバー

PLCなしで通信関係を確認する場合は、`settings/plc_settings.yaml` を以下のようにします。

```yaml
plc:
  enabled: false

test_server:
  enabled: true
  host: "127.0.0.1"
  port: 8010
  base_url: "http://127.0.0.1:8010"
```

FastAPIのダミーPLCサーバーを起動:

```bash
source .venv/bin/activate
python plc_test_server.py
```

uvを使う場合:

```bash
uv run python plc_test_server.py
```

ブラウザで以下にアクセスすると、簡易画面から `D100.00` のトリガーON、結果ビットの確認、結果リセット、全ビットOFFができます。

```text
http://127.0.0.1:8010/
```

この状態で別ターミナルからPLC監視コマンドを起動すると、監視コマンドはFastAPIサーバーのビット状態をPLCメモリとして扱います。

### Webアプリへのアクセス
   - サーバー起動後、ブラウザで次のURLにアクセスしてください：
      ```
      http://localhost:8000
      ```
### License
MITライセンスとして公開します。
ただし、本プログラム内で利用しているRoboflow RF-DETRはAGPLv3ライセンスです。RF-DETRの使用に関しては、Roboflow社のライセンス条件に従ってください。
