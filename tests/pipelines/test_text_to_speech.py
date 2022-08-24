import unittest

# NOTICE: Tensorflow 1.15 seems not so compatible with pytorch.
#         A segmentation fault may be raise by pytorch cpp library
#         if 'import tensorflow' in front of 'import torch'.
#         Puting a 'import torch' here can bypass this incompatibility.
import torch
from scipy.io.wavfile import write

from modelscope.outputs import OutputKeys
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
from modelscope.utils.logger import get_logger
from modelscope.utils.test_utils import test_level

import tensorflow as tf  # isort:skip

logger = get_logger()


class TextToSpeechSambertHifigan16kPipelineTest(unittest.TestCase):

    @unittest.skipUnless(test_level() >= 0, 'skip test in current test level')
    def test_pipeline(self):
        text = '今天北京天气怎么样？'
        model_id = 'damo/speech_sambert-hifigan_tts_zhitian_emo_zh-cn_16k'
        voice = 'zhitian_emo'

        sambert_hifigan_tts = pipeline(
            task=Tasks.text_to_speech, model=model_id)
        self.assertTrue(sambert_hifigan_tts is not None)
        output = sambert_hifigan_tts(input=text, voice=voice)
        self.assertIsNotNone(output[OutputKeys.OUTPUT_PCM])
        pcm = output[OutputKeys.OUTPUT_PCM]
        write('output.wav', 16000, pcm)


if __name__ == '__main__':
    unittest.main()
