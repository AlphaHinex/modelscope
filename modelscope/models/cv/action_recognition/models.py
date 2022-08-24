import torch.nn as nn

from .tada_convnext import TadaConvNeXt


class BaseVideoModel(nn.Module):
    """
    Standard video model.
    The model is divided into the backbone and the head, where the backbone
    extracts features and the head performs classification.

    The backbones can be defined in model/base/backbone.py or anywhere else
    as long as the backbone is registered by the BACKBONE_REGISTRY.
    The heads can be defined in model/module_zoo/heads/ or anywhere else
    as long as the head is registered by the HEAD_REGISTRY.

    The registries automatically finds the registered modules and construct
    the base video model.
    """

    def __init__(self, cfg):
        """
        Args:
            cfg (Config): global config object.
        """
        super(BaseVideoModel, self).__init__()
        # the backbone is created according to meta-architectures
        # defined in models/base/backbone.py
        self.backbone = TadaConvNeXt(cfg)

        # the head is created according to the heads
        # defined in models/module_zoo/heads
        self.head = BaseHead(cfg)

    def forward(self, x):
        x = self.backbone(x)
        x = self.head(x)
        return x


class BaseHead(nn.Module):
    """
    Constructs base head.
    """

    def __init__(
        self,
        cfg,
    ):
        """
        Args:
            cfg (Config): global config object.
        """
        super(BaseHead, self).__init__()
        self.cfg = cfg
        dim = cfg.VIDEO.BACKBONE.NUM_OUT_FEATURES
        num_classes = cfg.VIDEO.HEAD.NUM_CLASSES
        dropout_rate = cfg.VIDEO.HEAD.DROPOUT_RATE
        activation_func = cfg.VIDEO.HEAD.ACTIVATION
        self._construct_head(dim, num_classes, dropout_rate, activation_func)

    def _construct_head(self, dim, num_classes, dropout_rate, activation_func):
        self.global_avg_pool = nn.AdaptiveAvgPool3d(1)

        if dropout_rate > 0.0:
            self.dropout = nn.Dropout(dropout_rate)

        self.out = nn.Linear(dim, num_classes, bias=True)

        if activation_func == 'softmax':
            self.activation = nn.Softmax(dim=-1)
        elif activation_func == 'sigmoid':
            self.activation = nn.Sigmoid()
        else:
            raise NotImplementedError('{} is not supported as an activation'
                                      'function.'.format(activation_func))

    def forward(self, x):
        if len(x.shape) == 5:
            x = self.global_avg_pool(x)
            # (N, C, T, H, W) -> (N, T, H, W, C).
            x = x.permute((0, 2, 3, 4, 1))
        if hasattr(self, 'dropout'):
            out = self.dropout(x)
        else:
            out = x
        out = self.out(out)
        out = self.activation(out)
        out = out.view(out.shape[0], -1)
        return out, x.view(x.shape[0], -1)
