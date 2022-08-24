# Copyright (c) Alibaba, Inc. and its affiliates.
import os
import shutil
import tempfile
import unittest

from modelscope.metainfo import Trainers
from modelscope.trainers import build_trainer


class TestFinetuneSequenceClassification(unittest.TestCase):

    def setUp(self):
        print(('Testing %s.%s' % (type(self).__name__, self._testMethodName)))
        self.tmp_dir = tempfile.TemporaryDirectory().name
        if not os.path.exists(self.tmp_dir):
            os.makedirs(self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)
        super().tearDown()

    def finetune(self,
                 model_id,
                 train_dataset,
                 eval_dataset,
                 name=Trainers.nlp_base_trainer,
                 cfg_modify_fn=None,
                 **kwargs):
        kwargs = dict(
            model=model_id,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            work_dir=self.tmp_dir,
            cfg_modify_fn=cfg_modify_fn,
            **kwargs)

        os.environ['LOCAL_RANK'] = '0'
        trainer = build_trainer(name=name, default_args=kwargs)
        trainer.train()
        results_files = os.listdir(self.tmp_dir)
        self.assertIn(f'{trainer.timestamp}.log.json', results_files)
        for i in range(10):
            self.assertIn(f'epoch_{i+1}.pth', results_files)

    @unittest.skip
    def test_finetune_afqmc(self):

        def cfg_modify_fn(cfg):
            cfg.task = 'sentence-similarity'
            cfg['preprocessor'] = {'type': 'sen-sim-tokenizer'}
            cfg.train.optimizer.lr = 2e-5
            cfg['dataset'] = {
                'train': {
                    'labels': ['0', '1'],
                    'first_sequence': 'sentence1',
                    'second_sequence': 'sentence2',
                    'label': 'label',
                }
            }
            cfg.train.max_epochs = 10
            cfg.train.lr_scheduler = {
                'type': 'LinearLR',
                'start_factor': 1.0,
                'end_factor': 0.0,
                'total_iters':
                int(len(dataset['train']) / 32) * cfg.train.max_epochs,
                'options': {
                    'by_epoch': False
                }
            }
            cfg.train.hooks = [{
                'type': 'CheckpointHook',
                'interval': 1
            }, {
                'type': 'TextLoggerHook',
                'interval': 1
            }, {
                'type': 'IterTimerHook'
            }, {
                'type': 'EvaluationHook',
                'by_epoch': False,
                'interval': 100
            }]
            return cfg

        from datasets import load_dataset
        from datasets import DownloadConfig
        dc = DownloadConfig()
        dc.local_files_only = True
        dataset = load_dataset('clue', 'afqmc', download_config=dc)
        self.finetune(
            model_id='damo/nlp_structbert_backbone_tiny_std',
            train_dataset=dataset['train'],
            eval_dataset=dataset['validation'],
            cfg_modify_fn=cfg_modify_fn)

    @unittest.skip
    def test_finetune_tnews(self):

        def cfg_modify_fn(cfg):
            # TODO no proper task for tnews
            cfg.task = 'nli'
            cfg['preprocessor'] = {'type': 'nli-tokenizer'}
            cfg.train.optimizer.lr = 2e-5
            cfg['dataset'] = {
                'train': {
                    'labels': [
                        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10',
                        '11', '12', '13', '14'
                    ],
                    'first_sequence':
                    'sentence',
                    'label':
                    'label',
                }
            }
            cfg.train.max_epochs = 5
            cfg.train.lr_scheduler = {
                'type': 'LinearLR',
                'start_factor': 1.0,
                'end_factor': 0.0,
                'total_iters':
                int(len(dataset['train']) / 32) * cfg.train.max_epochs,
                'options': {
                    'by_epoch': False
                }
            }
            cfg.train.hooks = [{
                'type': 'CheckpointHook',
                'interval': 1
            }, {
                'type': 'TextLoggerHook',
                'interval': 1
            }, {
                'type': 'IterTimerHook'
            }, {
                'type': 'EvaluationHook',
                'by_epoch': False,
                'interval': 100
            }]
            return cfg

        from datasets import load_dataset
        from datasets import DownloadConfig
        dc = DownloadConfig()
        dc.local_files_only = True
        dataset = load_dataset('clue', 'tnews', download_config=dc)

        self.finetune(
            model_id='damo/nlp_structbert_backbone_tiny_std',
            train_dataset=dataset['train'],
            eval_dataset=dataset['validation'],
            cfg_modify_fn=cfg_modify_fn)

    @unittest.skip
    def test_veco_xnli(self):
        from datasets import load_dataset
        langs = ['en']
        langs_eval = ['en']
        train_datasets = []
        from datasets import DownloadConfig
        dc = DownloadConfig()
        dc.local_files_only = True
        for lang in langs:
            train_datasets.append(
                load_dataset('xnli', lang, split='train', download_config=dc))
        eval_datasets = []
        for lang in langs_eval:
            eval_datasets.append(
                load_dataset(
                    'xnli', lang, split='validation', download_config=dc))
        train_len = sum([len(dataset) for dataset in train_datasets])
        labels = ['0', '1', '2']

        def cfg_modify_fn(cfg):
            cfg.task = 'nli'
            cfg['preprocessor'] = {'type': 'nli-tokenizer'}
            cfg['dataset'] = {
                'train': {
                    'first_sequence': 'premise',
                    'second_sequence': 'hypothesis',
                    'labels': labels,
                    'label': 'label',
                }
            }
            cfg['train'] = {
                'work_dir':
                '/tmp',
                'max_epochs':
                2,
                'dataloader': {
                    'batch_size_per_gpu': 16,
                    'workers_per_gpu': 1
                },
                'optimizer': {
                    'type': 'AdamW',
                    'lr': 2e-5,
                    'options': {
                        'cumulative_iters': 8,
                    }
                },
                'lr_scheduler': {
                    'type': 'LinearLR',
                    'start_factor': 1.0,
                    'end_factor': 0.0,
                    'total_iters': int(train_len / 16) * 2,
                    'options': {
                        'by_epoch': False
                    }
                },
                'hooks': [{
                    'type': 'CheckpointHook',
                    'interval': 1,
                    'save_dir': '/root'
                }, {
                    'type': 'TextLoggerHook',
                    'interval': 1
                }, {
                    'type': 'IterTimerHook'
                }, {
                    'type': 'EvaluationHook',
                    'by_epoch': False,
                    'interval': 500
                }]
            }
            cfg['evaluation'] = {
                'dataloader': {
                    'batch_size_per_gpu': 128,
                    'workers_per_gpu': 1,
                    'shuffle': False
                }
            }
            return cfg

        self.finetune(
            'damo/nlp_veco_fill-mask-large',
            train_datasets,
            eval_datasets,
            name=Trainers.nlp_veco_trainer,
            cfg_modify_fn=cfg_modify_fn)


if __name__ == '__main__':
    unittest.main()
