import json
import tempfile
from pathlib import Path

from django.test import TestCase, override_settings
from PIL import Image

from annotator.models import Annotation, ImageFile, Label, Project


class SplitDatasetCocoTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project_root = Path(self.tmp.name)
        self.projects_dir = self.project_root / "projects"
        self.override = override_settings(
            PROJECT_ROOT=self.project_root,
            PROJECTS_DIR=self.projects_dir,
        )
        self.override.enable()
        self.project = Project.objects.create(
            name="project_a",
            folder_name="project_a",
            is_active=True,
            save_path=str(self.projects_dir / "project_a"),
        )
        data_dir = self.projects_dir / "project_a" / "data_collection"
        data_dir.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (100, 50), (255, 255, 255)).save(data_dir / "sample.jpg")
        self.image = ImageFile.objects.create(
            filename="sample.jpg",
            width=100,
            height=50,
            is_annotated=True,
            project=self.project,
        )
        self.label = Label.objects.create(project=self.project, name="part", is_active=True)
        Annotation.objects.create(
            image=self.image,
            label=self.label,
            x_center=0.5,
            y_center=0.5,
            width=0.4,
            height=0.4,
        )

    def tearDown(self):
        self.override.disable()
        self.tmp.cleanup()

    def test_split_dataset_writes_bbox_labels_and_coco_annotations(self):
        response = self.client.post(
            "/annotator/api/split_dataset/",
            data=json.dumps({
                "projectname": "project_a",
                "cropped": "data_collection",
                "split_ratio": 1.0,
                "image_size": 100,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        dataset_dir = self.projects_dir / "project_a" / "annotated" / "data_collection"
        self.assertTrue((dataset_dir / "labels" / "train" / "sample.txt").exists())
        coco_path = dataset_dir / "annotations" / "instances_train.json"
        self.assertTrue(coco_path.exists())
        coco = json.loads(coco_path.read_text(encoding="utf-8"))
        self.assertEqual(coco["images"][0]["file_name"], "sample.jpg")
        self.assertEqual(coco["categories"][0]["name"], "part")
        self.assertEqual(coco["annotations"][0]["bbox"], [30.0, 15.0, 40.0, 20.0])
