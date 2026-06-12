#!/usr/bin/env python
"""
プロジェクトフォルダ作成とパステスト
"""
import os
import sys
import django
from pathlib import Path

# Djangoの設定を読み込み
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'object_detection_system.settings')
django.setup()

from django.conf import settings

def test_project_folder_creation():
    """プロジェクトフォルダ作成をテスト"""
    print("=" * 60)
    print("プロジェクトフォルダ作成テスト")
    print("=" * 60)
    
    # テスト用プロジェクト名
    test_project_name = "test_project_20250704"
    
    print(f"BASE_DIR: {settings.BASE_DIR}")
    print(f"BASE_DIR.parent: {settings.BASE_DIR.parent}")
    
    # プロジェクトフォルダパス
    base_dir = settings.BASE_DIR.parent  # inventry_checkerディレクトリ
    project_path = base_dir / 'projects' / test_project_name / 'data_collection'
    
    print(f"作成予定パス: {project_path}")
    print(f"絶対パス: {project_path.absolute()}")
    
    # ディレクトリ作成
    try:
        project_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ ディレクトリ作成成功: {project_path}")
        
        # 存在確認
        if project_path.exists():
            print(f"✅ ディレクトリ存在確認: {project_path}")
        else:
            print(f"❌ ディレクトリが存在しません: {project_path}")
            return False
            
        # テスト画像保存
        test_image_path = project_path / "test_image.txt"
        with open(test_image_path, "w") as f:
            f.write("This is a test file")
        
        if test_image_path.exists():
            print(f"✅ テストファイル作成成功: {test_image_path}")
            # テストファイルを削除
            test_image_path.unlink()
            print("✅ テストファイル削除完了")
        else:
            print(f"❌ テストファイル作成失敗: {test_image_path}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def list_existing_projects():
    """既存のプロジェクトフォルダを一覧表示"""
    print("\n" + "=" * 60)
    print("既存プロジェクトフォルダ一覧")
    print("=" * 60)
    
    base_dir = settings.BASE_DIR.parent
    projects_dir = base_dir / 'projects'
    
    print(f"プロジェクトディレクトリ: {projects_dir}")
    
    if not projects_dir.exists():
        print("❌ projectsディレクトリが存在しません")
        return
    
    projects = []
    for item in projects_dir.iterdir():
        if item.is_dir():
            data_collection_path = item / 'data_collection'
            has_data_collection = data_collection_path.exists()
            projects.append({
                'name': item.name,
                'path': item,
                'has_data_collection': has_data_collection,
                'data_collection_path': data_collection_path
            })
    
    if projects:
        print(f"見つかったプロジェクト: {len(projects)}個")
        for project in projects:
            status = "✅" if project['has_data_collection'] else "❌"
            print(f"  {status} {project['name']}")
            print(f"    パス: {project['path']}")
            print(f"    data_collection: {project['data_collection_path']}")
            if project['has_data_collection']:
                # data_collection内のファイル数を確認
                try:
                    files = list(project['data_collection_path'].glob('*'))
                    print(f"    ファイル数: {len(files)}")
                except:
                    print(f"    ファイル数: 確認不可")
            print()
    else:
        print("プロジェクトが見つかりませんでした")

if __name__ == "__main__":
    try:
        # 既存プロジェクト一覧
        list_existing_projects()
        
        # フォルダ作成テスト
        success = test_project_folder_creation()
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 プロジェクトフォルダテスト成功！")
        else:
            print("⚠️  プロジェクトフォルダテストで問題が検出されました。")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
