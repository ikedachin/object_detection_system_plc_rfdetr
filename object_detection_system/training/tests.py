import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.test import TestCase, override_settings

from annotator.models import Project
from object_detection_system.asgi import application
from training.applications.rfdetr_train import _build_args, _send_new_metric_rows, run_rfdetr_training
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
            'resolution': '320',
            'batch_size': '2',
            'grad_accum_steps': '4',
            'num_workers': '1',
            'accelerator': 'cpu',
            'aug_config': json.dumps({'HorizontalFlip': {'p': 0.5}}),
            'other_params': json.dumps({}),
        }
        data.update(overrides)
        return data

    @patch('training.views.run_rfdetr_training')
    def test_rfdetr_params_are_passed_and_saved(self, mock_run_rfdetr_training):
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
        self.assertEqual(args[:2], ('Roboflow/rf-detr-large', str(self.dataset_yaml)))
        self.assertEqual(kwargs['epochs'], 3)
        self.assertEqual(kwargs['resolution'], 320)
        self.assertEqual(kwargs['batch_size'], 2)
        self.assertEqual(kwargs['grad_accum_steps'], 4)
        self.assertEqual(kwargs['num_workers'], 1)
        self.assertEqual(kwargs['accelerator'], 'cpu')
        self.assertEqual(kwargs['aug_config'], {'HorizontalFlip': {'p': 0.5}})

        training_run = TrainingRun.objects.get(training_name='train_view_test')
        self.assertEqual(training_run.imgsz, '320')
        self.assertEqual(training_run.batch, 2)
        self.assertEqual(training_run.other_params['num_workers'], 1)
        self.assertEqual(training_run.other_params['grad_accum_steps'], 4)
        self.assertEqual(training_run.other_params['aug_config'], {'HorizontalFlip': {'p': 0.5}})

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
                    'num_workers': 2,
                    'lr': 0.0002,
                    'grad_accum_steps': 8,
                    'early_stopping': True,
                }),
                num_workers='3',
                grad_accum_steps='6',
            ),
        )

        self.assertTrue(response.json()['success'])
        _, kwargs = mock_run_rfdetr_training.call_args
        self.assertEqual(kwargs['num_workers'], 3)
        self.assertEqual(kwargs['lr'], 0.0002)
        self.assertEqual(kwargs['grad_accum_steps'], 6)
        self.assertEqual(kwargs['accelerator'], 'cpu')
        self.assertIs(kwargs['early_stopping'], True)

    @patch('training.views.run_rfdetr_training')
    def test_form_fields_override_same_rfdetr_keys_in_other_params(self, mock_run_rfdetr_training):
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
                other_params=json.dumps({'num_workers': 1, 'grad_accum_steps': 9}),
                num_workers='2',
                grad_accum_steps='6',
            ),
        )

        self.assertTrue(response.json()['success'])
        _, kwargs = mock_run_rfdetr_training.call_args
        self.assertEqual(kwargs['num_workers'], 2)
        self.assertEqual(kwargs['grad_accum_steps'], 6)

    @patch('training.views.run_rfdetr_training')
    def test_invalid_aug_config_returns_error_without_training(self, mock_run_rfdetr_training):
        response = self.client.post(
            '/training/',
            data=self.post_data(training_name='invalid_test', aug_config='[]]'),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])
        self.assertIn('aug_config', response.json()['error'])
        mock_run_rfdetr_training.assert_not_called()
        self.assertFalse(TrainingRun.objects.filter(training_name='invalid_test').exists())

    @patch('training.views.run_rfdetr_training')
    def test_unsupported_detail_param_returns_error_without_training(self, mock_run_rfdetr_training):
        response = self.client.post(
            '/training/',
            data=self.post_data(training_name='unsupported_test', other_params=json.dumps({'flipud': 0.5})),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])
        self.assertIn('未対応', response.json()['error'])
        mock_run_rfdetr_training.assert_not_called()
        self.assertFalse(TrainingRun.objects.filter(training_name='unsupported_test').exists())

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


class RfdetrTrainingMetricsTests(TestCase):
    def test_new_metrics_csv_rows_are_sent_to_websocket_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            metrics_path = Path(tmp) / 'metrics.csv'
            metrics_path.write_text(
                'epoch,train/loss_bbox,train/loss_ce,metrics/precision(B),ignored\n'
                '1,0.123456,1.98765,0.81234,text\n'
                '2,0.11111,1.87654,0.9,text\n',
                encoding='utf-8',
            )

            with patch('training.applications.rfdetr_train._send_training_metrics') as mock_send:
                sent_rows = _send_new_metric_rows(metrics_path, total_epochs=5)

        self.assertEqual(sent_rows, 2)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(mock_send.call_args_list[0].args[0], 1)
        self.assertEqual(mock_send.call_args_list[0].args[1], 5)
        self.assertEqual(
            mock_send.call_args_list[0].args[2],
            {
                'train/loss_bbox': 0.1235,
                'train/loss_ce': 1.9876,
                'metrics/precision(B)': 0.8123,
            },
        )

    def test_metrics_csv_sender_skips_already_sent_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            metrics_path = Path(tmp) / 'metrics.csv'
            metrics_path.write_text(
                'epoch,train/loss_bbox\n'
                '1,0.2\n'
                '2,0.1\n',
                encoding='utf-8',
            )

            with patch('training.applications.rfdetr_train._send_training_metrics') as mock_send:
                sent_rows = _send_new_metric_rows(metrics_path, total_epochs=2, sent_rows=1)

        self.assertEqual(sent_rows, 2)
        mock_send.assert_called_once()
        self.assertEqual(mock_send.call_args.args[0], 2)

    async def test_training_metrics_are_delivered_to_rfdetr_websocket(self):
        communicator = WebsocketCommunicator(application, '/ws/rfdetr_training/')
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        try:
            await get_channel_layer().group_send(
                'rfdetr_training',
                {
                    'type': 'send_metrics',
                    'epoch': 2,
                    'total_epochs': 5,
                    'metrics': {
                        'train/loss_bbox': 0.12,
                        'train/loss_ce': 1.23,
                        'metrics/mAP50(B)': 0.66,
                    },
                },
            )
            response = await communicator.receive_json_from(timeout=1)
        finally:
            await communicator.disconnect()

        self.assertEqual(response['epoch'], 2)
        self.assertEqual(response['total_epochs'], 5)
        self.assertEqual(response['metrics']['train/loss_bbox'], 0.12)
        self.assertEqual(response['metrics']['train/loss_ce'], 1.23)
        self.assertEqual(response['metrics']['metrics/mAP50(B)'], 0.66)


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
            resolution=512,
            batch_size=4,
            output_dir=Path('/tmp/output'),
            other_params={
                'num_workers': 2,
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

    def test_run_rfdetr_training_passes_only_rfdetr_kwargs_to_model_train(self):
        captured = {}

        class FakeModel:
            def train(self, **kwargs):
                captured.update(kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            output_dir = project_root / 'output'
            checkpoint = output_dir / 'checkpoint_best_regular.pth'
            detect_yaml = output_dir / 'detect.yaml'
            with override_settings(PROJECT_ROOT=project_root, PROJECTS_DIR=project_root / 'projects'):
                with patch('training.applications.rfdetr_train._read_dataset_yaml') as mock_read_dataset_yaml, \
                     patch('training.applications.rfdetr_train.prepare_rfdetr_dataset') as mock_prepare_dataset, \
                     patch('training.applications.rfdetr_train.create_model', return_value=FakeModel()), \
                     patch('training.applications.rfdetr_train._find_checkpoint', return_value=checkpoint), \
                     patch('training.applications.rfdetr_train._write_detect_yaml', return_value=detect_yaml), \
                     patch('training.applications.rfdetr_train._read_metrics', return_value={}):
                    mock_read_dataset_yaml.return_value = (project_root / 'dataset', ['part'])
                    mock_prepare_dataset.return_value = str(project_root / 'adapted')

                    run_rfdetr_training(
                        'Roboflow/rf-detr-large',
                        str(project_root / 'dataset.yaml'),
                        epochs=5,
                        resolution=640,
                        batch_size=2,
                        device='cpu',
                        save_dir='output',
                        grad_accum_steps=4,
                        num_workers=1,
                        accelerator='cpu',
                        aug_config={'HorizontalFlip': {'p': 0.5}},
                    )

        self.assertEqual(captured['epochs'], 5)
        self.assertEqual(captured['resolution'], 640)
        self.assertEqual(captured['batch_size'], 2)
        self.assertEqual(captured['grad_accum_steps'], 4)
        self.assertEqual(captured['num_workers'], 1)
        self.assertEqual(captured['accelerator'], 'cpu')
        self.assertEqual(captured['aug_config'], {'HorizontalFlip': {'p': 0.5}})
        for yolo_key in ('imgsz', 'batch', 'workers', 'flipud', 'fliplr', 'mixup', 'perspective', 'shear', 'scale'):
            self.assertNotIn(yolo_key, captured)

    def test_run_rfdetr_training_rejects_unknown_train_params(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            with override_settings(PROJECT_ROOT=project_root, PROJECTS_DIR=project_root / 'projects'):
                with patch('training.applications.rfdetr_train._read_dataset_yaml', return_value=(project_root / 'dataset', ['part'])), \
                     patch('training.applications.rfdetr_train.prepare_rfdetr_dataset', return_value=str(project_root / 'adapted')), \
                     patch('training.applications.rfdetr_train.create_model'):
                    with self.assertRaisesMessage(ValueError, 'unsupported'):
                        run_rfdetr_training(
                            'Roboflow/rf-detr-large',
                            str(project_root / 'dataset.yaml'),
                            epochs=5,
                            resolution=640,
                            batch_size=2,
                            device='cpu',
                            save_dir='output',
                            flipud=0.5,
                        )
