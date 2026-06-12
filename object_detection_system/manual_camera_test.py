#!/usr/bin/env python
"""
手動カメラテスト（画像保存付き）
"""
import os
import sys
import django
from pathlib import Path
import time

# Djangoの設定を読み込み
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'object_detection_system.settings')
django.setup()

from django.conf import settings
from get_imgs.applications.camera_get_data import VideoCamera, find_available_cameras

def get_project_data_collection_path(project_name):
    """プロジェクトのdata_collectionフォルダパスを取得"""
    if not project_name:
        project_name = f"manual_test_{time.strftime('%Y%m%d_%H%M%S')}"
    
    base_dir = settings.BASE_DIR.parent
    project_path = base_dir / 'projects' / project_name / 'data_collection'
    project_path.mkdir(parents=True, exist_ok=True)
    return project_path

def manual_camera_test():
    """手動でカメラをテストして画像を保存"""
    print("=" * 60)
    print("手動カメラテスト（画像保存付き）")
    print("=" * 60)
    
    # 利用可能なカメラを検索
    available_cameras = find_available_cameras()
    if not available_cameras:
        print("❌ 利用可能なカメラが見つかりません")
        return False
    
    print(f"✅ 利用可能なカメラ: {available_cameras}")
    
    # テスト用プロジェクト名
    project_name = f"manual_test_{time.strftime('%Y%m%d_%H%M%S')}"
    save_path = get_project_data_collection_path(project_name)
    print(f"保存先: {save_path}")
    
    try:
        # カメラを初期化
        camera = VideoCamera(src=available_cameras[0], width=640, height=480)
        print(f"✅ カメラ {available_cameras[0]} 初期化成功")
        
        # 5枚の画像を取得して保存
        for i in range(5):
            print(f"画像 {i+1}/5 を取得中...")
            frame_data = camera.get_jpeg()
            
            if frame_data:
                filename = f"test_image_{i+1:02d}_{time.strftime('%H%M%S')}.jpg"
                output_path = save_path / filename
                
                with open(output_path, "wb") as f:
                    f.write(frame_data)
                
                file_size = output_path.stat().st_size
                print(f"✅ 保存成功: {filename} ({file_size} bytes)")
            else:
                print(f"❌ フレーム取得失敗")
            
            time.sleep(1)  # 1秒待機
        
        camera.stop()
        print(f"✅ カメラ停止完了")
        
        # 保存された画像の確認
        saved_files = list(save_path.glob("*.jpg"))
        print(f"\n保存された画像: {len(saved_files)}個")
        for file_path in saved_files:
            size = file_path.stat().st_size
            print(f"  - {file_path.name}: {size} bytes")
        
        return len(saved_files) > 0
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = manual_camera_test()
        print("\n" + "=" * 60)
        if success:
            print("🎉 手動カメラテスト成功！画像が正常に保存されました。")
        else:
            print("⚠️  手動カメラテストで問題が検出されました。")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
