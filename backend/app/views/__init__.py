"""Compatibility facade for the API view handlers.

The URL configuration historically imported ``app.views`` directly. Keeping
these re-exports makes that public application contract stable while the
implementations live in focused modules.
"""

from .auth import google_login
from .csrf import csrf_token
from .processing import (
    check_resolution,
    extract_youtube_id,
    get_video_duration_ffprobe,
    get_video_duration_yt_dlp,
    get_video_resolution,
    optimize_shortform,
    process_short_form_video,
    seo,
)
from .reports import generate_report
from .videos import (
    create_cookies_from_browser,
    download_video,
    extract_video_id,
    fetch_data,
    fetch_video_data,
    get_video,
    sanitize_filename,
    upload_video,
)
from .youtube import (
    authorize_youtube,
    check_auth,
    cleanup_temporary_file,
    get_youtube_auth_url,
    update_youtube_seo,
    upload_youtube_video,
    youtube_callback,
)

__all__ = [
    "authorize_youtube",
    "check_auth",
    "check_resolution",
    "cleanup_temporary_file",
    "create_cookies_from_browser",
    "csrf_token",
    "download_video",
    "extract_video_id",
    "extract_youtube_id",
    "fetch_data",
    "fetch_video_data",
    "generate_report",
    "get_video",
    "get_video_duration_ffprobe",
    "get_video_duration_yt_dlp",
    "get_video_resolution",
    "get_youtube_auth_url",
    "google_login",
    "optimize_shortform",
    "process_short_form_video",
    "sanitize_filename",
    "seo",
    "update_youtube_seo",
    "upload_video",
    "upload_youtube_video",
    "youtube_callback",
]
