#!/usr/bin/env python
"""
簡単なカメラテスト用スクリプト
"""
import sys
sys.path.append('.')
sys.path.append('./get_imgs/applications')

try:
    from get_imgs.applications.camera_get_data import find_available_cameras, VideoCamera
    print("カメラモジュールのインポート成功")
except ImportError as e:
    print(f"カメラモジュールのインポート失敗: {e}")
    # フォールバック：直接OpenCVでテスト
    import cv2
    
    print("OpenCVによる直接カメラテスト")
    print("=" * 50)
    
    found_cameras = []
    for i in range(5):
        print(f"カメラ {i} をテスト中...", end="")
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                height, width = frame.shape[:2]
                print(f" ✅ 利用可能 ({width}x{height})")
                found_cameras.append(i)
            else:
                print(" ❌ フレーム読み込み失敗")
        else:
            print(" ❌ 利用不可")
        cap.release()
    
    if found_cameras:
        print(f"\n✅ {len(found_cameras)}個のカメラが見つかりました: {found_cameras}")
    else:
        print("\n❌ 利用可能なカメラが見つかりませんでした。")
    
    sys.exit(0)

def main():
    print("=" * 50)
    print("カメラテストプログラム")
    print("=" * 50)
    
    # 1. 利用可能なカメラを検索
    print("\n1. 利用可能なカメラを検索中...")
    available_cameras = find_available_cameras()
    
    if not available_cameras:
        print("❌ 利用可能なカメラが見つかりませんでした。")
        return False
    
    print(f"✅ {len(available_cameras)}個のカメラが利用可能です: {available_cameras}")
    
    # 2. 最初のカメラをテスト
    camera_index = available_cameras[0]
    print(f"\n2. カメラ {camera_index} のテスト中...")
    try:
        camera = VideoCamera(src=camera_index, width=640, height=480)
        print(f"✅ カメラ {camera_index} の初期化成功")
        
        # フレームテスト
        for i in range(3):
            frame_data = camera.get_jpeg()
            if frame_data:
                print(f"✅ フレーム {i+1}: {len(frame_data)} bytes")
            else:
                print(f"❌ フレーム {i+1}: 取得失敗")
        
        camera.stop()
        print(f"✅ カメラ {camera_index} のテスト完了")
        return True
        
    except Exception as e:
        print(f"❌ カメラ {camera_index} のテスト失敗: {e}")
        return False

if __name__ == "__main__":
    try:
        success = main()
        print("\n" + "=" * 50)
        if success:
            print("🎉 カメラテスト完了！カメラが正常に動作しています。")
        else:
            print("⚠️  カメラテストで問題が検出されました。")
        print("=" * 50)
    except KeyboardInterrupt:
        print("\n\nテストが中断されました。")
    except Exception as e:
        print(f"\n❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()
