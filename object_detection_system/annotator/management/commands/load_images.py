from django.core.management.base import BaseCommand
from django.conf import settings
from annotator.models import ImageFile
import os
from PIL import Image


class Command(BaseCommand):
    help = 'Load images from multiple task-based directories into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            default='all',
            help='Source directory: all, data_collection, annotation, crop_preparation, or legacy'
        )

    def handle(self, *args, **options):
        source = options['source']
        
        # タスク別ディレクトリの定義
        source_dirs = []
        
        if source == 'all' or source == 'data_collection':
            source_dirs.extend([
                ('data_collection_auto', getattr(settings, 'DATA_COLLECTION_AUTO_DIR', None)),
                ('data_collection_manual', getattr(settings, 'DATA_COLLECTION_MANUAL_DIR', None)),
            ])
        
        if source == 'all' or source == 'annotation':
            source_dirs.append(('annotation_images', getattr(settings, 'ANNOTATION_IMAGES_DIR', None)))
        
        if source == 'all' or source == 'crop_preparation':
            source_dirs.extend([
                ('crop_source', getattr(settings, 'CROP_PREPARATION_SOURCE_DIR', None)),
                ('crop_cropped', getattr(settings, 'CROP_PREPARATION_CROPPED_DIR', None)),
            ])
        
        if source == 'all' or source == 'legacy':
            source_dirs.append(('legacy_base_images', getattr(settings, 'BASE_IMAGES_DIR', None)))
        
        # 存在するディレクトリのみをフィルタリング
        valid_dirs = [(name, path) for name, path in source_dirs if path and os.path.exists(path)]
        
        if not valid_dirs:
            self.stdout.write(
                self.style.ERROR(f'No valid directories found for source: {source}')
            )
            return

        supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
        loaded_count = 0
        
        for dir_name, image_dir in valid_dirs:
            self.stdout.write(f'Processing directory: {dir_name} ({image_dir})')
            
            for filename in os.listdir(image_dir):
                if filename.lower().endswith(supported_formats):
                    if not ImageFile.objects.filter(filename=filename).exists():
                        try:
                            file_path = os.path.join(image_dir, filename)
                            with Image.open(file_path) as img:
                                width, height = img.size
                            
                            ImageFile.objects.create(
                                filename=filename,
                                width=width,
                                height=height
                            )
                            loaded_count += 1
                            self.stdout.write(f'Loaded: {filename}')
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'Error loading {filename}: {str(e)}')
                            )
                    else:
                        self.stdout.write(f'Already exists: {filename}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully loaded {loaded_count} new images')
        )
