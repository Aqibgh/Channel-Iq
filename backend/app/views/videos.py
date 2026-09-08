"""Video metadata, transfer, and storage API handlers."""

import json
import os
import re
from urllib.parse import parse_qs, urlparse

import boto3
import yt_dlp
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from ..utils.fetchData import fetch_video_metadata
from .common import YOUTUBE_API_KEY, S3Uploader, logger


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def fetch_data(request):
    if request.method == "POST":
        try:
            # Parse the JSON body
            data = json.loads(request.body)
            video_url = data.get("videoURL")

            # Validate the video URL
            if not video_url:
                return JsonResponse({"error": "No video URL provided"}, status=400)

            try:
                # Call the fetch_video_metadata function directly
                video_metadata = fetch_video_metadata(video_url)

                if video_metadata:
                    return JsonResponse({
                        "message": "Video metadata fetched successfully",
                        "data": video_metadata
                    })
                else:
                    return JsonResponse({"error": "Failed to fetch video metadata"}, status=500)

            except Exception as e:
                logger.error(f"Error in fetch_video_metadata: {str(e)}")
                return JsonResponse({"error": "Error fetching video metadata", "details": str(e)}, status=500)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request body: {str(e)}")
            return JsonResponse({
                "error": "Invalid JSON in request body",
                "details": str(e)
            }, status=400)

        except Exception as e:
            logger.error(f"Unexpected error in fetch_data: {str(e)}")
            return JsonResponse({
                "error": "Internal server error",
                "details": str(e)
            }, status=500)

    return JsonResponse({
        "error": "Only POST method is allowed"
    }, status=405)


def extract_video_id(video_url):
    try:
        parsed_url = urlparse(video_url)
        if parsed_url.netloc in ["www.youtube.com", "youtube.com"]:
            query_params = parse_qs(parsed_url.query)
            return query_params.get("v", [None])[0]
        elif parsed_url.netloc == "youtu.be":
            return parsed_url.path.strip("/")
        return None
    except Exception as e:
        logger.error(f"Error extracting video ID: {e}")
        return None


def upload_video(request):
    if request.method == 'POST' and request.FILES['video']:
        video = request.FILES['video']
        fs = FileSystemStorage(location=settings.MEDIA_ROOT)
        filename = fs.save(video.name, video)
        file_url = fs.url(filename)
        return JsonResponse({'file_url': file_url})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def fetch_video_data(request):
    video_url = request.GET.get("url")
    if not video_url:
        return JsonResponse({"error": "No URL provided"}, status=400)

    video_id = extract_video_id(video_url)
    if not video_id:
        return JsonResponse({"error": "Invalid YouTube URL"}, status=400)

    if not YOUTUBE_API_KEY:
        return JsonResponse({"error": "YouTube API is not configured"}, status=503)

    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        response = youtube.videos().list(part="snippet", id=video_id).execute()

        if "items" not in response or not response["items"]:
            return JsonResponse({"error": "Video not found"}, status=404)

        video_data = response["items"][0]["snippet"]
        return JsonResponse({
            "title": video_data["title"],
            "thumbnail": video_data["thumbnails"]["high"]["url"],
        })

    except HttpError as e:
        logger.error(f"Error fetching video metadata: {e}")
        return JsonResponse({"error": f"Error fetching video metadata: {e}"}, status=500)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return JsonResponse({"error": f"An unexpected error occurred: {e}"}, status=500)


def sanitize_filename(filename):
    # Remove any characters that are not allowed in filenames
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)  # Remove invalid characters
    return filename


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def download_video(request):
    # Extract video URL from the request
    if request.method == "POST":
        video_url = request.POST.get("url")
    else:
        video_url = request.GET.get("url")

    # Validate the video URL
    if not video_url:
        return JsonResponse({"error": "No URL provided"}, status=400)

    # Extract video ID from the URL
    video_id = extract_video_id(video_url)
    if not video_id:
        return JsonResponse({"error": "Invalid YouTube URL"}, status=400)

    # Enhanced yt-dlp options to avoid bot detection
    def get_ydl_opts(download=False, output_path=None):
        opts = {
            'quiet': True,
            'no_warnings': True,
            'logger': logger,
            # User agent and headers to appear more like a regular browser
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip,deflate',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                'Keep-Alive': '300',
                'Connection': 'keep-alive',
            },
            # Additional options to avoid detection
            'sleep_interval': 1,
            'max_sleep_interval': 3,
            'sleep_interval_requests': 1,
            'extractor_retries': 3,
            'retries': 3,
        }


        if os.path.exists(settings.YOUTUBE_COOKIES_FILE):
            opts['cookiefile'] = settings.YOUTUBE_COOKIES_FILE

        if not download:
            opts['skip_download'] = True
        else:
            opts.update({
                'format': 'bv*[height<=1080]+ba/b[height<=1080]',
                'merge_output_format': 'mp4',
                'outtmpl': output_path,
                'quiet': False,
            })

        return opts

    # Check video duration before downloading
    try:
        ydl_info_opts = get_ydl_opts(download=False)

        with yt_dlp.YoutubeDL(ydl_info_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

            # Get duration in seconds
            duration = info.get('duration', 0)

            # Check if video is between 5 minutes and 1 hour
            min_duration = 0.5 * 60  # 5 minutes in seconds
            max_duration = 60 * 60  # 1 hour in seconds

            if duration < min_duration:
                return JsonResponse({
                    "error": "VIDEO_TOO_SHORT",
                    "message": "Video must be longer than 5 minutes"
                }, status=400)

            if duration > max_duration:
                return JsonResponse({
                    "error": "VIDEO_TOO_LONG",
                    "message": "Video must be shorter than 1 hour"
                }, status=400)

    except yt_dlp.utils.DownloadError as e:
        error_message = str(e)
        if "Sign in to confirm you're not a bot" in error_message:
            return JsonResponse({
                "error": "AUTHENTICATION_REQUIRED",
                "message": "YouTube requires authentication. Please contact administrator to set up cookies.",
                "details": "Bot detection triggered - cookies or browser authentication needed"
            }, status=403)
        else:
            logger.error(f"Info extraction failed: {error_message}")
            return JsonResponse({"error": f"Could not validate video duration: {error_message}"}, status=500)
    except Exception as e:
        logger.exception("Unexpected error during video validation")
        return JsonResponse({"error": f"Validation error: {str(e)}"}, status=500)

    # Define the local save path using MEDIA_ROOT
    sanitized_filename = sanitize_filename(f"{video_id}.mp4")
    local_file_path = os.path.join(settings.MEDIA_ROOT, "videos", sanitized_filename)

    # Ensure the videos directory exists
    os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

    # Check if the file already exists locally
    if os.path.exists(local_file_path):
        logger.debug(f"Video already exists locally: {local_file_path}")

        # Check if it also exists in S3
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        s3_key = f"videos/{video_id}.mp4"

        try:
            # Check if file exists in S3 bucket
            s3_client.head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=s3_key)
            video_url_s3 = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
            return JsonResponse({
                "message": "Video already exists.",
                "url": video_url_s3,
                "local_path": local_file_path
            })
        except s3_client.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                # File exists locally but not in S3, upload it
                try:
                    logger.debug(f"Uploading existing local file to S3")
                    s3_client.upload_file(local_file_path, settings.AWS_STORAGE_BUCKET_NAME, s3_key)
                    video_url_s3 = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
                    return JsonResponse({
                        "message": "Existing video uploaded to S3.",
                        "url": video_url_s3,
                        "local_path": local_file_path
                    })
                except Exception as upload_error:
                    logger.error(f"Failed to upload existing file to S3: {str(upload_error)}")
                    return JsonResponse({
                        "message": "File exists locally but S3 upload failed.",
                        "local_path": local_file_path
                    })

    # If file doesn't exist locally, proceed with download
    try:
        ydl_opts = get_ydl_opts(download=True, output_path=local_file_path)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.debug(f"Downloading video: {video_url}")
            ydl.download([video_url])

        if not os.path.exists(local_file_path):
            return JsonResponse({"error": "Downloaded file not found."}, status=500)

        # Upload to S3
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        s3_key = f"videos/{video_id}.mp4"
        logger.debug(f"Uploading to S3 bucket: {settings.AWS_STORAGE_BUCKET_NAME}, key: {s3_key}")
        s3_client.upload_file(local_file_path, settings.AWS_STORAGE_BUCKET_NAME, s3_key)
        video_url_s3 = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"

        return JsonResponse({
            "message": "Video uploaded successfully.",
            "url": video_url_s3,
            "local_path": local_file_path
        })

    except yt_dlp.utils.DownloadError as e:
        error_message = str(e)
        if "Sign in to confirm you're not a bot" in error_message:
            return JsonResponse({
                "error": "AUTHENTICATION_REQUIRED",
                "message": "YouTube requires authentication. Please contact administrator to set up cookies.",
                "details": "Bot detection triggered during download - cookies or browser authentication needed"
            }, status=403)
        else:
            logger.error(f"Download failed: {error_message}")
            return JsonResponse({"error": f"Download error: {error_message}"}, status=500)
    except boto3.exceptions.S3UploadFailedError as e:
        logger.error(f"S3 upload failed: {str(e)}")
        return JsonResponse({"error": f"S3 upload failed: {str(e)}"}, status=500)
    except Exception as e:
        logger.exception("Unexpected error occurred")
        return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)


def create_cookies_from_browser():
    """
    Helper function to extract cookies from browser.
    Call this once to set up cookies for your application.
    """
    try:
        # This will extract cookies from your default browser
        # You can specify 'chrome', 'firefox', 'safari', etc.
        ydl_opts = {
            'cookiesfrombrowser': ('chrome', None, None, None),
            'quiet': True,
            'extract_flat': True,
        }

        # Create a temporary file to save cookies
        cookies_path = os.path.join(settings.BASE_DIR, 'youtube_cookies.txt')

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract cookies and save them
            ydl.params['cookiefile'] = cookies_path
            # This will create the cookies file
            info = ydl.extract_info('https://www.youtube.com/watch?v=dQw4w9WgXcQ', download=False)

        return cookies_path
    except Exception as e:
        logger.error(f"Failed to create cookies file: {str(e)}")
        return None


def get_video(request, video_id):
    """Get video URL by video ID"""
    # Initialize S3 uploader
    s3_uploader = S3Uploader(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
        region=getattr(settings, 'AWS_S3_REGION_NAME', None)
    )

    s3_key = f"videos/{video_id}.mp4"

    # Check if the file exists in S3
    if s3_uploader.file_exists_in_s3(s3_key):
        video_url = s3_uploader.get_s3_url(s3_key)
        return JsonResponse({
            "video_id": video_id,
            "url": video_url
        })
    else:
        return JsonResponse({
            "error": "Video not found"
        }, status=404)
