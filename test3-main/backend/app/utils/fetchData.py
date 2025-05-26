import yt_dlp
import json
import os
from django.conf import settings  # Ensure Django settings is imported

def fetch_video_metadata(url):
    ydl_opts = {
        'quiet': True,
        'forcejson': True,
    }

    # Add cookies file from settings if it exists
    if hasattr(settings, 'YOUTUBE_COOKIES_FILE') and os.path.exists(settings.YOUTUBE_COOKIES_FILE):
        ydl_opts['cookiefile'] = settings.YOUTUBE_COOKIES_FILE

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Fetch the video metadata
            info_dict = ydl.extract_info(url, download=False)

            # Extract the title, description, and tags
            video_metadata = {
                'title': info_dict.get('title', 'N/A'),
                'description': info_dict.get('description', 'N/A').strip(),
                'tags': [
                    tag.replace('\r', '').replace('\n', '').strip()
                    for tag in info_dict.get('tags', [])
                    if tag.strip()
                ]
            }

            return video_metadata
    except Exception as e:
        print(f"Error fetching video metadata: {str(e)}")
        return
