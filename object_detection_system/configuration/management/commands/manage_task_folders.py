from django.core.management.base import BaseCommand
from django.conf import settings
import os
import shutil
from pathlib import Path


class Command(BaseCommand):
    help = 'Manage task-based folder operations for the inventory checker'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=['create', 'migrate', 'status', 'move', 'workflow'],
            help='Action to perform: create, migrate, status, move, or workflow'
        )
        parser.add_argument(
            '--workflow-type',
            type=str,
            choices=['with-crop', 'without-crop'],
            help='Workflow type: with-crop or without-crop'
        )
        parser.add_argument(
            '--source',
            type=str,
            help='Source folder for move action'
        )
        parser.add_argument(
            '--target',
            type=str,
            choices=['data_collection_auto', 'data_collection_manual', 'crop_source', 
                    'crop_cropped', 'annotation_images', 'training_images', 
                    'production_input', 'production_output'],
            help='Target folder for move action'
        )
        parser.add_argument(
            '--filename',
            type=str,
            help='Specific filename to move'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'create':
            self.create_folders()
        elif action == 'migrate':
            self.migrate_existing_data()
        elif action == 'status':
            self.show_status()
        elif action == 'move':
            self.move_files(options)
        elif action == 'workflow':
            self.execute_workflow(options)

    def get_task_folders(self):
        """タスク別フォルダの定義を取得"""
        return {
            'data_collection_auto': getattr(settings, 'DATA_COLLECTION_AUTO_DIR'),
            'data_collection_manual': getattr(settings, 'DATA_COLLECTION_MANUAL_DIR'),
            'crop_source': getattr(settings, 'CROP_PREPARATION_SOURCE_DIR'),
            'crop_cropped': getattr(settings, 'CROP_PREPARATION_CROPPED_DIR'),
            'annotation_images': getattr(settings, 'ANNOTATION_IMAGES_DIR'),
            'annotation_labels': getattr(settings, 'ANNOTATION_LABELS_DIR'),
            'training_images': getattr(settings, 'TRAINING_IMAGES_DIR'),
            'training_labels': getattr(settings, 'TRAINING_LABELS_DIR'),
            'production_input': getattr(settings, 'PRODUCTION_INPUT_DIR'),
            'production_output': getattr(settings, 'PRODUCTION_OUTPUT_DIR'),
        }

    def create_folders(self):
        """タスク別フォルダ構成を作成"""
        folders = self.get_task_folders()
        
        for name, path in folders.items():
            if path:
                path.mkdir(parents=True, exist_ok=True)
                self.stdout.write(
                    self.style.SUCCESS(f'Created folder: {name} -> {path}')
                )
                
                # READMEファイルを作成
                readme_path = path / 'README.txt'
                if not readme_path.exists():
                    self.create_readme(name, readme_path)

    def create_readme(self, folder_name, readme_path):
        """フォルダ用のREADMEファイルを作成"""
        content_map = {
            'data_collection_auto': 'データ収集（自動）: 自動撮影・バッチ処理で取得された画像',
            'data_collection_manual': 'データ収集（手動）: 手動撮影・外部取り込み画像',
            'crop_source': '切り抜き準備（元画像）: 切り抜き処理の元となる画像',
            'crop_cropped': '切り抜き準備（処理済み）: 切り抜き・リサイズ済み画像',
            'annotation_images': 'アノテーション（画像）: ラベリング対象画像',
            'annotation_labels': 'アノテーション（ラベル）: 正規化BBox形式ラベルファイル',
            'training_images': '学習データ（画像）: 機械学習用学習画像',
            'training_labels': '学習データ（ラベル）: 機械学習用ラベルデータ',
            'production_input': '実用データ（入力）: 員数確認用入力画像',
            'production_output': '実用データ（出力）: 員数確認結果データ',
        }
        
        content = f"# {content_map.get(folder_name, folder_name)}\n\n"
        content += f"作成日時: {os.getcwd()}\n"
        content += "このフォルダは在庫確認システムのタスク別データ管理用です。\n"
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def migrate_existing_data(self):
        """既存データを新フォルダ構成に移行"""
        project_root = settings.PROJECT_ROOT
        
        # 移行マッピング
        migration_map = [
            (project_root / 'base_images', self.get_task_folders()['data_collection_auto']),
            (project_root / 'snaps' / 'snaps_auto', self.get_task_folders()['data_collection_auto']),
            (project_root / 'snaps' / 'snaps_manual', self.get_task_folders()['data_collection_manual']),
            (settings.MEDIA_ROOT / 'cropped', self.get_task_folders()['crop_cropped']),
        ]
        
        image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.JPG', '.JPEG', '.PNG')
        
        for src_path, dst_path in migration_map:
            if src_path.exists():
                self.stdout.write(f'Migrating: {src_path} -> {dst_path}')
                
                # ターゲットフォルダを作成
                dst_path.mkdir(parents=True, exist_ok=True)
                
                copied_count = 0
                for file_path in src_path.iterdir():
                    if file_path.is_file() and file_path.suffix in image_extensions:
                        dst_file = dst_path / file_path.name
                        
                        if not dst_file.exists():
                            shutil.copy2(file_path, dst_file)
                            copied_count += 1
                
                self.stdout.write(
                    self.style.SUCCESS(f'  Copied {copied_count} images')
                )

    def show_status(self):
        """各フォルダの状況を表示"""
        folders = self.get_task_folders()
        image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
        
        self.stdout.write(self.style.SUCCESS('Task Folder Status:'))
        self.stdout.write('=' * 60)
        
        for name, path in folders.items():
            if path and path.exists():
                files = [f for f in path.iterdir() 
                        if f.is_file() and f.suffix.lower() in image_extensions]
                self.stdout.write(f'{name:25} | {len(files):4} files | {path}')
            else:
                self.stdout.write(f'{name:25} | NOT FOUND | {path}')

    def move_files(self, options):
        """ファイルをタスク間で移動"""
        source = options.get('source')
        target = options.get('target') 
        filename = options.get('filename')
        
        if not all([source, target]):
            self.stdout.write(
                self.style.ERROR('Both --source and --target are required for move action')
            )
            return
        
        folders = self.get_task_folders()
        
        # ソースパスを解決
        if source in folders:
            source_path = folders[source]
        else:
            source_path = Path(source)
        
        target_path = folders.get(target)
        
        if not source_path or not source_path.exists():
            self.stdout.write(
                self.style.ERROR(f'Source path not found: {source_path}')
            )
            return
        
        if not target_path:
            self.stdout.write(
                self.style.ERROR(f'Invalid target: {target}')
            )
            return
        
        target_path.mkdir(parents=True, exist_ok=True)
        
        # ファイル移動
        if filename:
            # 特定ファイルのみ移動
            src_file = source_path / filename
            dst_file = target_path / filename
            
            if src_file.exists():
                shutil.move(str(src_file), str(dst_file))
                self.stdout.write(
                    self.style.SUCCESS(f'Moved: {filename}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'File not found: {filename}')
                )
        else:
            # 全ての画像ファイルを移動
            image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
            moved_count = 0
            
            for file_path in source_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                    dst_file = target_path / file_path.name
                    shutil.move(str(file_path), str(dst_file))
                    moved_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(f'Moved {moved_count} files from {source} to {target}')
            )

    def execute_workflow(self, options):
        """ワークフロー実行"""
        workflow_type = options.get('workflow_type')
        
        if not workflow_type:
            self.stdout.write(
                self.style.ERROR('--workflow-type is required for workflow action')
            )
            return
        
        folders = self.get_task_folders()
        
        if workflow_type == 'with-crop':
            self.stdout.write(
                self.style.SUCCESS('切り抜きありワークフロー')
            )
            self.stdout.write('手順:')
            self.stdout.write('1. データ収集 → crop_preparation/source/')
            self.stdout.write('2. 切り抜き処理 → crop_preparation/cropped/')
            self.stdout.write('3. アノテーション → annotation_data/images/')
            self.stdout.write('4. 学習データ準備 → training_data/')
            self.stdout.write('5. 実用データ処理 → production_data/')
            
            # データ収集からcrop_preparationへの移行例
            data_collection_auto = folders['data_collection_auto']
            crop_source = folders['crop_source']
            
            if data_collection_auto.exists() and crop_source:
                image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
                images = [f for f in data_collection_auto.iterdir() 
                         if f.is_file() and f.suffix.lower() in image_extensions]
                
                if images:
                    self.stdout.write(f'利用可能な画像: {len(images)}枚 ({data_collection_auto})')
                    self.stdout.write('次のコマンドで移行できます:')
                    self.stdout.write(f'python manage.py manage_task_folders move --source=data_collection_auto --target=crop_source')
        
        elif workflow_type == 'without-crop':
            self.stdout.write(
                self.style.SUCCESS('切り抜きなしワークフロー')
            )
            self.stdout.write('手順:')
            self.stdout.write('1. データ収集 → annotation_data/images/ (直接)')
            self.stdout.write('2. アノテーション → annotation_data/labels/')
            self.stdout.write('3. 学習データ準備 → training_data/')
            self.stdout.write('4. 実用データ処理 → production_data/')
            
            # データ収集からアノテーションへの直接移行例
            data_collection_auto = folders['data_collection_auto']
            annotation_images = folders['annotation_images']
            
            if data_collection_auto.exists() and annotation_images:
                image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
                images = [f for f in data_collection_auto.iterdir() 
                         if f.is_file() and f.suffix.lower() in image_extensions]
                
                if images:
                    self.stdout.write(f'利用可能な画像: {len(images)}枚 ({data_collection_auto})')
                    self.stdout.write('次のコマンドで移行できます:')
                    self.stdout.write(f'python manage.py manage_task_folders move --source=data_collection_auto --target=annotation_images')
