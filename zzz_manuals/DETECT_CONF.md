
## RF-DETRモデルの推論設定
---
RF-DETR物体検出の設定は `settings/rfdetr_detect.yaml` で管理されています。初期値は以下の設定が含まれます：

```yaml
RF-DETR:
  detect_config:
    conf: 0.45  # 信頼度閾値
    save: False  # 画像保存
    save_txt: True  # テキストファイルに結果保存
    save_conf: True  # 信頼度スコア保存
    line_width: 2  # バウンディングボックスの線幅
    exist_ok: True  # 既存結果ディレクトリの上書き許可
    verbose: False  # 詳細出力の抑制

image_size:
  type: SD480p  # 推論時の画像サイズ（640x480px）
```
<br>

---

#### 他に利用できる推論用の引数の設定（上級者向け）
これらを上記の`settings.rfdetr_detect.yaml`に追記していただくことも可能です。

参照url: https://docs.rfdetr.com/ja/modes/predict/#inference-sources

- **推論引数:**

| 引数 | タイプ	| デフォルト | 説明 |
| --- | --- | --- | --- |
| source | str,url または ndarray | 'rfdetr/assets' | 推論のデータソースを指定。画像パス、ビデオファイル、ディレクトリ、URL、ndarray。本プログラムではndarray |
| conf | float | 0.25 | 検出の最小信頼度しきい値の設定。この閾値以下の信頼度で検出されたオブジェクトは無視し、誤検出を減らす。 | 
| iou | float | 0.7 | Non-Maximum Suppression (NMS)のIntersection Over Union(IoU)しきい値。値が低いほど、重複するボックスが排除され、重複減。 | 
| imgsz | int または tuple | 640 | 推論のための画像サイズを定義。単一の整数値 640 正方形にリサイズする場合、または（高さ、幅）のタプルを使用。本プログラムでは640 | 
| rect | bool | True | Trueは画像の短辺をストライドで割り切れるまで最小限にパディングし、推論速度を向上。Falseにすると、推論中に画像を正方形にパディング。| 
| half | bool | False | 半精度(FP16)推論が可能。GPUでのモデル推論を、精度への影響を最小限に抑えながら高速化。今回はGPUを使用しない。 | 
| device | str | None | 推論を行うデバイスを指定（例． cpu, cuda:0 または 0）.CPU 、特定のGPU 、またはモデル実行用の他のコンピュート・デバイスを選択できる。 | 
| batch | int | 1 | 推論のバッチ・サイズを指定（ソースが ディレクトリ、ビデオファイル、または .txt ファイル）。今回は一枚ずつの処理なのでデフォルト設定。 | 
| max_det | int | 300 | 画像あたりの最大検出数。1回の推論でモデルが検出できるオブジェクトの最大値。 |
| vid_stride | int | 1 | ビデオ入力の時間的な解像度を犠牲にして処理を高速化するために、ビデオのフレームをいくつスキップするかを指定。1の値はすべてのフレームを処理し、それ以上の値はフレームをスキップする。 |
| stream_buffer | bool | False | ビデオストリームの受信フレームバッファに貯めるか否かを指定。Falseはリアルタイム・アプリケーション用に最適。Trueの場合、推論のFPSがストリームのFPSより低い場合、遅延が発生。|
| visualize | bool | False | 推論中にモデルの特徴量マップを可視化。モデルが何を「見て」いるのかを確認できる。デバッグやモデルの解釈用。 |
| augment | bool | False | 予測に対するテスト時間拡張（TTA）を可能にし、推論速度を犠牲にすることで検出のロバスト性を向上させる可能性がある。 |
| agnostic_nms | bool | False | 異なるクラスのオーバーラップしたボックスをマージ。クラスにとらわれない非最大抑制（NMS）を有効化。クラスの重複が一般的なマルチクラス検出シナリオに有効 |
| classes | list[int] | None | 指定されたクラスに属する物体のみを検出。複数クラスの検出タスクにおいて、必要なものだけに絞り込む時に利用。 |
| retina_masks | bool | False | 高解像度のセグメンテーションマスクを返す。。返されるマスク (masks.data)が有効なら、元の画像サイズと一致。無効にすると、推論時に使われた画像サイズ。
| embed | list[int] | None | 特徴ベクトルまたは埋め込みを抽出するレイヤを指定します。クラスタリングや類似検索のような下流のタスクに便利です。 |
| project | str | None | saveが有効の時、推論結果を出力するディレクトリの名前。 |
| name | str | None | saveが有効の時、projectディレクトリの中のサブディレクトリの名前を指定。 |
| stream | bool | False | すべてのフレームを一度にメモリにロードせず、Resultsオブジェクトのジェネレーターを返すことで、長いビデオや多数の画像のメモリ効率的な処理を可能にする。
| verbose | bool | True | ターミナルに詳細な推論ログを表示。 | 

<br>

- **可視化の引数：**

| 議論 | タイプ | デフォルト	| 説明 |
| --- | --- | --- | --- |
| show | bool | False | もし True注釈付きの画像やビデオをウィンドウに表示。開発中やテスト中の即時の視覚的フィードバックに便利。| 
| save | bool | False or True | 注釈付きの画像や動画をファイルに保存。文書化、デフォルトは、CLI の場合は True、Python の場合は False。 |
| save_frames | bool | False | 動画を処理する際、個々のフレームを画像として保存。|
| save_txt | bool | False | 検出結果をテキストファイルに保存します。 [class] [x_center] [y_center] [width] [height] [confidence]|
| save_conf | bool | False | Trueの場合、保存されたテキストファイルに信頼度スコアが含まれる。 | 
| save_crop | bool | False | 検出画像をトリミングして保存。 | 
| show_labels | bool | True | 視覚出力に各検出のラベルを表示。 |
| show_conf | bool | True | 各検出の信頼スコアがラベルと一緒に表示。 |
| show_boxes | bool | True | 検出されたオブジェクトの周囲にバウンディングボックスを描画。 |
| line_width | None or int | None | バウンディングボックスの線幅を指定。 | 


