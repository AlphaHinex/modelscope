# Copyright (c) Alibaba, Inc. and its affiliates.
from typing import TYPE_CHECKING

from modelscope.utils.import_utils import LazyImportModule

if TYPE_CHECKING:

    from .clip import CLIPForMultiModalEmbedding
    from .gemm import GEMMForMultiModalEmbedding
    from .diffusion import DiffusionForTextToImageSynthesis
    from .mmr import VideoCLIPForMultiModalEmbedding
    from .mplug_for_visual_question_answering import \
        MPlugForVisualQuestionAnswering
    from .ofa_for_all_tasks import OfaForAllTasks
    from .ofa_for_text_to_image_synthesis_model import \
        OfaForTextToImageSynthesis

else:
    _import_structure = {
        'clip': ['CLIPForMultiModalEmbedding'],
        'diffusion': ['DiffusionForTextToImageSynthesis'],
        'gemm': ['GEMMForMultiModalEmbedding'],
        'mmr': ['VideoCLIPForMultiModalEmbedding'],
        'mplug_for_visual_question_answering':
        ['MPlugForVisualQuestionAnswering'],
        'ofa_for_all_tasks': ['OfaForAllTasks'],
        'ofa_for_text_to_image_synthesis_model':
        ['OfaForTextToImageSynthesis']
    }

    import sys

    sys.modules[__name__] = LazyImportModule(
        __name__,
        globals()['__file__'],
        _import_structure,
        module_spec=__spec__,
        extra_objects={},
    )
