"""Shared dependencies and optional feature fallbacks for API views."""

import logging
import os

from django.conf import settings

from ..utils.s3uploader import S3Uploader

logger = logging.getLogger(__name__)

# Keep these values in one place so view modules do not each recreate the same
# configuration and optional-import logic.
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
MEDIA_ROOT = settings.MEDIA_ROOT


def _unavailable_feature(feature_name):
    """Return a callable that explains which optional dependency is missing."""

    def unavailable(*args, **kwargs):
        raise RuntimeError(
            f"{feature_name} is unavailable in the lightweight demo image. "
            "Install backend/requirement.txt for the full media-processing stack."
        )

    return unavailable


def _unavailable_class(feature_name):
    """Return a class that raises a useful error when instantiated."""

    class UnavailableFeature:
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                f"{feature_name} is unavailable in the lightweight demo image. "
                "Install backend/requirement.txt for the full media-processing stack."
            )

    UnavailableFeature.__name__ = feature_name
    return UnavailableFeature


try:
    from moviepy.editor import VideoFileClip
except ImportError:
    VideoFileClip = _unavailable_class("video resolution")


try:
    from ..utils.SEO import EnhancedYouTubeSEOGenerator
except ImportError:
    EnhancedYouTubeSEOGenerator = _unavailable_class("SEO generation")


try:
    from ..utils.Audio.audio import AudioEnhancer
except ImportError:
    AudioEnhancer = _unavailable_class("audio enhancement")


try:
    from ..utils.clips.clips2.main import process_video
except ImportError:
    process_video = _unavailable_feature("clip processing")


try:
    from ..utils.video.video_processing import process_media, process_media_shortform
except ImportError:
    process_media = _unavailable_feature("video upscaling")
    process_media_shortform = _unavailable_feature("short-form video upscaling")


try:
    from ..utils.Captions import DjangoVideoTranscriber
except ImportError:
    DjangoVideoTranscriber = _unavailable_class("caption generation")


__all__ = [
    "AudioEnhancer",
    "DjangoVideoTranscriber",
    "EnhancedYouTubeSEOGenerator",
    "MEDIA_ROOT",
    "S3Uploader",
    "VideoFileClip",
    "YOUTUBE_API_KEY",
    "logger",
    "process_media",
    "process_media_shortform",
    "process_video",
]
