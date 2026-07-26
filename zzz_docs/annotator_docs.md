
# annotatorアプリケーション プログラム設計書

## 1. システム概要

本アプリは、物体検出用データセットのアノテーション管理を行うDjangoアプリケーションです。  
プロジェクト単位で画像・ラベル・アノテーションを管理し、RF-DETR学習で使用するCOCOデータと補助的なYOLO形式ラベルの生成までを一貫してサポートします。

---

## 2. 全体フロー図

```
[プロジェクト選択/作成]
        ↓
[画像読込/管理] ←→ [ラベル管理]
        ↓
[アノテーション画面]
        ↓
[アノテーション保存]
        ↓
[データセット分割・YAML生成]
        ↓
[学習用データ出力]
```

---

## 3. モデル構造

- **Project**: アノテーション対象プロジェクト（画像・ラベル・設定を管理）
- **Label**: アノテーション用ラベル（プロジェクト単位で管理）
- **ImageFile**: 画像ファイル情報（ファイル名・寸法・プロジェクト紐付け）
- **Annotation**: 画像ごとのアノテーション情報（ラベル・座標）

---

## 4. 主要関数・API詳細

### 4.1 画像・プロジェクト管理

- **index(request)**  
  画像一覧ページを表示。アクティブなプロジェクトの画像・ラベル・進捗を集計。
- **project(request)**  
  プロジェクト一覧・選択画面を表示。
- **scan_projects(request)**  
  data_collectionフォルダをスキャンし、未登録のプロジェクトを自動作成。
- **set_active_project(request, project_id)**  
  指定プロジェクトをアクティブ化。cropped画像の有無も返却。
- **load_project_images(request, project_id)**  
  プロジェクト内の画像をDBに登録。cropped/originalの選択可。

### 4.2 アノテーション画面・操作

- **annotate(request, image_id, cropped)**  
  画像のアノテーション画面を表示。画像・ラベル・既存アノテーションを取得。
- **save_annotations(request, image_id)**  
  アノテーションデータを保存。既存データを削除し新規登録。

### 4.3 ラベル管理

- **add_label(request)**  
  新規ラベルを追加（プロジェクト単位、重複不可）。
- **delete_label(request, label_id)**  
  ラベルを削除（使用中は不可）。
- **update_label(request, label_id)**  
  ラベル名・色を更新（重複不可）。
- **set_active_label(request)**  
  指定ラベルをアクティブ化（プロジェクト内で1つのみ）。

### 4.4 データセット生成

- **split_dataset(request)**  
  アノテーション済み画像をtrain/validに分割し、画像、YOLO形式ラベル、COCO JSON、YAMLを出力。

### 4.5 画像配信・サムネイル

- **serve_image(request, filename)**  
  プロジェクト内画像を動的に配信。複数パスを探索。
- **get_thumbnail(request, image_id, cropped)**  
  サムネイル画像を生成・配信。

---

## 5. 各関数の詳細説明

（例：index, annotate, save_annotations, split_dataset, serve_image など、主要関数の引数・処理内容・返却値を詳述）

### index(request)
- **目的**: 画像一覧・進捗表示
- **処理**:
  1. アクティブなプロジェクト取得
  2. プロジェクト未選択時は警告・リダイレクト
  3. 画像・ラベル・進捗数を集計
  4. テンプレートへデータ渡し
- **返却**: 画像一覧HTML

### annotate(request, image_id, cropped)
- **目的**: 画像アノテーション画面表示
- **処理**:
  1. 指定画像・プロジェクト取得
  2. ラベル・既存アノテーション取得
  3. 画像パス決定（cropped/original）
  4. 前後画像の取得
  5. テンプレートへデータ渡し
- **返却**: アノテーション画面HTML

### save_annotations(request, image_id)
- **目的**: アノテーションデータ保存
- **処理**:
  1. 既存アノテーション削除
  2. 新規アノテーション登録
  3. 画像のis_annotatedフラグ更新
- **返却**: JSON（成功/失敗）

### split_dataset(request)
- **目的**: データセット分割・RF-DETR形式出力
- **処理**:
  1. アノテーション済み画像・ラベル取得
  2. train/valid分割
  3. 画像リサイズ・パディング
  4. YOLO形式ラベルとCOCO JSONを生成
  5. データセットYAMLを生成
- **返却**: JSON（成功/失敗・出力先情報）

### serve_image(request, filename)
- **目的**: 画像ファイル配信
- **処理**:
  1. DB・複数パスから画像検索
  2. ファイル存在確認
  3. バイナリ配信
- **返却**: 画像データ or 404

---

## 6. クラス図（簡易）

```
Project
 └─<Label>
 └─<ImageFile>
      └─<Annotation>
```

---

## 7. 注意事項・設計上のポイント

- プロジェクト単位で全データを分離管理
- 画像・ラベル・アノテーションはDBで一元管理
- 画像パス探索は複数パターンに対応
- RF-DETR形式出力はラベルID・座標変換を厳密に実施

---

（`test-plc-server-bridge-to-CJ2` / `b6d2f2f` を2026年7月27日に再確認）
