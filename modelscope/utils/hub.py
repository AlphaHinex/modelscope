# Copyright (c) Alibaba, Inc. and its affiliates.

import os
import os.path as osp
from typing import List, Optional, Union

from requests import HTTPError

from modelscope.hub.constants import Licenses, ModelVisibility
from modelscope.hub.file_download import model_file_download
from modelscope.hub.snapshot_download import snapshot_download
from modelscope.utils.config import Config
from modelscope.utils.constant import DEFAULT_MODEL_REVISION, ModelFile
from .logger import get_logger

logger = get_logger(__name__)


def create_model_if_not_exist(
        api,
        model_id: str,
        chinese_name: str,
        visibility: Optional[int] = ModelVisibility.PUBLIC,
        license: Optional[str] = Licenses.APACHE_V2,
        revision: Optional[str] = DEFAULT_MODEL_REVISION):
    exists = True
    try:
        api.get_model(model_id=model_id, revision=revision)
    except HTTPError:
        exists = False
    if exists:
        print(f'model {model_id} already exists, skip creation.')
        return False
    else:
        api.create_model(
            model_id=model_id,
            visibility=visibility,
            license=license,
            chinese_name=chinese_name,
        )
        print(f'model {model_id} successfully created.')
        return True


def read_config(model_id_or_path: str,
                revision: Optional[str] = DEFAULT_MODEL_REVISION):
    """ Read config from hub or local path

    Args:
        model_id_or_path (str): Model repo name or local directory path.
        revision: revision of the model when getting from the hub
    Return:
        config (:obj:`Config`): config object
    """
    if not os.path.exists(model_id_or_path):
        local_path = model_file_download(
            model_id_or_path, ModelFile.CONFIGURATION, revision=revision)
    else:
        local_path = os.path.join(model_id_or_path, ModelFile.CONFIGURATION)

    return Config.from_file(local_path)


def auto_load(model: Union[str, List[str]]):
    if isinstance(model, str):
        if not osp.exists(model):
            model = snapshot_download(model)
    else:
        model = [
            snapshot_download(m) if not osp.exists(m) else m for m in model
        ]

    return model


def get_model_type(model_dir):
    """Get the model type from the configuration.

    This method will try to get the 'model.type' or 'model.model_type' field from the configuration.json file.
    If this file does not exist, the method will try to get the 'model_type' field from the config.json.

    @param model_dir: The local model dir to use.
    @return: The model type string, returns None if nothing is found.
    """
    try:
        configuration_file = osp.join(model_dir, ModelFile.CONFIGURATION)
        config_file = osp.join(model_dir, 'config.json')
        if osp.isfile(configuration_file):
            cfg = Config.from_file(configuration_file)
            return cfg.model.model_type if hasattr(cfg.model, 'model_type') and not hasattr(cfg.model, 'type') \
                else cfg.model.type
        elif osp.isfile(config_file):
            cfg = Config.from_file(config_file)
            return cfg.model_type if hasattr(cfg, 'model_type') else None
    except Exception as e:
        logger.error(f'parse config file failed with error: {e}')


def parse_label_mapping(model_dir):
    """Get the label mapping from the model dir.

    This method will do:
    1. Try to read label-id mapping from the label_mapping.json
    2. Try to read label-id mapping from the configuration.json
    3. Try to read label-id mapping from the config.json

    @param model_dir: The local model dir to use.
    @return: The label2id mapping if found.
    """
    import json
    import os
    label2id = None
    label_path = os.path.join(model_dir, ModelFile.LABEL_MAPPING)
    if os.path.exists(label_path):
        with open(label_path) as f:
            label_mapping = json.load(f)
        label2id = {name: idx for name, idx in label_mapping.items()}

    if label2id is None:
        config_path = os.path.join(model_dir, ModelFile.CONFIGURATION)
        config = Config.from_file(config_path)
        if hasattr(config, 'model') and hasattr(config.model, 'label2id'):
            label2id = config.model.label2id
    if label2id is None:
        config_path = os.path.join(model_dir, 'config.json')
        config = Config.from_file(config_path)
        if hasattr(config, 'label2id'):
            label2id = config.label2id
    return label2id
