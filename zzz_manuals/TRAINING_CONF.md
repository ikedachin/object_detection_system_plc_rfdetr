
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
`imges/valid`は学習用データとば別の性能検証用のデータです。

<br>

---

### 学習時パラメータ
参考url：https://docs.rfdetr.com/ja/modes/train/

RF-DETRの学習時に設定できる主なパラメータは以下の通りです。学習アプリで主要なものは画面から選択することができます。追加で設定する場合は、詳細設定ボタンを押してjson形式で記入してください。



- **学習パラメータ一覧：**

| パラメータ | 説明 | 例 |
|---|---|---|
| model | 学習に使用するモデル | Roboflow/rf-detr-large |
| data | データセット設定ファイル | data.yaml |
| epochs | 学習の繰り返し回数 | 100 |
| batch | バッチサイズ | 16 |
| imgsz | 入力画像サイズ | 640 |
| name | 実験名（保存フォルダ名） | "exp1" |
| lr0 | 初期学習率 | 0.01 |
| lrf | 最終学習率係数 | 0.01 |
| momentum | モーメンタム | 0.937 |
| weight_decay | 重み減衰 | 0.0005 |
| optimizer | 最適化手法（SGD, Adam, auto） | 'auto' |
| dropout | ドロップアウト率 | 0.0 |
| patience | EarlyStoppingのpatience | 50 |
| device | 使用するデバイス（cpu/gpu） | 'cuda' |
| workers | データローダーのワーカ数 | 8 |
| project | 保存先ディレクトリ | "runs/train" |
| exist_ok | 既存フォルダ上書き可否 | True |
| pretrained | 事前学習済み重みの利用 | True |
| resume | 学習再開 | False |
| amp | 自動混合精度 | True |
| freeze | 凍結するレイヤー数 | 0 |
| rect | 画像を矩形で読み込む | False |
| cache | データセットキャッシュ | False |
| image_weights | 画像重み付け | False |
| single_cls | 単一クラス学習 | False |
| close_mosaic | Mosaic拡張の停止 | 0 |
| seed | 乱数シード | 0 |
| deterministic | 完全再現性 | False |
| val | 検証の有無 | True |
| plots | 学習中の可視化 | True |
| save | モデル保存 | True |
| save_period | 保存周期 | -1 |




詳細は公式ドキュメント（https://docs.rfdetr.com/ja/modes/train/）を参照してください。



- **オーグメンテーション（Augmentation）**

RF-DETRでは学習時に画像の拡張（オーグメンテーション）を自動で行い、汎化性能を高めます。主なオーグメンテーションは以下の通りです。

| オーグメンテーション | 説明 |

| オーグメンテーション | 説明 |
|---|---|
| mosaic | 複数画像の合成（Mosaic augmentation） |
| mixup | 画像のMixUp合成（MixUp augmentation） |
| copy_paste | 物体のコピー＆ペースト（Copy-Paste augmentation） |
| hsv | 色相・彩度・明度の変化（HSV augmentation） |
| flip | 画像の左右反転（Horizontal flip） |
| scale | 画像の拡大・縮小（Scaling） |
| translate | 画像の平行移動（Translation） |
| shear | 画像の斜め変形（Shearing） |
| perspective | 画像の遠近変換（Perspective transformation） |
| rotate | 画像の回転（Rotation） |
| pad | 画像のパディング（Padding） |
| blur | 画像のぼかし（Blurring） |
| gaussian | ガウシアンノイズ付加（Gaussian noise） |
| grayscale | グレースケール変換（Grayscale） |
| color_jitter | 色調・コントラスト・明度のランダム変化（Color jitter） |
| random_crop | ランダムクロップ（Random crop） |
| cutout | ランダム領域マスク（Cutout） |
| clahe | コントラスト制限付きヒストグラム平坦化（CLAHE） |
| channel_shuffle | チャンネルシャッフル（Channel shuffle） |
| sharpen | シャープ化（Sharpen） |
| emboss | エンボス加工（Emboss） |
| brightness | 明度変化（Brightness） |
| contrast | コントラスト変化（Contrast） |
| saturation | 彩度変化（Saturation） |
| exposure | 露光変化（Exposure） |

（一部はバージョンや設定により有効/無効が異なります。詳細は公式ドキュメントを参照してください）



詳細なパラメータやカスタマイズ方法は公式ドキュメントを参照してください。

---



