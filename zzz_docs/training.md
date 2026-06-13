# trainingアプリケーション プログラム設計書

## 1. システム概要

本アプリは、RF-DETR物体検出モデルの学習・管理を行うDjangoアプリケーションです。  
プロジェクト単位で学習データセット・パラメータ・学習履歴・モデルファイルを一元管理し、YAML編集や学習結果の保存もサポートします。

---

## 2. 全体フロー図

```
[プロジェクト選択]
      ↓
[YAML選択・編集]
      ↓
[学習パラメータ入力]
      ↓
[RF-DETR学習実行]
      ↓
[モデル・メトリクス保存]
      ↓
[履歴・再学習・YAML編集]
```

---

## 3. 主要関数・API詳細

### 3.1 学習管理・実行

- **train_view(request)**  
  学習画面表示・学習実行・YAML取得/編集・プロジェクト/YAMLリスト取得を一括管理するメインビュー。
- **get_projects_with_yaml(data_type)**  
  指定データ種別（cropped/data_collection）でYAMLが存在するプロジェクト一覧を返却。
- **get_dataset_yamls(project, data_type)**  
  プロジェクト・データ種別ごとのYAMLファイル一覧を返却。

---

## 4. 各関数の詳細説明

### train_view(request)
- **目的**: 学習画面表示・学習実行・YAML取得/編集
- **処理**:
  1. POST: 学習リクエスト受信→RF-DETR学習実行→モデル・メトリクス保存→DB登録
  2. GET(yaml_path): YAMLファイル内容取得
  3. GET(project_name, data_type): プロジェクト・データ種別ごとのYAMLリスト取得
  4. POST(yaml_edit_path): YAMLファイル内容書き換え
  5. GET(デフォルト): プロジェクト・YAMLリスト・画面表示
- **返却**: JSON/HTML

### get_projects_with_yaml(data_type)
- **目的**: YAMLが存在するプロジェクト一覧取得
- **処理**:
  1. DBから全プロジェクト取得
  2. 指定データ種別のannotated配下にYAMLが存在するもののみ返却
- **返却**: プロジェクトリスト

### get_dataset_yamls(project, data_type)
- **目的**: プロジェクト・データ種別ごとのYAMLファイル一覧取得
- **処理**:
  1. annotated配下のYAMLファイルを列挙
- **返却**: YAMLファイルリスト

---

## 5. クラス図（簡易）

```
Project
  ↑
TrainingRun
  ↑
train_view
```

---

## 6. 注意事項・設計上のポイント

- 学習パラメータ・履歴・モデルパス・メトリクスをDBで一元管理
- YAML編集・取得APIも統合
- 学習実行時はプロジェクトのactive_yaml_path/active_weight_pathも更新
- RF-DETRのaccelerator設定（auto/cpu/cuda/mps）

---

（本設計書は2026年6月13日現在のRF-DETR実装に基づく）
