from django.db import models
from annotator.models import Project
from training.models import TrainingRun

# Create your models here.

class InferenceResult(models.Model):
    """推論結果を保存するモデル"""
    # 関連情報
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='inference_results', verbose_name="プロジェクト")
    training_run = models.ForeignKey(TrainingRun, on_delete=models.CASCADE, related_name='inference_results', verbose_name="学習モデル")
    
    # 推論実行情報
    model_name = models.CharField(max_length=255, verbose_name="モデル名")
    
    # 画像情報
    result_image_path = models.CharField(max_length=512, verbose_name="推論結果画像パス")
    image_width = models.PositiveIntegerField(verbose_name="画像幅")
    image_height = models.PositiveIntegerField(verbose_name="画像高さ")
    
    # 推論結果サマリー
    detected_class_summary = models.JSONField(verbose_name="検出クラス要約", help_text="クラス名とカウントの辞書")
    total_objects_count = models.PositiveIntegerField(verbose_name="総検出オブジェクト数", default=0)
    
    # 推論設定
    inference_config = models.JSONField(verbose_name="推論設定", default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="レコード作成日時")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "推論結果"
        verbose_name_plural = "推論結果"
    
    def __str__(self):
        return f"{self.project.name} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')} - {self.total_objects_count}個検出"


class DetectedObject(models.Model):
    """検出されたオブジェクトの詳細情報を保存するモデル"""
    inference_result = models.ForeignKey(InferenceResult, on_delete=models.CASCADE, related_name='detected_objects', verbose_name="推論結果")
    
    # RF-DETR出力情報
    class_id = models.PositiveIntegerField(verbose_name="クラスID")
    class_name = models.CharField(max_length=100, verbose_name="クラス名")
    confidence = models.FloatField(verbose_name="信頼度")
    
    # バウンディングボックス座標（正規化BBox形式：中央座標x, y + 幅w, 高さh、全て元画像に対する割合）
    bbox_center_x = models.FloatField(verbose_name="中央X座標", help_text="バウンディングボックス中央のX座標（元画像に対する割合）")
    bbox_center_y = models.FloatField(verbose_name="中央Y座標", help_text="バウンディングボックス中央のY座標（元画像に対する割合）")
    bbox_width = models.FloatField(verbose_name="幅", help_text="バウンディングボックスの幅（元画像に対する割合）")
    bbox_height = models.FloatField(verbose_name="高さ", help_text="バウンディングボックスの高さ（元画像に対する割合）")
    
    class Meta:
        ordering = ['-confidence']
        verbose_name = "検出オブジェクト"
        verbose_name_plural = "検出オブジェクト"
    
    def __str__(self):
        return f"{self.class_name} (信頼度: {self.confidence:.2f})"

