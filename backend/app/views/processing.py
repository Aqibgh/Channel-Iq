"""Media-processing API handlers."""

import boto3
import json
import os
import re
import subprocess
import time

from django.conf import settings
from django.core.mail import send_mail
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .common import (
    AudioEnhancer,
    DjangoVideoTranscriber,
    EnhancedYouTubeSEOGenerator,
    MEDIA_ROOT,
    S3Uploader,
    VideoFileClip,
    logger,
    process_media,
    process_media_shortform,
    process_video,
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_short_form_video(request):
    if request.method == "POST":
        try:
            # Parse the JSON body
            data = json.loads(request.body)
            video_url = data.get("videoURL")
            clip_length = data.get("clipLength")
            clip_count = data.get("clipCount")
            user_email = data.get("userEmail")

            logger.info(f"Received video URL: {video_url}, Clip Length: {clip_length}, Clip Count: {clip_count}")

            # Validate input
            if not video_url:
                return JsonResponse({"error": "Missing required parameter: videoURL"}, status=400)

            # Parse clip parameters
            try:
                clip_count = int(clip_count) if clip_count else 3
            except (ValueError, TypeError):
                logger.warning(f"Invalid clipCount: {clip_count}, using default of 3")
                clip_count = 3

            if clip_length == "auto" or not clip_length:
                clip_length = "auto"
            else:
                try:
                    clip_length = int(clip_length)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid clipLength: {clip_length}, using 'auto'")
                    clip_length = "auto"

            # Check video length using yt-dlp
            video_id = extract_youtube_id(video_url)
            if not video_id:
                return JsonResponse({"error": "Invalid YouTube URL"}, status=400)

            # Try to get video duration with yt-dlp
            try:
                duration = get_video_duration_yt_dlp(video_url)

                if duration is None:
                    logger.warning("Could not determine video length. Proceeding with caution.")
                elif clip_length != "auto" and clip_count > 0:
                    required_duration = clip_length * clip_count
                    if duration < required_duration:
                        error_message = (
                            f"Video duration ({duration} seconds) is insufficient for "
                            f"{clip_count} clips of {clip_length} seconds each "
                            f"(requires {required_duration} seconds)"
                        )
                        logger.error(error_message)
                        return JsonResponse({"error": error_message}, status=400)

                logger.info(f"Video duration check passed: {duration} seconds")
            except Exception as e:
                logger.error(f"Error checking video duration: {e}")
                # Continue without duration check if it fails

            # Process the video
            clips = process_video(video_url, clip_length, clip_count, MEDIA_ROOT)

            if not clips:
                return JsonResponse({"error": "Failed to generate clips from the video"}, status=500)

            # Initialize S3Uploader
            s3_uploader = S3Uploader(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
                region=settings.AWS_S3_REGION_NAME
            )

            # Get user ID from the request
            user_id = request.user.sub if request.user.is_authenticated else "anonymous"

            # Upload clips to S3
            s3_clip_urls = []
            for idx, clip in enumerate(clips):
                local_file_path = os.path.join(MEDIA_ROOT, clip["clip_path"])
                clip_id = f"clip_{idx}_{int(time.time())}"
                s3_key = s3_uploader.get_user_video_key(user_id, clip_id)

                upload_result = s3_uploader.upload_file(local_file_path, s3_key)

                if upload_result["success"]:
                    s3_clip_urls.append({
                        "url": upload_result["url"],
                        "key": upload_result["key"]
                    })
                else:
                    logger.error(f"Failed to upload clip to S3: {upload_result['error']}")

            logger.info(f"Generated S3 clip URLs: {s3_clip_urls}")

            # Send email notification if user email is provided
            if user_email and s3_clip_urls:
                try:
                    # Email details
                    subject = "Your Short-Form Video Processing is Complete"
                    message = f"Hello,\n\nYour video has been successfully processed into {len(s3_clip_urls)} short-form clips.\n\n"
                    message += "Your clips are available at the following links:\n"

                    for i, clip_data in enumerate(s3_clip_urls, 1):
                        message += f"Clip {i}: {clip_data['url']}\n"

                    message += f"\nClip Length: {clip_length}\n"
                    message += "\nThank you for using our service!\n"

                    from_email = settings.DEFAULT_FROM_EMAIL
                    send_mail(subject, message, from_email, [user_email], fail_silently=False)

                    logger.info(f"Email notification sent to {user_email}")

                except Exception as e:
                    logger.error(f"Error sending email notification: {e}")

            # Return success response
            return JsonResponse({
                "message": "Video processed successfully",
                "clips": s3_clip_urls
            }, status=200)

        except json.JSONDecodeError:
            logger.error("Invalid JSON data in request body")
            return JsonResponse({"error": "Invalid JSON data in request body"}, status=400)
        except Exception as e:
            logger.error(f"Error in process_short_form_video: {e}")
            return JsonResponse({"error": str(e)}, status=500)


def extract_youtube_id(url):
    """Extract YouTube video ID from a URL"""
    patterns = [
        r'(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def get_video_duration_yt_dlp(url):
    """
    Get video duration using yt-dlp with optional YouTube cookies
    """
    try:
        # Check if yt-dlp is installed
        try:
            subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("yt-dlp not found. Installing...")
            subprocess.run(['pip', 'install', 'yt-dlp'], check=True)

        # Build the yt-dlp command
        cmd = ['yt-dlp', '--get-duration', '--skip-download']

        # Add cookies if available
        if hasattr(settings, 'YOUTUBE_COOKIES_FILE') and settings.YOUTUBE_COOKIES_FILE:
            cmd += ['--cookies', settings.YOUTUBE_COOKIES_FILE]

        # Add the video URL
        cmd.append(url)

        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # Get and parse the duration string
        duration_str = result.stdout.strip()
        logger.info(f"yt-dlp duration result: {duration_str}")

        parts = duration_str.split(':')

        if len(parts) == 3:  # HH:MM:SS
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:  # MM:SS
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        elif len(parts) == 1 and parts[0].isdigit():  # SS
            return int(parts[0])
        else:
            logger.warning(f"Could not parse duration: {duration_str}")
            return None

    except Exception as e:
        logger.error(f"Error getting duration with yt-dlp: {e}")

        # Optional: fallback to ffprobe if you want
        try:
            return get_video_duration_ffprobe(url)
        except Exception as ffprobe_error:
            logger.error(f"Fallback ffprobe method also failed: {ffprobe_error}")
            return None


def get_video_duration_ffprobe(url):
    """
    Fallback: Get video duration using ffprobe if available
    """
    try:
        # Check if ffprobe is available
        subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)

        # Use ffprobe to get duration
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration_str = result.stdout.strip()

        # Convert to seconds
        duration = float(duration_str)
        return int(duration)

    except Exception as e:
        logger.error(f"Error getting duration with ffprobe: {e}")
        return None


def get_video_resolution(video_path):
    """Gets the resolution (width x height) of the video."""
    with VideoFileClip(video_path) as video:
        width, height = video.size  # (width, height)
    return width, height


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_resolution(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            video_path = data.get("video_path")



            # Normalize and verify the path
            video_path = os.path.normpath(video_path)


            try:
                # Use ffprobe to extract video dimensions
                cmd = [
                    "ffprobe", "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=width,height",
                    "-of", "json", video_path
                ]
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                if result.returncode != 0:
                    return JsonResponse({
                        "resolution": None,
                        "error": "Failed to retrieve video resolution",
                        "details": result.stderr
                    }, status=500)

                metadata = json.loads(result.stdout)
                width = metadata['streams'][0]['width']
                height = metadata['streams'][0]['height']

                return JsonResponse({
                    "resolution": {
                        "width": width,
                        "height": height
                    },
                    "error": None
                })

            except Exception as e:
                return JsonResponse({
                    "resolution": None,
                    "error": f"Error reading video file: {str(e)}"
                }, status=500)

        except json.JSONDecodeError as e:
            return JsonResponse({
                "resolution": None,
                "error": "Invalid JSON in request body"
            }, status=400)
        except Exception as e:
            return JsonResponse({
                "resolution": None,
                "error": f"Server error: {str(e)}"
            }, status=500)

    return JsonResponse({
        "resolution": None,
        "error": "Only POST method is allowed"
    }, status=405)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def seo(request):
    if request.method == "POST":
        try:
            # Parse the JSON body
            data = json.loads(request.body)
            video_url = data.get("videoURL")
            localpath = data.get("localVideoPath")
            selected_features = data.get("selectedFeatures", [])  # Extract selected features
            user_id = data.get("userId")
            user_email = data.get("userEmail")  # Get user email from the request
            logger.debug("Processing SEO request for user %s", user_id)

            # Debugging log
            logger.info(f"Received video URL for SEO: {video_url}, Selected Features: {selected_features}, LocalPath: {localpath}")

            if not video_url and not localpath:
                return JsonResponse({"error": "No URL or local path provided"}, status=400)

            # Define the order of feature processing
            feature_order = ["SEO", "Video Quality", "Noise Reduction"]
            selected_features = sorted(
                selected_features,
                key=lambda feature: feature_order.index(feature) if feature in feature_order else len(feature_order)
            )
            logger.info(f"Selected features after sort: {selected_features}")

            # Initialize a dictionary to store the results for all selected features
            results = {}

            # Check video resolution before processing
            video_resolution = None
            if localpath:
                try:
                    width, height = get_video_resolution(localpath)
                    logger.info(f"Video Resolution: {width}x{height}")
                    video_resolution = (width, height)
                except Exception as e:
                    logger.error(f"Error getting video resolution: {e}")
                    results["video_upscaling"] = {"error": "Failed to get video resolution"}

            # Handle SEO feature
            if "SEO" in selected_features:
                try:
                    if video_url:
                        seo_generator = EnhancedYouTubeSEOGenerator()
                        seo_data = seo_generator.process_video(video_url)
                        results["seo"] = seo_data
                except Exception as e:
                    logger.error(f"Error in SEO processing: {e}")
                    results["seo"] = {"error": str(e)}

            # Handle Video Quality feature - LOCAL processing
            upscaled_video_path = None
            if "Video Quality" in selected_features and localpath:
                    try:
                        # Only proceed with upscaling if the resolution is less than or equal to 480p (height <= 480)
                        if video_resolution and video_resolution[1] <= 480:
                            # Calculate target upscale factor to reach ~1080p
                            original_height = video_resolution[1]
                            target_height = 1080
                            upscale_factor = min(4, target_height / original_height)  # Cap at 4x (max model capability)

                            # Adjust resize factor to feed appropriate resolution to AI
                            # We want to feed the largest possible input that won't exceed GPU memory
                            resize_factor = min(100, (100 * 4 / upscale_factor))  # Adjust based on upscale needs

                            upscaled_video_path = process_media(
                                file_path=localpath,
                                ai_model="RealESR_Gx4",  # Good for general upscaling
                                resize_factor=resize_factor,
                                output_path=None,
                                cpu_number=4,
                                keep_frames=False,
                            )

                            results["video_upscaling"] = {
                                "processed_file_path": upscaled_video_path,
                                "original_resolution": f"{video_resolution[0]}x{video_resolution[1]}",
                                "target_resolution": "1920x1080",
                                "status": "success"
                            }
                        else:
                            results["video_upscaling"] = {
                                "message": f"Resolution {video_resolution[0]}x{video_resolution[1]} is greater than 480p, skipping upscaling."
                            }
                    except Exception as e:
                        logger.error(f"Error in video upscaling: {e}")
                        results["video_upscaling"] = {"error": str(e)}

            # Handle Noise Reduction feature - LOCAL processing
            enhanced_audio_path = None
            if "Noise Reduction" in selected_features:
                try:
                    clip_path = upscaled_video_path or localpath
                    if clip_path:
                        # Create output directory if it doesn't exist
                        output_dir = os.path.join(settings.MEDIA_ROOT, 'processed')
                        os.makedirs(output_dir, exist_ok=True)

                        # Initialize AudioEnhancer
                        audio_enhancer = AudioEnhancer()

                        # Process the video
                        process_result = audio_enhancer.process_video(
                            video_path=str(clip_path),
                            output_dir=str(output_dir)
                        )

                        # Get the enhanced video path from the result
                        enhanced_audio_path = process_result.get('enhanced_video_path')

                        if enhanced_audio_path and os.path.exists(enhanced_audio_path):
                            results["audio_processing"] = {
                                "processed_file_path": enhanced_audio_path,
                                "status": "success"
                            }
                        else:
                            results["audio_processing"] = {
                                "error": "Enhanced video file not found",
                                "status": "error"
                            }
                    else:
                        results["audio_processing"] = {
                            "error": "Clip path not provided",
                            "status": "error"
                        }
                except Exception as e:
                    logger.error(f"Error in audio processing: {str(e)}")
                    results["audio_processing"] = {
                        "error": str(e),
                        "status": "error"
                    }

            # FINAL S3 UPLOAD - Upload the final processed video to S3
            final_video_path = enhanced_audio_path or upscaled_video_path or localpath
            s3_url = None

            # Only upload if we have a user ID and a processed video
            if user_id and final_video_path and os.path.exists(final_video_path):
                try:
                    # Initialize S3 uploader
                    s3_uploader = S3Uploader(
                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                        bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
                        region=settings.AWS_S3_REGION_NAME
                    )

                    # Generate a unique video ID based on processing features
                    feature_string = "-".join(selected_features).lower().replace(" ", "-")
                    video_id = f"{feature_string}_{os.path.basename(final_video_path).split('.')[0]}"

                    # Upload to S3
                    s3_key = s3_uploader.get_user_video_key(user_id, video_id)
                    upload_result = s3_uploader.upload_file(final_video_path, s3_key)

                    if upload_result["success"]:
                        # Add S3 information to results
                        results["s3_upload"] = {
                            "url": upload_result["url"],
                            "key": upload_result["key"],
                            "status": "success"
                        }
                        s3_url = upload_result["url"]

                        # Update the processed file path in the final results to use the S3 URL
                        if enhanced_audio_path:
                            results["audio_processing"]["s3_processed_file_path"] = upload_result["url"]
                        elif upscaled_video_path:
                            results["video_upscaling"]["s3_processed_file_path"] = upload_result["url"]
                    else:
                        results["s3_upload"] = {
                            "error": f"Failed to upload to S3: {upload_result.get('error')}",
                            "status": "error"
                        }
                except Exception as e:
                    logger.error(f"Error uploading to S3: {str(e)}")
                    results["s3_upload"] = {
                        "error": str(e),
                        "status": "error"
                    }

            # Send email notification if user email is provided
            if user_email:
                try:
                    # Generate list of processed features
                    processed_features = []
                    if "seo" in results and "error" not in results["seo"]:
                        processed_features.append("SEO")
                    if "video_upscaling" in results and results["video_upscaling"].get("status") == "success":
                        processed_features.append("Video Quality")
                    if "audio_processing" in results and results["audio_processing"].get("status") == "success":
                        processed_features.append("Noise Reduction")

                    # Generate feature list text
                    feature_list = ", ".join(processed_features)

                    # Construct email subject and message
                    subject = "Your Video Processing is Complete"

                    # Construct the message body
                    message = f"Hello,\n\nYour video has been successfully processed with the following features: {feature_list}.\n\n"

                    # Add S3 URL if available
                    if s3_url:
                        message += f"You can access your processed video here: {s3_url}\n\n"

                    # Add SEO details if available
                    if "seo" in results and "error" not in results["seo"]:
                        seo_data = results["seo"]
                        message += "SEO Recommendations:\n"
                        if "title" in seo_data:
                            message += f"- Title: {seo_data['title']}\n"
                        if "description" in seo_data:
                            message += f"- Description: {seo_data['description']}\n"
                        if "tags" in seo_data and seo_data["tags"]:
                            message += f"- Tags: {', '.join(seo_data['tags'])}\n"

                    message += "\nThank you for using our service!\n"

                    # Send email
                    from_email = settings.DEFAULT_FROM_EMAIL
                    send_mail(subject, message, from_email, [user_email], fail_silently=False)

                    # Log success
                    logger.info(f"Email notification sent to {user_email}")
                    results["email_notification"] = {"status": "success", "email": user_email}

                except Exception as e:
                    logger.error(f"Error sending email notification: {e}")
                    results["email_notification"] = {"status": "error", "message": str(e)}

            # Return results after processing all selected features
            return JsonResponse({
                "message": "Processing completed successfully",
                "results": results
            }, status=200)

        except json.JSONDecodeError:
            logger.error("Invalid JSON data in request body")
            return JsonResponse({"error": "Invalid JSON data in request body"}, status=400)
        except Exception as e:
            logger.error(f"Error in SEO function: {e}")
            return JsonResponse({"error": "Internal Server Error"}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def optimize_shortform(request):
    if request.method == "POST":
        try:
            # Parse the JSON body
            data = json.loads(request.body)
            clip_path = data.get("clipPath")
            clip_key = data.get("clipKey")
            selected_features = data.get("selectedFeatures", [])
            video_url = data.get("videoURL", None)
            user_email = data.get("userEmail")

            # Debugging log
            logger.info(f"Received clip for optimization: {clip_path}, Key: {clip_key}, Selected Features: {selected_features}, Video URL: {video_url}")

            if not clip_path or not clip_key:
                return JsonResponse({"error": "No clip path or key provided"}, status=400)

            # Initialize S3 uploader with credentials from settings
            s3_uploader = S3Uploader(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
                region=settings.AWS_S3_REGION_NAME
            )

            # Download the clip from S3 to local media folder
            local_dir = os.path.join(settings.MEDIA_ROOT, 'temp_downloads')
            os.makedirs(local_dir, exist_ok=True)

            filename = os.path.basename(clip_key)
            local_clip_path = os.path.join(local_dir, filename)

            # Download file from S3
            try:
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_S3_REGION_NAME
                )
                s3_client.download_file(settings.AWS_STORAGE_BUCKET_NAME, clip_key, local_clip_path)
                logger.info(f"Successfully downloaded clip from S3 to {local_clip_path}")
            except Exception as e:
                logger.error(f"Error downloading clip from S3: {e}")
                return JsonResponse({"error": f"Failed to download clip from S3: {str(e)}"}, status=500)

            # Initialize results dictionary
            results = {}

            # Check language if Captions feature is selected
            if "Captions" in selected_features:
                try:
                    def detect_audio_language(file_path):
                        """
                        Detect the language of the audio in a video file
                        Returns language code (e.g., 'en' for English)
                        """
                        try:
                            # Create a temporary file for the audio
                            temp_audio_path = file_path.replace('.mp4', '_temp_audio.wav')

                            # Extract audio from video
                            command = [
                                'ffmpeg',
                                '-i', file_path,
                                '-vn',  # Skip video
                                '-acodec', 'pcm_s16le',
                                '-ar', '16000',
                                '-ac', '1',
                                temp_audio_path,
                                '-y'  # Overwrite if exists
                            ]

                            subprocess.run(command, check=True, capture_output=True)

                            # Use whisper to detect language
                            import whisper
                            model = whisper.load_model("tiny")  # Using tiny model just for language detection
                            result = model.transcribe(temp_audio_path, task="translate")

                            # Clean up
                            if os.path.exists(temp_audio_path):
                                os.remove(temp_audio_path)

                            return result.get("language", "unknown")
                        except Exception as e:
                            logger.error(f"Error detecting language: {e}")
                            return "unknown"  # Default to unknown on error

                    # Detect language of the clip
                    detected_language = detect_audio_language(local_clip_path)

                    if detected_language.lower() != "en":
                        # Clean up the downloaded file
                        if os.path.exists(local_clip_path):
                            os.remove(local_clip_path)

                        # Return early with language error message
                        return JsonResponse({
                            "message": "Cannot process video with selected features.",
                            "results": {
                                "captions": {
                                    "status": "language_error",
                                    "detected_language": detected_language,
                                    "message": f"Captions can only be applied to English content. Detected language: {detected_language}."
                                }
                            }
                        }, status=200)
                except Exception as e:
                    logger.error(f"Error in language detection: {e}")
                    # Continue with processing if language detection fails
                    results["captions"] = {"error": f"Language detection error: {str(e)}"}
            # Sort features to ensure Video Quality comes before Noise Reduction
            feature_order = ["SEO", "Video Quality", "Noise Reduction", "Captions"]
            selected_features = sorted(
                selected_features,
                key=lambda feature: feature_order.index(feature) if feature in feature_order else len(feature_order)
            )
            logger.info(f"Selected features after sort: {selected_features}")

            # Initialize S3 uploader with credentials from settings
            s3_uploader = S3Uploader(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
                region=settings.AWS_S3_REGION_NAME
            )

            # Download the clip from S3 to local media folder
            local_dir = os.path.join(settings.MEDIA_ROOT, 'temp_downloads')
            os.makedirs(local_dir, exist_ok=True)

            filename = os.path.basename(clip_key)
            local_clip_path = os.path.join(local_dir, filename)

            # Download file from S3
            try:
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_S3_REGION_NAME
                )
                s3_client.download_file(settings.AWS_STORAGE_BUCKET_NAME, clip_key, local_clip_path)
                logger.info(f"Successfully downloaded clip from S3 to {local_clip_path}")
            except Exception as e:
                logger.error(f"Error downloading clip from S3: {e}")
                return JsonResponse({"error": f"Failed to download clip from S3: {str(e)}"}, status=500)

            # Initialize results dictionary
            results = {}
            current_clip_path = local_clip_path  # Start with downloaded file

            # Process SEO if selected
            if "SEO" in selected_features:
                try:
                    seo_generator = EnhancedYouTubeSEOGenerator(
                        youtube_api_key=settings.YOUTUBE_API_KEY,
                        openai_api_key=settings.OPENAI_API_KEY
                    )

                    if video_url:
                        # If we have the original video URL, process with enhanced context
                        try:
                            # First get additional context from the original video
                            video_id = seo_generator.extract_video_id(video_url)
                            video_details = {}
                            competitor_videos = []
                            comments = []
                            transcript_data = {}

                            # Get basic video details if valid URL
                            if video_id:
                                try:
                                    video_details = seo_generator.get_video_details(video_id)
                                    competitor_videos = seo_generator.get_competitor_videos(video_details.get("title", ""))
                                    comments = seo_generator.analyze_comments(video_id)
                                    transcript_data = seo_generator.get_youtube_transcript_with_timestamps(video_id)
                                except Exception as e:
                                    logger.warning(f"Non-critical error getting additional video context: {e}")



                            # Generate SEO content with combined context
                            seo_data = seo_generator.process_video_shortform_enhanced(
                                file_path=current_clip_path,
                                original_video_details=video_details,
                                original_transcript=transcript_data,
                                competitor_videos=competitor_videos,
                                comments=comments
                            )
                            results["seo"] = seo_data
                        except Exception as e:
                            logger.error(f"Error in enhanced SEO processing: {e}")
                            # Fall back to basic SEO if enhanced fails
                            seo_data = seo_generator.process_video_shortform(current_clip_path)
                            results["seo"] = seo_data
                    else:
                        # Basic SEO processing without original video context
                        seo_data = seo_generator.process_video_shortform(current_clip_path)
                        results["seo"] = seo_data
                except Exception as e:
                    logger.error(f"Error in SEO processing: {e}")
                    results["seo"] = {"error": str(e)}

            # Process Video Quality if selected
            upscaled_video_path = None
            if "Video Quality" in selected_features:
                try:
                    upscaled_video_path = process_media_shortform(
                        file_path=current_clip_path,
                        ai_model="IRCNN_Lx1",
                        resize_factor=100,
                        output_path=None,
                        cpu_number=4,
                        keep_frames=False,
                    )
                    results["video_upscaling"] = {"processed_file_path": upscaled_video_path}

                    # Update current working path
                    current_clip_path = upscaled_video_path
                    logger.info(f"Updated path after video processing: {current_clip_path}")
                except Exception as e:
                    logger.error(f"Error in video upscaling: {e}")
                    results["video_upscaling"] = {"error": str(e)}

            # Process Noise Reduction if selected
            enhanced_video_path = None
            if "Noise Reduction" in selected_features:
                try:
                    if current_clip_path:
                        # Create output directory if it doesn't exist
                        output_dir = os.path.join(settings.MEDIA_ROOT, 'processed')
                        os.makedirs(output_dir, exist_ok=True)

                        # Process audio
                        audio_enhancer = AudioEnhancer()
                        process_result = audio_enhancer.process_video(
                            video_path=str(current_clip_path),
                            output_dir=str(output_dir)
                        )

                        enhanced_video_path = process_result.get('enhanced_video_path')

                        if enhanced_video_path and os.path.exists(enhanced_video_path):
                            results["audio_processing"] = {
                                "processed_file_path": enhanced_video_path,
                                "status": "success"
                            }
                            # Update current working path
                            current_clip_path = enhanced_video_path
                        else:
                            results["audio_processing"] = {
                                "error": "Enhanced video file not found",
                                "status": "error"
                            }
                    else:
                        results["audio_processing"] = {
                            "error": "Clip path not provided",
                            "status": "error"
                        }
                except Exception as e:
                    logger.error(f"Error in audio processing: {str(e)}")
                    results["audio_processing"] = {
                        "error": str(e),
                        "status": "error"
                    }

            # Process Captions if selected
            captioned_video_path = None
            if "Captions" in selected_features:
                try:
                    # Use final processed video path
                    final_video_path = current_clip_path

                    # Process captions
                    transcriber = DjangoVideoTranscriber(
                        model_path="large-v3-turbo",
                        video_path=final_video_path
                    )

                    captioned_video_path = transcriber.process_video()

                    results["captions"] = {
                        "processed_file_path": captioned_video_path,
                        "status": "success"
                    }

                    # Update current working path
                    current_clip_path = captioned_video_path
                    logger.info(f"Updated path after captioning: {current_clip_path}")
                except Exception as e:
                    logger.error(f"Error in captioning: {e}")
                    results["captions"] = {"error": str(e)}

            # Upload the final processed file to S3
            final_processed_path = current_clip_path
            final_s3_url = None

            if final_processed_path and os.path.exists(final_processed_path):
                try:
                    # Create S3 key for the processed file
                    processed_filename = os.path.basename(final_processed_path)
                    processed_s3_key = f"processed/{processed_filename}"

                    # Upload to S3
                    upload_result = s3_uploader.upload_file(
                        local_file_path=final_processed_path,
                        s3_key=processed_s3_key
                    )

                    if upload_result["success"]:
                        # Add S3 URL and key to results
                        final_s3_url = upload_result["url"]
                        results["final_processed"] = {
                            "s3_url": upload_result["url"],
                            "s3_key": upload_result["key"],
                            "status": "success"
                        }
                    else:
                        results["final_processed"] = {
                            "error": upload_result["error"],
                            "status": "error"
                        }
                except Exception as e:
                    logger.error(f"Error uploading processed file to S3: {e}")
                    results["final_processed"] = {
                        "error": f"S3 upload error: {str(e)}",
                        "status": "error"
                    }

            # Send email notification if user email is provided
            if user_email:
                try:
                    # Generate list of processed features
                    processed_features = []
                    for feature in selected_features:
                        if feature == "SEO" and "seo" in results and "error" not in results["seo"]:
                            processed_features.append("SEO")
                        elif feature == "Video Quality" and "video_upscaling" in results and "error" not in results["video_upscaling"]:
                            processed_features.append("Video Quality")
                        elif feature == "Noise Reduction" and "audio_processing" in results and results["audio_processing"].get("status") == "success":
                            processed_features.append("Noise Reduction")
                        elif feature == "Captions" and "captions" in results and results["captions"].get("status") == "success":
                            processed_features.append("Captions")

                    # Generate feature list text
                    feature_list = ", ".join(processed_features)

                    # Construct email subject and message
                    subject = "Your Short-Form Video Optimization is Complete"

                    # Construct the message body
                    message = f"Hello,\n\nYour short-form video has been successfully optimized with the following features: {feature_list}.\n\n"

                    # Add S3 URL if available
                    if final_s3_url:
                        message += f"You can access your optimized video here: {final_s3_url}\n\n"

                    # Add SEO details if available
                    if "seo" in results and "error" not in results["seo"]:
                        seo_data = results["seo"]
                        message += "SEO Recommendations:\n"
                        if "title" in seo_data:
                            message += f"- Title: {seo_data['title']}\n"
                        if "description" in seo_data:
                            message += f"- Description: {seo_data['description']}\n"
                        if "tags" in seo_data and seo_data["tags"]:
                            message += f"- Tags: {', '.join(seo_data['tags'])}\n"

                    message += "\nThank you for using our service!\n"

                    # Send email
                    from_email = settings.DEFAULT_FROM_EMAIL
                    send_mail(subject, message, from_email, [user_email], fail_silently=False)

                    # Log success
                    logger.info(f"Email notification sent to {user_email}")
                    results["email_notification"] = {"status": "success", "email": user_email}

                except Exception as e:
                    logger.error(f"Error sending email notification: {e}")
                    results["email_notification"] = {"status": "error", "message": str(e)}

            # Clean up local files
            try:
                # Delete the original downloaded file
                if os.path.exists(local_clip_path):
                    os.remove(local_clip_path)

                # Delete intermediate processed files
                if upscaled_video_path and os.path.exists(upscaled_video_path):
                    os.remove(upscaled_video_path)

                if enhanced_video_path and os.path.exists(enhanced_video_path):
                    os.remove(enhanced_video_path)

                if captioned_video_path and os.path.exists(captioned_video_path):
                    os.remove(captioned_video_path)

                logger.info("Cleaned up local temporary files")
            except Exception as e:
                logger.warning(f"Error cleaning up local files: {e}")
                # Don't return an error if cleanup fails, just log it

            return JsonResponse({
                "message": "Processing completed successfully",
                "results": results
            }, status=200)

        except json.JSONDecodeError:
            logger.error("Invalid JSON data in request body")
            return JsonResponse({"error": "Invalid JSON data in request body"}, status=400)
        except Exception as e:
            logger.error(f"Error in optimize_shortform function: {e}")
            return JsonResponse({"error": f"Internal Server Error: {str(e)}"}, status=500)
