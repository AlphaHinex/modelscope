import math
import os
import random

import decord
import numpy as np
import torch
import torch.nn as nn
import torch.utils.data
import torch.utils.dlpack as dlpack
import torchvision.transforms._transforms_video as transforms
from decord import VideoReader
from torchvision.transforms import Compose


def ReadVideoData(cfg, video_path):
    """ simple interface to load video frames from file

    Args:
        cfg (Config): The global config object.
        video_path (str): video file path
    """
    data = _decode_video(cfg, video_path)
    transform = kinetics400_tranform(cfg)
    data_list = []
    for i in range(data.size(0)):
        for j in range(cfg.TEST.NUM_SPATIAL_CROPS):
            transform.transforms[1].set_spatial_index(j)
            data_list.append(transform(data[i]))
    return torch.stack(data_list, dim=0)


def kinetics400_tranform(cfg):
    """
    Configs the transform for the kinetics-400 dataset.
    We apply controlled spatial cropping and normalization.
    Args:
        cfg (Config): The global config object.
    """
    resize_video = KineticsResizedCrop(
        short_side_range=[cfg.DATA.TEST_SCALE, cfg.DATA.TEST_SCALE],
        crop_size=cfg.DATA.TEST_CROP_SIZE,
        num_spatial_crops=cfg.TEST.NUM_SPATIAL_CROPS)
    std_transform_list = [
        transforms.ToTensorVideo(), resize_video,
        transforms.NormalizeVideo(
            mean=cfg.DATA.MEAN, std=cfg.DATA.STD, inplace=True)
    ]
    return Compose(std_transform_list)


def _interval_based_sampling(vid_length, vid_fps, target_fps, clip_idx,
                             num_clips, num_frames, interval, minus_interval):
    """
        Generates the frame index list using interval based sampling.
        Args:
            vid_length  (int): the length of the whole video (valid selection range).
            vid_fps     (int): the original video fps
            target_fps  (int): the normalized video fps
            clip_idx    (int): -1 for random temporal sampling, and positive values for
                                sampling specific clip from the video
            num_clips   (int): the total clips to be sampled from each video.
                                combined with clip_idx, the sampled video is the "clip_idx-th"
                                 video from "num_clips" videos.
            num_frames  (int): number of frames in each sampled clips.
            interval    (int): the interval to sample each frame.
            minus_interval (bool): control the end index
        Returns:
            index (tensor): the sampled frame indexes
        """
    if num_frames == 1:
        index = [random.randint(0, vid_length - 1)]
    else:
        # transform FPS
        clip_length = num_frames * interval * vid_fps / target_fps

        max_idx = max(vid_length - clip_length, 0)
        start_idx = clip_idx * math.floor(max_idx / (num_clips - 1))
        if minus_interval:
            end_idx = start_idx + clip_length - interval
        else:
            end_idx = start_idx + clip_length - 1

        index = torch.linspace(start_idx, end_idx, num_frames)
        index = torch.clamp(index, 0, vid_length - 1).long()

    return index


def _decode_video_frames_list(cfg, frames_list, vid_fps):
    """
        Decodes the video given the numpy frames.
        Args:
            cfg          (Config): The global config object.
            frames_list  (list):  all frames for a video, the frames should be numpy array.
            vid_fps      (int):  the fps of this video.
        Returns:
            frames            (Tensor): video tensor data
    """
    assert isinstance(frames_list, list)
    num_clips_per_video = cfg.TEST.NUM_ENSEMBLE_VIEWS

    frame_list = []
    for clip_idx in range(num_clips_per_video):
        # for each clip in the video,
        # a list is generated before decoding the specified frames from the video
        list_ = _interval_based_sampling(
            len(frames_list), vid_fps, cfg.DATA.TARGET_FPS, clip_idx,
            num_clips_per_video, cfg.DATA.NUM_INPUT_FRAMES,
            cfg.DATA.SAMPLING_RATE, cfg.DATA.MINUS_INTERVAL)
        frames = None
        frames = torch.from_numpy(
            np.stack([frames_list[l_index] for l_index in list_.tolist()],
                     axis=0))
        frame_list.append(frames)
    frames = torch.stack(frame_list)
    if num_clips_per_video == 1:
        frames = frames.squeeze(0)

    return frames


def _decode_video(cfg, path):
    """
        Decodes the video given the numpy frames.
        Args:
            path          (str): video file path.
        Returns:
            frames            (Tensor): video tensor data
    """
    vr = VideoReader(path)

    num_clips_per_video = cfg.TEST.NUM_ENSEMBLE_VIEWS

    frame_list = []
    for clip_idx in range(num_clips_per_video):
        # for each clip in the video,
        # a list is generated before decoding the specified frames from the video
        list_ = _interval_based_sampling(
            len(vr), vr.get_avg_fps(), cfg.DATA.TARGET_FPS, clip_idx,
            num_clips_per_video, cfg.DATA.NUM_INPUT_FRAMES,
            cfg.DATA.SAMPLING_RATE, cfg.DATA.MINUS_INTERVAL)
        frames = None
        if path.endswith('.avi'):
            append_list = torch.arange(0, list_[0], 4)
            frames = dlpack.from_dlpack(
                vr.get_batch(torch.cat([append_list,
                                        list_])).to_dlpack()).clone()
            frames = frames[append_list.shape[0]:]
        else:
            frames = dlpack.from_dlpack(
                vr.get_batch(list_).to_dlpack()).clone()
        frame_list.append(frames)
    frames = torch.stack(frame_list)
    if num_clips_per_video == 1:
        frames = frames.squeeze(0)
    del vr
    return frames


class KineticsResizedCrop(object):
    """Perform resize and crop for kinetics-400 dataset
    Args:
        short_side_range (list): The length of short side range. In inference, this shoudle be [256, 256]
        crop_size         (int): The cropped size for frames.
        num_spatial_crops (int): The number of the cropped spatial regions in each video.
    """

    def __init__(
        self,
        short_side_range,
        crop_size,
        num_spatial_crops=1,
    ):
        self.idx = -1
        self.short_side_range = short_side_range
        self.crop_size = int(crop_size)
        self.num_spatial_crops = num_spatial_crops

    def _get_controlled_crop(self, clip):
        """Perform controlled crop for video tensor.
        Args:
            clip (Tensor): the video data, the shape is [T, C, H, W]
        """
        _, _, clip_height, clip_width = clip.shape

        length = self.short_side_range[0]

        if clip_height < clip_width:
            new_clip_height = int(length)
            new_clip_width = int(clip_width / clip_height * new_clip_height)
            new_clip = torch.nn.functional.interpolate(
                clip, size=(new_clip_height, new_clip_width), mode='bilinear')
        else:
            new_clip_width = int(length)
            new_clip_height = int(clip_height / clip_width * new_clip_width)
            new_clip = torch.nn.functional.interpolate(
                clip, size=(new_clip_height, new_clip_width), mode='bilinear')
        x_max = int(new_clip_width - self.crop_size)
        y_max = int(new_clip_height - self.crop_size)
        if self.num_spatial_crops == 1:
            x = x_max // 2
            y = y_max // 2
        elif self.num_spatial_crops == 3:
            if self.idx == 0:
                if new_clip_width == length:
                    x = x_max // 2
                    y = 0
                elif new_clip_height == length:
                    x = 0
                    y = y_max // 2
            elif self.idx == 1:
                x = x_max // 2
                y = y_max // 2
            elif self.idx == 2:
                if new_clip_width == length:
                    x = x_max // 2
                    y = y_max
                elif new_clip_height == length:
                    x = x_max
                    y = y_max // 2
        return new_clip[:, :, y:y + self.crop_size, x:x + self.crop_size]

    def set_spatial_index(self, idx):
        """Set the spatial cropping index for controlled cropping..
        Args:
            idx (int): the spatial index. The value should be in [0, 1, 2], means [left, center, right], respectively.
        """
        self.idx = idx

    def __call__(self, clip):
        return self._get_controlled_crop(clip)
