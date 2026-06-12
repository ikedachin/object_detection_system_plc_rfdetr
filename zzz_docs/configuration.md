# configurationアプリケーション プログラム設計書

## 1. システム概要

本アプリは、アノテーションプロジェクトの作成・管理・削除・情報取得・アクティブ化など、プロジェクト全体の設定・運用管理を担うDjangoアプリケーションです。  
また、ワークフローや進捗管理のためのモデル・APIも提供します。

---

## 2. 全体フロー図

```
[プロジェクト追加/削除]
      ↓
[プロジェクト情報取得]
      ↓
[プロジェクトアクティブ化]
      ↓
[ワークフロー/進捗管理]
      ↓
[各アプリ連携]
```

---

## 3. 主要関数・API詳細

### 3.1 プロジェクト管理

- **project_manager(request)**  
  プロジェクト一覧・管理画面を表示。DBから全プロジェクト情報を取得。
- **add_project(request)**  
  新規プロジェクト作成API。画像アップロード・DB登録・アクティブ化まで一括実行。
- **delete_project(request)**  
  プロジェクト削除API。ディレクトリ・DB両方から削除。
- **get_project_info(request)**  
  プロジェクト情報取得API。画像数・サイズ・ファイル一覧を返却。
- **set_active_project(request)**  
  プロジェクトをアクティブ化するAPI。DBのis_activeフラグを更新。

### 3.2 ワークフロー・進捗管理

- **workflow_manager(request)**  
  ワークフロー管理画面の表示。
- **change_workflow(request)**  
  ワークフロー設定の変更API。

### 3.3 共通・補助

- **parse_json_request(request)**  
  リクエストボディからJSONを安全に解析する共通関数。
- **crop_redirect(request)**  
  画像切り抜きアプリへのリダイレクト。

---

## 4. 各関数の詳細説明

### project_manager(request)
- **目的**: プロジェクト一覧・管理画面の表示
- **処理**:
  1. DBから全プロジェクト情報を取得
  2. テンプレートへデータ渡し
- **返却**: HTML

### add_project(request)
- **目的**: 新規プロジェクト作成API
- **処理**:
  1. POSTデータ・画像ファイル受信
  2. プロジェクトディレクトリ作成
  3. 画像保存・DB登録
  4. アクティブ化
- **返却**: JSON

### delete_project(request)
- **目的**: プロジェクト削除API
- **処理**:
  1. POSTデータ受信
  2. ディレクトリ削除
  3. DBからも削除
- **返却**: JSON

### get_project_info(request)
- **目的**: プロジェクト情報取得API
- **処理**:
  1. GETパラメータ受信
  2. ディレクトリ内画像数・サイズ・ファイル一覧集計
- **返却**: JSON

### set_active_project(request)
- **目的**: プロジェクトのアクティブ化
- **処理**:
  1. POSTデータ受信
  2. DBのis_activeフラグを更新
- **返却**: JSON

### workflow_manager(request), change_workflow(request)
- **目的**: ワークフロー管理画面表示・設定変更
- **処理**: DBのワークフロー設定を取得・更新
- **返却**: HTML/JSON

### parse_json_request(request)
- **目的**: JSONデータの安全なパース
- **処理**: バイト列→文字列→JSONデコード
- **返却**: (データ, エラー)

### crop_redirect(request)
- **目的**: 画像切り抜きアプリへのリダイレクト
- **処理**: `/crop/` へリダイレクト
- **返却**: HTTPリダイレクト

---

## 5. クラス図（簡易）

```
Project
  ↑
project_manager, add_project, delete_project, get_project_info, set_active_project
  ↓
WorkflowSetting, TaskProgress, ProjectTaskProgress, ProjectWorkflowState
  ↑
workflow_manager, change_workflow
```

---

## 6. 注意事項・設計上のポイント

- プロジェクトの物理ディレクトリとDB情報を常に同期
- アクティブプロジェクトはis_activeフラグで一元管理
- ワークフロー・進捗管理は専用モデルで柔軟に拡張可能
- 画像アップロード・削除時のエラーハンドリングを徹底

---

（本設計書は2025年7月25日現在の実装に基づく）
