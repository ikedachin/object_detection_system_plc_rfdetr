# get_imgsアプリケーション プログラム設計書

## 1. システム概要

本アプリは、物体検出用データセットの画像収集・管理を行うDjangoアプリケーションです。  
プロジェクト単位で画像収集・カメラ制御・セッション管理を行い、他アプリ（annotator等）との連携も担います。

---

## 2. 全体フロー図

```
[プロジェクト作成]
      ↓
[フォルダ構造生成]
      ↓
[アクティブ化]
      ↓
[データ収集セッション作成]
      ↓
[カメラ制御・画像取得]
      ↓
[画像保存・統計管理]
```

---

## 3. 主要関数・API詳細

### 3.1 プロジェクト・フォルダ管理

- **index(request)**  
  アクティブプロジェクト・全プロジェクト一覧画面を表示。
- **create_project_folders(request)**  
  新規プロジェクト作成API。DB登録・フォルダ構造生成・annotator連携。
- **set_active_project(request)**  
  プロジェクトをアクティブ化。annotator連携も実施。
- **get_project_stats(request)**  
  プロジェクトの画像数・統計情報を取得。

### 3.2 データ収集セッション管理

- **create_collection_session(request)**  
  データ収集セッションを作成。プロジェクト・セッション名等を登録。

### 3.3 カメラ制御・テスト

- **get_camera_availability(request)**  
  利用可能なカメラ一覧を取得。
- **test_camera_connection(request)**  
  指定カメラの接続テストを実施。

---

## 4. 各関数の詳細説明

### index(request)
- **目的**: プロジェクト一覧画面の表示
- **処理**:
  1. アクティブプロジェクト・全プロジェクト取得
  2. テンプレートへデータ渡し
- **返却**: HTML

### create_project_folders(request)
- **目的**: 新規プロジェクト作成・フォルダ生成
- **処理**:
  1. POSTデータ受信
  2. DB登録・フォルダ構造生成
  3. annotatorアプリのProjectも作成
- **返却**: JSON

### set_active_project(request)
- **目的**: プロジェクトのアクティブ化
- **処理**:
  1. POSTデータ受信
  2. DBのis_activeフラグ更新
  3. annotatorアプリのProjectもアクティブ化
- **返却**: JSON

### get_project_stats(request)
- **目的**: プロジェクトの統計情報取得
- **処理**:
  1. GETパラメータ受信
  2. 画像数・統計情報集計
- **返却**: JSON

### create_collection_session(request)
- **目的**: データ収集セッション作成
- **処理**:
  1. POSTデータ受信
  2. DataCollectionSession DB登録
- **返却**: JSON

### get_camera_availability(request)
- **目的**: 利用可能なカメラ一覧取得
- **処理**:
  1. カメラデバイスを列挙
- **返却**: JSON

### test_camera_connection(request)
- **目的**: カメラ接続テスト
- **処理**:
  1. POSTデータ受信
  2. 指定カメラでフレーム取得テスト
- **返却**: JSON

---

## 5. クラス図（簡易）

```
DataCollectionProject
  ↑
DataCollectionSession
  ↑
カメラ制御・画像保存
```

---

## 6. 注意事項・設計上のポイント

- プロジェクト・セッション・画像はDBで一元管理
- annotatorアプリとの連携を常に維持
- カメラ制御・画像保存時のエラーハンドリングを徹底
- 日本語名・特殊文字にも配慮したフォルダ生成

---

（本設計書は2025年7月25日現在の実装に基づく）
