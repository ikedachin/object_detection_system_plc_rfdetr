# ライセンス整理

この文書は、このリポジトリ本体と外部ライブラリ・モデルのライセンス境界を整理するためのメモです。正式な法務判断が必要な場合は、各提供元の最新ライセンス文書を確認してください。

## このリポジトリ本体

Copyright 2026 ikedachin.

このリポジトリに含まれるDjangoアプリケーションコード、画面、補助スクリプト、ドキュメントは Apache License 2.0 として扱います。

本リポジトリは、RF-DETRやAlbumentationsを利用しやすくするためのWebアプリケーションです。RF-DETR本体、Albumentations本体、学習済みモデル重みを本リポジトリ独自の成果物として再ライセンスするものではありません。

## RF-DETR

RF-DETRはRoboflow社が提供する物体検出モデルおよびPythonパッケージです。RF-DETRの使用、モデル重み、追加コンポーネントにはRoboflow社が定めるライセンス条件が適用されます。

Roboflow社のRF-DETR READMEでは、通常の `rfdetr` パッケージおよびApache指定モデルはApache 2.0、Plus系コンポーネント（`rfdetr_plus`、RF-DETR-XL/2XL detection modelなど）はPML 1.0と説明されています。Plus系を使う場合は、Roboflow社の最新条件を必ず確認してください。

## Albumentations

Albumentations本体はMIT Licenseの画像拡張ライブラリです。本アプリではRF-DETR学習時の `aug_config` を通じてAlbumentations形式の拡張設定を利用します。

AlbumentationsとAlbumentationsXは区別してください。AlbumentationsXはAlbumentationsの後継プロジェクトですが、Albumentations本体とは異なるライセンス体系です。このリポジトリで前提としているのは `albumentations` パッケージです。

## 配布時の注意

- このリポジトリ本体を配布する場合は、Apache License 2.0のライセンス文書を同梱してください。
- RF-DETR、RF-DETRのモデル重み、Plus系コンポーネントを同梱・利用する場合は、Roboflow社のライセンス条件を確認してください。
- Albumentationsを同梱・利用する場合は、AlbumentationsのMIT License条件を確認してください。
- 依存ライブラリのライセンスは、`uv.lock` や実際のインストール環境に基づいてリリース前に再確認してください。
