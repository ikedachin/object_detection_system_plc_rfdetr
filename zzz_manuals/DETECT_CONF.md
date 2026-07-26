# RF-DETRモデルの推論設定

> 対象: `test-plc-server-bridge-to-CJ2` / `b6d2f2f`（2026-07-27確認）

## 1. 設定ファイル

初期テンプレートは `settings/rfdetr_detect.yaml` です。学習完了後は、各 `TrainingRun.config_yaml_path` が示すYAMLをcheckerが使用します。

```yaml
RF_DETR:
  model_path:
  model_name: Roboflow/rf-detr-large
  num_queries:
  num_classes:
  num_select:
  class_names: []
  detect_config:
    conf: 0.45
    verbose: false
```

## 2. 項目

| 項目 | 型 | 役割 |
|---|---|---|
| `RF_DETR.model_path` | 文字列またはnull | 学習済みチェックポイント。通常はTrainingRun側で解決 |
| `RF_DETR.model_name` | 文字列 | RF-DETRモデル種別 |
| `RF_DETR.num_queries` | 整数またはnull | モデル生成時のquery数 |
| `RF_DETR.num_classes` | 整数またはnull | 学習クラス数 |
| `RF_DETR.num_select` | 整数またはnull | 選択候補数 |
| `RF_DETR.class_names` | 文字列配列 | クラスIDを表示名へ変換する一覧 |
| `RF_DETR.detect_config.conf` | 0～1の数値 | 検出信頼度の下限。既定値0.45 |
| `RF_DETR.detect_config.verbose` | 真偽値 | 推論処理の詳細出力用拡張値 |

## 3. 現行推論APIへの渡し方

`checker/applications/detect.py` は次の呼出しを行います。

```python
detections = model.predict(image, threshold=threshold)
```

`threshold` は `detect_config.conf` を使用します。`class_names` は検出結果にクラス名が含まれない場合の表示名解決に使います。

## 4. 注意事項

- 旧版に記載されていた `iou`、`imgsz`、`rect`、`save_txt`、`save_conf`、`retina_masks` 等はUltralytics系の引数であり、現行 `RFDETRBase.predict()` へそのまま渡す仕様ではありません。
- 未対応のキーを追加しても、現行 `detect_objects()` が参照しない限り動作は変わりません。
- 閾値を下げると検出数と誤検出が増え、上げると見逃しが増えます。変更後は実画像で員数判定を確認してください。
- `model_path` と `class_names` は学習成果物と一致させてください。
- パスが他PCのWindows絶対パスの場合は、システムが現在のプロジェクトルートへの再基準化を試みます。

## 5. 変更確認

1. checker画面で対象プロジェクトと学習モデルを有効化する。
2. モデルロード完了を確認する。
3. 既知のOK画像、NG画像、未検出画像、複数クラス画像で検査する。
4. 結果画像、クラス別件数、合否を確認する。
5. PLC運用時は画面確認後にダミーモードで信号を確認し、最後に実PLCで受入試験する。
