# checkerアプリケーション プログラム設計書

## 1. システム概要

本アプリは、RF-DETRモデルを用いた物体検出推論・検証を行うDjangoアプリケーションです。  
プロジェクトごとに学習済みモデル・設定ファイルを選択し、画像推論・結果判定・可視化をサポートします。

---

## 2. 全体フロー図

```
[プロジェクト選択]
      ↓
[設定ファイル・重み選択]
      ↓
[推論画像アップロード/選択]
      ↓
[RF-DETR推論]
      ↓
[判定・可視化]
      ↓
[結果表示・保存]
```

---

## 3. 主要関数・API詳細

### 3.1 ビュー・API

- **checker_index(request)**  
  プロジェクト・設定ファイル・重みファイルの選択画面を表示。モデルロードも担当。
- **get_config_files(request)**  
  プロジェクトIDからmodels配下の設定ファイル（yaml）一覧を返すAPI。
- **get_weight_path(request)**  
  プロジェクトID・設定ファイル名から重みファイルパスと存在判定を返すAPI。

### 3.2 推論ロジック

- **detect_objects(img, model, **kwargs)**  
  画像とモデルを受けてRF-DETR推論を実行。結果画像を保存し、判定ロジックへ渡す。
- **result_detector(result)**  
  RF-DETR推論結果からクラスごとの個数を集計し、判定基準に従い合否・詳細を返却。

### 3.3 WebSocket（リアルタイム機能）

- **CheckerServerTime(AsyncWebsocketConsumer)**  
  サーバ時刻の配信。
- **Confirm(AsyncWebsocketConsumer)**  
  推論結果のリアルタイム通知等。

---

## 4. 各関数の詳細説明

### checker_index(request)
- **目的**: 推論用プロジェクト・設定・重み選択画面の表示
- **処理**:
  1. プロジェクト一覧・アクティブプロジェクト取得
  2. 設定ファイル・重みファイルの存在確認
  3. RF-DETRモデルのロード
  4. テンプレートへデータ渡し
- **返却**: HTML

### get_config_files(request)
- **目的**: 設定ファイル一覧取得API
- **処理**:
  1. プロジェクトIDからmodels配下を再帰検索
  2. yamlファイル一覧を返却
- **返却**: JSON

### get_weight_path(request)
- **目的**: 重みファイルパス・存在判定API
- **処理**:
  1. プロジェクトID・設定ファイル名から重みパス生成
  2. ファイル存在確認・モデルロード
- **返却**: JSON

### detect_objects(img, model, **kwargs)
- **目的**: RF-DETR推論実行
- **処理**:
  1. 推論用保存ディレクトリ生成
  2. RF-DETRモデルで推論
  3. 結果画像保存
  4. 判定ロジックへ渡す
- **返却**: 判定結果（result_detectorの返り値）

### result_detector(result)
- **目的**: 推論結果の合否判定
- **処理**:
  1. クラスごとの個数集計
  2. 判定基準（例: s=8個, 他=9個）で合否判定
- **返却**: (合否, クラス名, 個数, 結果画像)

---

## 5. クラス図（簡易）

```
Project
  ↑
checker_index, get_config_files, get_weight_path
  ↓
detect_objects
  ↓
result_detector
```

---

## 6. 注意事項・設計上のポイント

- プロジェクトごとに重み・設定ファイルを分離管理
- RF-DETRモデルの動的ロードに対応
- 推論結果は合否判定・画像保存・可視化まで一貫
- WebSocketによるリアルタイム通知も実装

---

（本設計書は2025年7月25日現在の実装に基づく）
