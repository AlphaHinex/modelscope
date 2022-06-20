import os
from typing import Any, Dict

import json
import numpy as np
import torch
from sofa import SbertModel
from sofa.models.sbert.modeling_sbert import SbertPreTrainedModel
from torch import nn

from modelscope.utils.constant import Tasks
from ..base import Model, Tensor
from ..builder import MODELS

__all__ = ['SbertForSentenceSimilarity']


class SbertTextClassifier(SbertPreTrainedModel):

    def __init__(self, config):
        super().__init__(config)
        self.num_labels = config.num_labels
        self.config = config
        self.encoder = SbertModel(config, add_pooling_layer=True)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)
        self.classifier = nn.Linear(config.hidden_size, config.num_labels)

    def forward(self, input_ids=None, token_type_ids=None):
        outputs = self.encoder(
            input_ids,
            token_type_ids=token_type_ids,
            return_dict=None,
        )
        pooled_output = outputs[1]
        pooled_output = self.dropout(pooled_output)
        logits = self.classifier(pooled_output)
        return logits


@MODELS.register_module(
    Tasks.sentence_similarity,
    module_name=r'sbert-base-chinese-sentence-similarity')
class SbertForSentenceSimilarity(Model):

    def __init__(self, model_dir: str, *args, **kwargs):
        """initialize the sentence similarity model from the `model_dir` path.

        Args:
            model_dir (str): the model path.
            model_cls (Optional[Any], optional): model loader, if None, use the
                default loader to load model weights, by default None.
        """
        super().__init__(model_dir, *args, **kwargs)
        self.model_dir = model_dir

        self.model = SbertTextClassifier.from_pretrained(
            model_dir, num_labels=2)
        self.model.eval()
        self.label_path = os.path.join(self.model_dir, 'label_mapping.json')
        with open(self.label_path) as f:
            self.label_mapping = json.load(f)
        self.id2label = {idx: name for name, idx in self.label_mapping.items()}

    def forward(self, input: Dict[str, Any]) -> Dict[str, np.ndarray]:
        """return the result by the model

        Args:
            input (Dict[str, Any]): the preprocessed data

        Returns:
            Dict[str, np.ndarray]: results
                Example:
                    {
                        'predictions': array([1]), # lable 0-negative 1-positive
                        'probabilities': array([[0.11491239, 0.8850876 ]], dtype=float32),
                        'logits': array([[-0.53860897,  1.5029076 ]], dtype=float32) # true value
                    }
        """
        input_ids = torch.tensor(input['input_ids'], dtype=torch.long)
        token_type_ids = torch.tensor(
            input['token_type_ids'], dtype=torch.long)
        with torch.no_grad():
            logits = self.model(input_ids, token_type_ids)
        probs = logits.softmax(-1).numpy()
        pred = logits.argmax(-1).numpy()
        logits = logits.numpy()
        res = {'predictions': pred, 'probabilities': probs, 'logits': logits}
        return res
