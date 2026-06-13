
## RF-DETRモデルの学習設定
---

### データセット設定
アノテーション後、画像分割ボタンを押下するとそのプロジェクトフォルダ内にyamlファイルが自動生成されます。この情報によって学習されます。


例:
```yaml
# Train/val/test sets as 1) dir: path/to/imgs, 2) file: path/to/imgs.txt, or 3) list: [path/to/imgs1, path/to/imgs2, ..]
path: ../../datasets/project_20250724_222419 # dataset root dir
train: images/train # train images
val: images/valid # val images
test: # test images (optional)

# Classes
names:
  0: red  # 赤い物体
  1: long  # 長い物体
  2: small  # 小さい物体
```
これらのアノテーションラベル（`names`）、学習データ（`images/train`）によって学習します。
`images/valid` は学習用データとは別の性能検証用データです。

<br>

---

### 学習時パラメータ
参考url：https://rfdetr.roboflow.com/latest/learn/run/detection/

RF-DETRの学習時に設定できる主なパラメータは以下の通りです。学習アプリで主要なものは画面から選択できます。追加で設定する場合は、詳細設定ボタンを押してJSON形式で記入してください。



- **学習パラメータ一覧：**

| パラメータ | 説明 | 例 |
|---|---|---|
| model_name | 学習に使用するRF-DETRモデル | Roboflow/rf-detr-large |
| dataset_yaml | データセット設定ファイル | data.yaml |
| epochs | 学習の繰り返し回数 | 100 |
| batch_size | バッチサイズ | 16 |
| resolution | 入力画像サイズ | 640 |
| grad_accum_steps | 勾配蓄積ステップ数 | 4 |
| accelerator | 実行アクセラレータ。auto/cpu/cuda/mpsなど | auto |
| num_workers | データローダーのワーカ数 | 1 |
| lr | 学習率 | 0.0001 |
| lr_encoder | encoder側の学習率 | 0.00015 |
| weight_decay | 重み減衰 | 0.0001 |
| eval_interval | 検証を実行する間隔 | 1 |
| compute_val_loss | validation lossを計算するか | true |
| use_ema | EMAを使うか | true |
| gradient_checkpointing | メモリ削減用のgradient checkpointing | false |
| tensorboard | TensorBoardログを出力するか | false |
| wandb | Weights & Biasesログを出力するか | false |
| project | ロガー用プロジェクト名 | "runs/train" |
| run | ロガー用実行名 | "exp1" |
| resume | 学習再開用チェックポイント | checkpoint.pth |
| pretrain_weights | 事前学習済み重み | checkpoint.pth |
| checkpoint_interval | チェックポイント保存間隔 | 1 |
| seed | 乱数シード | 0 |
| early_stopping | Early Stoppingを使うか | false |
| early_stopping_patience | Early Stoppingのpatience | 10 |
| early_stopping_min_delta | Early Stoppingの最小改善量 | 0.001 |
| aug_config | Albumentations形式の拡張設定 | {"HorizontalFlip": {"p": 0.5}} |
| num_queries | DETR query数 | 300 |
| num_select | 推論時に選択する候補数 | 300 |
| pin_memory | DataLoaderのpin_memory | true |
| persistent_workers | DataLoader workerを保持するか | false |
| prefetch_factor | DataLoaderのprefetch数 | 2 |
| progress_bar | 進捗表示方式 | rich |

詳細は公式ドキュメント（https://rfdetr.roboflow.com/latest/learn/run/detection/）を参照してください。



- **オーグメンテーション（Augmentation）**

本アプリではRF-DETRの `aug_config` にAlbumentations形式のJSONを渡せます。空欄はRF-DETR標準、`{}` は拡張なしです。`p` を0より大きくすると、その変換が有効になります。

| オーグメンテーション | 説明 |
|---|---|
| HorizontalFlip | 左右反転 |
| VerticalFlip | 上下反転 |
| Rotate | 回転 |
| Affine | 拡大縮小、平行移動、回転、せん断 |
| ShiftScaleRotate | 平行移動、拡大縮小、回転 |
| RandomCrop / CenterCrop / RandomResizedCrop | クロップ |
| Perspective | 遠近変換 |
| ElasticTransform / GridDistortion | 形状変形 |
| ColorJitter / HueSaturationValue / RandomBrightnessContrast | 色、明度、コントラスト調整 |
| GaussianBlur / Blur / GaussNoise | ぼかし、ノイズ |
| CLAHE / Sharpen / Equalize | コントラスト補正、シャープ化、ヒストグラム平坦化 |

Albumentations本体はMIT Licenseです。後継のAlbumentationsXは別ライセンスのため、導入するライブラリ名とライセンスを区別してください。



詳細なパラメータやカスタマイズ方法は公式ドキュメントを参照してください。

---

