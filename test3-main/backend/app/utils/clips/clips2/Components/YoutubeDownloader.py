import os
import re
import yt_dlp
import unicodedata
from django.conf import settings  # Make sure this is available if running inside Django

def sanitize_filename(filename):
    """Remove invalid characters for filenames and strip emojis."""
    # Remove emojis and other non-printable characters
    filename = ''.join(c for c in filename if not unicodedata.category(c).startswith('So'))
    # Remove invalid characters for filenames
    return re.sub(r'[\\/*?:"<>|]', "_", filename)

def download_youtube_video(url, media_root=None):
    try:
        if not media_root:
            media_root = settings.MEDIA_ROOT  # Use Django's media root

        video_folder = os.path.join(media_root, "videos")
        os.makedirs(video_folder, exist_ok=True)

        # Get video ID without downloading
        ydl_info_opts = {
            'quiet': True,
            'skip_download': True,
        }

        # Include cookies if available
        if hasattr(settings, 'YOUTUBE_COOKIES_FILE') and os.path.exists(settings.YOUTUBE_COOKIES_FILE):
            ydl_info_opts['cookiefile'] = settings.YOUTUBE_COOKIES_FILE

        with yt_dlp.YoutubeDL(ydl_info_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)

        video_id = info_dict['id']
        output_file = os.path.join(video_folder, f"{video_id}.mp4")

        # Check if file already exists
        if os.path.exists(output_file):
            print(f"Video {video_id} already exists at {output_file}. Skipping download.")
            return os.path.abspath(output_file)

        # yt-dlp download options
        ydl_opts = {
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]',
            'outtmpl': output_file,
            'merge_output_format': 'mp4',
            'quiet': False,
        }

        if hasattr(settings, 'YOUTUBE_COOKIES_FILE') and os.path.exists(settings.YOUTUBE_COOKIES_FILE):
            ydl_opts['cookiefile'] = settings.YOUTUBE_COOKIES_FILE

        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return os.path.abspath(output_file)

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print("Please ensure yt-dlp is installed and up to date:")
        print("pip install --upgrade yt-dlp")
        return None

# Optional for CLI usage (will fail if settings are not available outside Django)
if __name__ == "__main__":
    youtube_url = input("Enter YouTube video URL: ")
    downloaded_file_path = download_youtube_video(youtube_url)
    print(f"Downloaded video file: {downloaded_file_path}")
