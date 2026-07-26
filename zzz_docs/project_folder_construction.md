# プロジェクトフォルダ構成

> 対象: `test-plc-server-bridge-to-CJ2` / `b6d2f2f`（2026-07-27確認）

```text
project-root/
├── projects/
│   └── {project.folder_name}/
│       ├── data_collection/          # get_imgsで撮影した元画像
│       ├── cropped/                  # crop_appで一括切り抜きした画像
│       ├── annotated/
│       │   ├── data_collection/      # 元画像を使う学習データ
│       │   │   ├── images/
│       │   │   │   ├── train/
│       │   │   │   └── valid/
│       │   │   ├── labels/
│       │   │   │   ├── train/
│       │   │   │   └── valid/
│       │   │   ├── annotations/      # COCO JSON
│       │   │   └── data.yaml
│       │   └── cropped/              # 切り抜き画像を使う学習データ
│       │       └── （同じ構成）
│       ├── models/
│       │   └── {training_name}/      # checkpoint、metrics、推論設定
│       └── thumbnail/                # 画面表示用サムネイル
├── detect/
│   └── YYYYMMDD/
│       └── HH_MM_SS/
│           └── predict/
│               └── latest.png
└── settings/
    ├── plc_settings.yaml
    ├── rfdetr_detect.yaml
    └── rfdetr_detect_format.yaml
```

## 補足

- `annotated` 直下ではなく、入力種別ごとの `data_collection` または `cropped` 配下に学習データが生成されます。
- RF-DETR学習用にCOCOアノテーションを生成します。YOLO形式のラベルファイルもデータセット生成処理で出力されます。
- 学習成果物の正確なファイル名はRF-DETRのバージョンと学習結果に依存します。
- DBに保存された他PC由来のパスは、checkerが現在のリポジトリルートへ再基準化する場合があります。
