# Copyright (c) Alibaba, Inc. and its affiliates.
import unittest

from modelscope.hub.snapshot_download import snapshot_download
from modelscope.models import Model
from modelscope.models.nlp import TransformerCRFForNamedEntityRecognition
from modelscope.pipelines import pipeline
from modelscope.pipelines.nlp import NamedEntityRecognitionPipeline
from modelscope.preprocessors import NERPreprocessor
from modelscope.utils.constant import Tasks
from modelscope.utils.test_utils import test_level


class NamedEntityRecognitionTest(unittest.TestCase):
    model_id = 'damo/nlp_raner_named-entity-recognition_chinese-base-news'
    sentence = '这与温岭市新河镇的一个神秘的传说有关。'

    @unittest.skipUnless(test_level() >= 2, 'skip test in current test level')
    def test_run_by_direct_model_download(self):
        cache_path = snapshot_download(self.model_id)
        tokenizer = NERPreprocessor(cache_path)
        model = TransformerCRFForNamedEntityRecognition(
            cache_path, tokenizer=tokenizer)
        pipeline1 = NamedEntityRecognitionPipeline(
            model, preprocessor=tokenizer)
        pipeline2 = pipeline(
            Tasks.named_entity_recognition,
            model=model,
            preprocessor=tokenizer)
        print(f'sentence: {self.sentence}\n'
              f'pipeline1:{pipeline1(input=self.sentence)}')
        print()
        print(f'pipeline2: {pipeline2(input=self.sentence)}')

    @unittest.skipUnless(test_level() >= 0, 'skip test in current test level')
    def test_run_with_model_from_modelhub(self):
        model = Model.from_pretrained(self.model_id)
        tokenizer = NERPreprocessor(model.model_dir)
        pipeline_ins = pipeline(
            task=Tasks.named_entity_recognition,
            model=model,
            preprocessor=tokenizer)
        print(pipeline_ins(input=self.sentence))

    @unittest.skipUnless(test_level() >= 1, 'skip test in current test level')
    def test_run_with_model_name(self):
        pipeline_ins = pipeline(
            task=Tasks.named_entity_recognition, model=self.model_id)
        print(pipeline_ins(input=self.sentence))

    @unittest.skipUnless(test_level() >= 2, 'skip test in current test level')
    def test_run_with_default_model(self):
        pipeline_ins = pipeline(task=Tasks.named_entity_recognition)
        print(pipeline_ins(input=self.sentence))


if __name__ == '__main__':
    unittest.main()
