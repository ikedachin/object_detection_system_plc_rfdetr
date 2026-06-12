import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings

from annotator.models import Project
from training.applications.rfdetr_train import _build_args
from training.applications.rfdetr_native import training_kwargs_from_args
from training.models import TrainingRun


class TrainViewParameterTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project_root = Path(self.tmp.name)
        self.override = override_settings(
            PROJECT_ROOT=self.project_root,
            PROJECTS_DIR=self.project_root / 'projects',
        )
        self.override.enable()
        self.project = Project.objects.create(
            name='test_project',
            folder_name='test_project',
            save_path=str(settings.PROJECTS_DIR / 'test_project'),
        )
        self.dataset_yaml = (
            settings.PROJECT_ROOT
            / 'projects'
            / self.project.folder_name
            / 'annotated'
            / 'data_collection'
            / 'data.yaml'
        )
        self.dataset_yaml.parent.mkdir(parents=True, exist_ok=True)
        self.dataset_yaml.write_text(
            f"path: {self.dataset_yaml.parent}\ntrain: images/train\nval: images/valid\nnames:\n  0: part\n",
            encoding='utf-8',
        )
        self.best_model_path = (
            settings.PROJECT_ROOT
            / 'projects'
            / self.project.folder_name
            / 'models'
            / 'train_view_test'
            / 'checkpoint_best_regular.pth'
        )
        self.config_yaml_path = self.best_model_path.with_name('detect.yaml')

    def tearDown(self):
        self.override.disable()
        self.tmp.cleanup()

    def post_data(self, **overrides):
        data = {
            'project_id': str(self.project.id),
            'training_name': 'train_view_test',
            'data_type': 'data_collection',
            'dataset_yaml_fullpath': str(self.dataset_yaml),
            'model_name': 'Roboflow/rf-detr-large',
            'epochs': '3',
            'imgsz': '320',
            'batch': '2',
            'flipud': '0.2',
            'fliplr': '0.1',
            'mixup': '0.3',
            'perspective': '0.4',
            'shear': '0.5',
            'scale': '0.6',
            'other_params': json.dumps({'workers': 1}),
        }
        data.update(overrides)
        return data

    @patch('training.views.run_rfdetr_training')
    def test_augmentation_params_are_passed_and_saved(self, mock_run_rfdetr_training):
        mock_run_rfdetr_training.return_value = (
            {'metrics/mAP50(B)': '0.9000'},
            str(self.best_model_path),
            str(self.config_yaml_path),
            {},
        )

        response = self.client.post('/training/', data=self.post_data())

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        mock_run_rfdetr_training.assert_called_once()
        args, kwargs = mock_run_rfdetr_training.call_args
        self.assertEqual(args[:5], ('Roboflow/rf-detr-large', str(self.dataset_yaml), 3, '320', 2))
        self.assertEqual(kwargs['workers'], 1)
        self.assertEqual(kwargs['flipud'], 0.2)
        self.assertEqual(kwargs['fliplr'], 0.1)
        self.assertEqual(kwargs['mixup'], 0.3)
        self.assertEqual(kwargs['perspective'], 0.4)
        self.assertEqual(kwargs['shear'], 0.5)
        self.assertEqual(kwargs['scale'], 0.6)

        training_run = TrainingRun.objects.get(training_name='train_view_test')
        self.assertEqual(training_run.flipud, 0.2)
        self.assertEqual(training_run.fliplr, 0.1)
        self.assertEqual(training_run.mixup, 0.3)
        self.assertEqual(training_run.perspective, 0.4)
        self.assertEqual(training_run.shear, 0.5)
        self.assertEqual(training_run.scale, 0.6)
        self.assertEqual(training_run.other_params['workers'], 1)
        self.assertEqual(training_run.other_params['flipud'], 0.2)

    @patch('training.views.run_rfdetr_training')
    def test_other_params_are_passed_to_training(self, mock_run_rfdetr_training):
        mock_run_rfdetr_training.return_value = (
            {},
            str(self.best_model_path),
            str(self.config_yaml_path),
            {},
        )

        response = self.client.post(
            '/training/',
            data=self.post_data(
                training_name='detail_params_test',
                other_params=json.dumps({
                    'workers': 2,
                    'lr': 0.0002,
                    'grad_accum_steps': 8,
                    'accelerator': 'cpu',
                    'early_stopping': True,
                }),
            ),
        )

        self.assertTrue(response.json()['success'])
        _, kwargs = mock_run_rfdetr_training.call_args
        self.assertEqual(kwargs['workers'], 2)
        self.assertEqual(kwargs['lr'], 0.0002)
        self.assertEqual(kwargs['grad_accum_steps'], 8)
        self.assertEqual(kwargs['accelerator'], 'cpu')
        self.assertIs(kwargs['early_stopping'], True)

    @patch('training.views.run_rfdetr_training')
    def test_form_fields_override_same_keys_in_other_params(self, mock_run_rfdetr_training):
        mock_run_rfdetr_training.return_value = (
            {},
            str(self.best_model_path),
            str(self.config_yaml_path),
            {},
        )

        response = self.client.post(
            '/training/',
            data=self.post_data(
                training_name='override_test',
                other_params=json.dumps({'workers': 1, 'flipud': 0.9, 'scale': 0.9}),
                flipud='0.2',
                scale='0.6',
            ),
        )

        self.assertTrue(response.json()['success'])
        _, kwargs = mock_run_rfdetr_training.call_args
        self.assertEqual(kwargs['workers'], 1)
        self.assertEqual(kwargs['flipud'], 0.2)
        self.assertEqual(kwargs['scale'], 0.6)

    @patch('training.views.run_rfdetr_training')
    def test_invalid_augmentation_param_returns_error_without_training(self, mock_run_rfdetr_training):
        response = self.client.post(
            '/training/',
            data=self.post_data(training_name='invalid_test', flipud='1.1'),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])
        self.assertIn('flipud', response.json()['error'])
        mock_run_rfdetr_training.assert_not_called()
        self.assertFalse(TrainingRun.objects.filter(training_name='invalid_test').exists())

    @patch('training.views.run_rfdetr_training')
    def test_empty_augmentation_param_returns_error_without_training(self, mock_run_rfdetr_training):
        response = self.client.post(
            '/training/',
            data=self.post_data(training_name='empty_test', mixup=''),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])
        self.assertIn('mixup', response.json()['error'])
        mock_run_rfdetr_training.assert_not_called()
        self.assertFalse(TrainingRun.objects.filter(training_name='empty_test').exists())

    @patch('training.views.run_rfdetr_training')
    def test_blank_training_name_is_generated_from_project(self, mock_run_rfdetr_training):
        generated_model_path = (
            settings.PROJECT_ROOT
            / 'projects'
            / self.project.folder_name
            / 'models'
            / 'generated'
            / 'checkpoint_best_regular.pth'
        )
        mock_run_rfdetr_training.return_value = (
            {},
            str(generated_model_path),
            str(generated_model_path.with_name('detect.yaml')),
            {},
        )

        response = self.client.post('/training/', data=self.post_data(training_name=''))

        self.assertTrue(response.json()['success'])
        training_run = TrainingRun.objects.get()
        self.assertRegex(training_run.training_name, r'^test_project_\d{8}_\d{6}$')

    @patch('training.views.run_rfdetr_training')
    def test_invalid_other_params_returns_error_without_training(self, mock_run_rfdetr_training):
        response = self.client.post(
            '/training/',
            data=self.post_data(training_name='invalid_json_test', other_params='[]'),
        )

        self.assertFalse(response.json()['success'])
        self.assertIn('詳細パラメータ', response.json()['error'])
        mock_run_rfdetr_training.assert_not_called()


class TrainingProjectYamlSelectionTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project_root = Path(self.tmp.name)
        self.override = override_settings(
            PROJECT_ROOT=self.project_root,
            PROJECTS_DIR=self.project_root / 'projects',
        )
        self.override.enable()
        self.project_without_yaml = Project.objects.create(
            name='no_yaml_project',
            folder_name='no_yaml_folder',
            is_active=True,
        )
        self.project_with_yaml = Project.objects.create(
            name='display_name_project',
            folder_name='actual_folder',
        )
        self.yaml_path = (
            settings.PROJECTS_DIR
            / self.project_with_yaml.folder_name
            / 'annotated'
            / 'data_collection'
            / 'dataset.yaml'
        )
        self.yaml_path.parent.mkdir(parents=True, exist_ok=True)
        self.yaml_path.write_text(
            f"path: {self.yaml_path.parent}\ntrain: images/train\nval: images/valid\nnames:\n  0: part\n",
            encoding='utf-8',
        )

    def tearDown(self):
        self.override.disable()
        self.tmp.cleanup()

    def test_training_page_lists_projects_even_without_yaml(self):
        response = self.client.get('/training/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'no_yaml_project')
        self.assertContains(response, 'display_name_project')

    def test_dataset_yaml_api_resolves_project_by_name_folder_or_id(self):
        for project_value in (
            self.project_with_yaml.name,
            self.project_with_yaml.folder_name,
            str(self.project_with_yaml.id),
        ):
            response = self.client.get(
                '/training/',
                {'project_name': project_value, 'data_type': 'data_collection'},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['yamls'][0]['name'], 'dataset.yaml')


class RfdetrTrainingArgumentTests(TestCase):
    def test_detail_params_are_mapped_to_rfdetr_train_kwargs(self):
        args = _build_args(
            model_name='Roboflow/rf-detr-large',
            dataset_root=Path('/tmp/dataset'),
            class_names=['part'],
            epochs=7,
            imgsz='512',
            batch=4,
            output_dir=Path('/tmp/output'),
            other_params={
                'workers': 2,
                'lr': 0.0002,
                'grad_accum_steps': 8,
                'accelerator': 'cpu',
                'early_stopping': True,
                'aug_config': {'HorizontalFlip': {'p': 0.5}},
            },
        )
        args.dataset_dir = '/tmp/adapted'

        kwargs = training_kwargs_from_args(args)

        self.assertEqual(kwargs['dataset_dir'], '/tmp/adapted')
        self.assertEqual(kwargs['epochs'], 7)
        self.assertEqual(kwargs['batch_size'], 4)
        self.assertEqual(kwargs['resolution'], 512)
        self.assertEqual(kwargs['num_workers'], 2)
        self.assertEqual(kwargs['lr'], 0.0002)
        self.assertEqual(kwargs['grad_accum_steps'], 8)
        self.assertEqual(kwargs['accelerator'], 'cpu')
        self.assertIs(kwargs['early_stopping'], True)
        self.assertEqual(kwargs['aug_config'], {'HorizontalFlip': {'p': 0.5}})
